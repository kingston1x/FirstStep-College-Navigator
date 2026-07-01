"""
cleaner.py — Scholarship Data Cleaner
=======================================
 takes raw scholarship CSVs (from manual collection
and scraper) and outputs a single clean CSV that the model and backend both read from

Input:  data/raw/Scholarships.csv  (and any extra raw files)
Output: data/clean/scholarships_clean.csv

Usage:
    python cleaner.py
    python cleaner.py --input data/raw/Scholarships.csv --output data/clean/scholarships_clean.csv

    
Dependencies:
    pip install pandas
"""

import argparse
import os
import re
import sys
from datetime import datetime

import pandas as pd


# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DEFAULT_INPUT  = "data/raw/Scholarships.csv"
DEFAULT_OUTPUT = "data/clean/scholarships_clean.csv"

# Every column the model (firststep_model.py) expects — do not remove any.
REQUIRED_COLUMNS = [
    "id", "name", "provider", "country", "level", "field_of_study",
    "min_gpa", "funding_type", "value", "deadline", "eligibility",
    "language_req", "description", "apply_url", "source_url",
    "source_type", "collected_by", "date_added", "needs_review",
]

# if blank then rows dropped.
NON_NULLABLE = ["id", "name", "provider", "country"]

# Valid study levels (case-insensitive). Anything else → normalised to "Any".
VALID_LEVELS = {"undergraduate", "masters", "phd", "doctoral", "any"}

# Valid funding types (case-insensitive). Anything not matching → kept as-is
# but flagged in the report.
KNOWN_FUNDING_TYPES = {"fully funded", "partial", "tuition only", "stipend only"}

# year month day
DEADLINE_FORMAT = "%Y-%m-%d"


# ──────────────────────────────────────────────────────────────
# 1. LOAD
# ──────────────────────────────────────────────────────────────────────────────

def load(path: str) -> pd.DataFrame:
    """Load one or more CSVs and concatenate them."""
    paths = path.split(",") if "," in path else [path]
    frames = []
    for p in paths:
        p = p.strip()
        if not os.path.exists(p):
            print(f"  [WARN] File not found, skipping: {p}")
            continue
        df = pd.read_csv(p, dtype=str)
        print(f"  Loaded {len(df)} rows from {p}")
        frames.append(df)

    if not frames:
        sys.exit("  [ERROR] No input files could be read. Exiting.")

    combined = pd.concat(frames, ignore_index=True)
    print(f"  Total rows after merge: {len(combined)}")
    return combined

# ──────────────────────────────────────────────────────────────────────────────
# 2. VALIDATE COLUMNS
# ────────────────────────────────────────────────────────────────

def validate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add any missing expected columns as empty strings so downstream doesn't break."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        print(f"  [WARN] Missing columns added as empty: {missing}")
        for col in missing:
            df[col] = ""
    # Keep only the expected columns ( extras, keep silently)
    return df


#──────────────────────────────────
# 3. DROP BAD ROWS
# ───────────────────────────────────────────────────────────

