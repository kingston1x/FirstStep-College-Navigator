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

DEFAULT_INPUT  = "data\raw\Scholarships.csv"
DEFAULT_OUTPUT = "data\clean\scholarships_clean.csv"

# Every column the model (firststep_model.py) expects — do not remove any.
REQUIRED_COLUMNS = [
    "id", "name", "provider", "country", "level", "field_of_study",
    "min_gpa", "funding_type", "value", "deadline", "eligibility",
    "language_req", "description", "apply_url", "source_url",
    "source_type", "collected_by", "date_added",
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
    """Parse any sensible date format and output YYYY-MM-DD. Returns raw if bad."""
    if pd.isna(raw):
        return ""
    raw_str = str(raw).strip()
    # Already correct format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw_str):
        return raw_str
    # Try common formats
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y",
                "%b %d, %Y", "%d %B %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw_str, fmt).strftime(DEADLINE_FORMAT)
        except ValueError:
            continue
    # Couldn't parse, keep as-is and flag
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
# 5. FLAG ISSUES (non-destructive — just prints a report)
# ───────────────────────────────────────────────────────

def flag_issues(df: pd.DataFrame) -> None:
    """Print a data quality report. Doesn't modify the dataframe."""
    issues = []

    # Past deadlines
    today = datetime.today()
    for _, row in df.iterrows():
        try:
            dl = datetime.strptime(row["deadline"], DEADLINE_FORMAT)
            if dl < today:
                issues.append(f"  [EXPIRED]  {row['id']} — deadline {row['deadline']} is in the past")
        except (ValueError, TypeError):
            if row["deadline"]:
                issues.append(f"  [BAD DATE] {row['id']} — unparseable deadline: '{row['deadline']}'")

    # Missing apply_url
    for _, row in df.iterrows():
        if not row.get("apply_url", "").strip():
            issues.append(f"  [NO URL]   {row['id']} — missing apply_url")

    # Missing description
    for _, row in df.iterrows():
        if not row.get("description", "").strip():
            issues.append(f"  [NO DESC]  {row['id']} — missing description")

    if issues:
        print(f"\n  Data quality flags ({len(issues)} total):")
        for issue in issues:
            print(issue)
    else:
        print("\n  No data quality issues found.")


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
    flag_issues(df)

    print("\nStep 6 — Saving")
    save(df, args.output)

    print("\n── Done ─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