def drop_bad_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicates and rows missing critical fields."""
    before = len(df)

    # Strip space on all string columns first
    df = df.apply(lambda col: col.str.strip() if col.dtype == object else col)

    # Blank out cells that are just whitespace or  null 
    null_values = {"", "n/a", "na", "none", "null", "-", "—", "tbd"}
    df = df.replace(null_values, pd.NA)

    # Drop rows missing non-nullable fields
    df = df.dropna(subset=NON_NULLABLE)
    after_null = len(df)

    # Drop exact duplicate rows
    df = df.drop_duplicates()
    after_dedup = len(df)

    # Drop duplicate IDs — keep the first occurrence ( recently added if
    # we sort by date_added first)
    if "date_added" in df.columns:
        df = df.sort_values("date_added", ascending=False, na_position="last")
    df = df.drop_duplicates(subset=["id"], keep="first")
    after_id_dedup = len(df)

    print(f"  Rows dropped (missing required fields): {before - after_null}")
    print(f"  Rows dropped (exact duplicates):        {after_null - after_dedup}")
    print(f"  Rows dropped (duplicate IDs):           {after_dedup - after_id_dedup}")
    print(f"  Rows remaining: {after_id_dedup}")
    return df.reset_index(drop=True)


# ──────────────────────
# 4. NORMALISE FIELDS
# ────────────────────────────────────────────────

def normalise_level(raw) -> str:
    """Normalise study level to a consistent value."""
    if pd.isna(raw):
        return "Any"
    text = str(raw).lower().strip()
    if text in ("undergraduate", "ug", "bachelor", "bachelors", "bachelor's"):
        return "Undergraduate"
    if text in ("masters", "master", "master's", "postgraduate", "pg", "msc", "ma", "mba"):
        return "Masters"
    if text in ("phd", "doctoral", "doctorate", "research"):
        return "PhD"
    if text in ("any", "all", "all levels"):
        return "Any"
    # slash or semicolons , lists multiple 
    if any(sep in text for sep in ["/", ";", ","]):
        return raw.strip()
    # Unknown — keep original but title-cased
    return str(raw).strip().title()


def normalise_country(raw) -> str:
    """Consistent country naming."""
    if pd.isna(raw):
        return ""
    country_map = {
        "usa": "US", "united states": "US", "u.s.": "US", "u.s.a.": "US",
        "united kingdom": "UK", "great britain": "UK", "england": "UK",
        "türkiye": "Turkey", "turkiye": "Turkey",
        "people's republic of china": "China", "prc": "China",
    }
    val = str(raw).strip()
    return country_map.get(val.lower(), val)


def normalise_deadline(raw) -> str:
    """
    Parse any sensible date format and output YYYY-MM-DD. Returns raw if bad.

    Scholarship deadlines in the wild come with a lot of noise:
      - annotations: "31 July 2026 (annual)", "Rolling**"
      - multiple dates / ranges: "1/28 Feb 2026", "10 Apr/2 May 2026",
        "Feb-April 2026", "varies, July-Oct 2026"
    We strip the noise and, for ranges, keep the EARLIEST parseable date
    (the one a student needs to hit), rather than giving up entirely.
    """
    if pd.isna(raw):
        return ""
    raw_str = str(raw).strip()

    # Already correct format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw_str):
        return raw_str

    def _try_parse(s: str) -> str | None:
        s = s.strip()
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y",
                    "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).strftime(DEADLINE_FORMAT)
            except ValueError:
                continue
        return None

    # Strip parenthetical annotations like "(annual)" and stray asterisks.
    cleaned = re.sub(r"\(.*?\)", "", raw_str)
    cleaned = cleaned.replace("*", "").strip().rstrip(",")

    parsed = _try_parse(cleaned)
    if parsed:
        return parsed

    # Handle "varies, <range>" by dropping the "varies," prefix.
    cleaned2 = re.sub(r"^varies,?\s*", "", cleaned, flags=re.IGNORECASE)

    # Date ranges: split on "/" or "-" and try each side, keep the earliest
    # that parses. Handles "1/28 Feb 2026", "10 Apr/2 May 2026",
    # "Feb-April 2026", "27 Feb/29 May 2026".
    candidates: list[str] = []
    for sep in ("/", "-"):
        if sep in cleaned2:
            parts = [p.strip() for p in cleaned2.split(sep)]
            # If the first part has no year/month name, borrow the trailing
            # "<Month> <Year>" (or day+month+year) from the last part.
            tail_match = re.search(r"([A-Za-z]+\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})$", cleaned2)
            tail = tail_match.group(1) if tail_match else ""
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                if _try_parse(p):
                    candidates.append(p)
                elif tail and p not in tail:
                    candidates.append(f"{p} {tail}".strip() if not re.search(r"\d{4}", p) else p)

    parsed_candidates = [d for d in (_try_parse(c) for c in candidates) if d]
    if parsed_candidates:
        return min(parsed_candidates)

    # Couldn't parse (e.g. "Rolling", "Ongoing (annual)") — keep as-is and flag.
    return raw_str


def normalise_funding_type(raw) -> str:
    """Title-case funding type and warn on unknowns."""
    if pd.isna(raw):
        return ""
    val = str(raw).strip().lower()
    if val in KNOWN_FUNDING_TYPES:
        return val.title()
    # the model doesn't filter on this field strictly
    return str(raw).strip()


def normalise_language(raw) -> str:
    """Clean up language field — strip parens/notes, title-case."""
    if pd.isna(raw):
        return ""
    # Remove things like "(HSK/IELTS may apply)"
    cleaned = re.sub(r"\(.*?\)", "", str(raw)).strip()
    return cleaned.title() if cleaned else str(raw).strip()


def normalise_url(raw) -> str:
    """Ensure URL has a scheme; leave blank if clearly not a URL."""
    if pd.isna(raw):
        return ""
    val = str(raw).strip()
    if not val:
        return ""
    if not val.startswith(("http://", "https://")):
        val = "https://" + val
    return val


def normalise_text_field(raw) -> str:
    """Collapse multiple spaces, strip, and ensure consistent spacing after semicolons."""
    if pd.isna(raw):
        return ""
    text = str(raw).strip()
    text = re.sub(r"[ \t]+", " ", text)          # collapse whitespace
    text = re.sub(r"\s*;\s*", "; ", text)         # consistent semicolons
    return text


def normalise_all(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all normalisation functions to the dataframe."""
    df["level"]        = df["level"].apply(normalise_level)
    df["country"]      = df["country"].apply(normalise_country)
    df["deadline"]     = df["deadline"].apply(normalise_deadline)
    df["funding_type"] = df["funding_type"].apply(normalise_funding_type)
    df["language_req"] = df["language_req"].apply(normalise_language)
    df["apply_url"]    = df["apply_url"].apply(normalise_url)
    df["source_url"]   = df["source_url"].apply(normalise_url)

    for col in ["name", "provider", "field_of_study", "eligibility",
                "description", "value", "min_gpa"]:
        if col in df.columns:
            df[col] = df[col].apply(normalise_text_field)

    # Standardise source_type capitalisation
    if "source_type" in df.columns:
        df["source_type"] = df["source_type"].str.strip().str.title().fillna("")

    return df


# ──────────────────────────────────────────
# 5. FLAG ISSUES — sets needs_review + prints a report
# ───────────────────────────────────────────────────────

def flag_issues(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a 'needs_review' flag per row (True if a human should double-check
    this scholarship before it goes live), and print a data quality report.

    A row is flagged if any of:
      - deadline is in the past
      - deadline couldn't be parsed into YYYY-MM-DD
      - apply_url is missing
      - description is missing
    """
    today = datetime.today()
    reasons = [[] for _ in range(len(df))]

    for i, row in df.iterrows():
        deadline_val = str(row.get("deadline", "") or "")
        if deadline_val:
            try:
                dl = datetime.strptime(deadline_val, DEADLINE_FORMAT)
                if dl < today:
                    reasons[i].append(f"[EXPIRED] deadline {deadline_val} is in the past")
            except ValueError:
                reasons[i].append(f"[BAD DATE] unparseable deadline: '{deadline_val}'")

        if not str(row.get("apply_url", "") or "").strip():
            reasons[i].append("[NO URL] missing apply_url")

        if not str(row.get("description", "") or "").strip():
            reasons[i].append("[NO DESC] missing description")

    df["needs_review"] = [len(r) > 0 for r in reasons]

    total_flagged = sum(df["needs_review"])
    if total_flagged:
        print(f"\n  Data quality flags ({total_flagged} row(s) marked needs_review=True):")
        for i, row in df.iterrows():
            if reasons[i]:
                print(f"  {row['id']} — " + "; ".join(reasons[i]))
    else:
        print("\n  No data quality issues found. needs_review is False for all rows.")

    return df


# ───────────────────────────────────────────────────────────
# 6. SAVE
# ─────────────────────────────────────────

def save(df: pd.DataFrame, output_path: str) -> None:
    """Write clean CSV to disk, creating output directory if needed."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    # Output only the standard columns in order, plus any extras appended at end
    standard = [c for c in REQUIRED_COLUMNS if c in df.columns]
    extras   = [c for c in df.columns if c not in REQUIRED_COLUMNS and not c.startswith("_")]
    df[standard + extras].to_csv(output_path, index=False)
    print(f"\n  Saved {len(df)} clean rows → {output_path}")


# ─────────────────────────────────────────────────────────────────────────
# 7. MAIN
# ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Clean raw scholarship CSV data.")
    parser.add_argument("--input",  default=DEFAULT_INPUT,
                        help="Path to raw CSV (or comma-separated list of paths)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help="Where to write the clean CSV")
    args = parser.parse_args()

    print("\n── cleaner.py ─────────────────────────────")
    print(f"  Input:  {args.input}")
    print(f"  Output: {args.output}")
    print("───────────────────────────────────────────────────\n")

    print("Step 1 — Loading data")
    df = load(args.input)

    print("\nStep 2 — Validating columns")
    df = validate_columns(df)

    print("\nStep 3 — Dropping bad rows")
    df = drop_bad_rows(df)

    print("\nStep 4 — Normalising fields")
    df = normalise_all(df)

    print("\nStep 5 — Flagging issues")
    df = flag_issues(df)

    print("\nStep 6 — Saving")
    save(df, args.output)

    print("\n── Done ─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
