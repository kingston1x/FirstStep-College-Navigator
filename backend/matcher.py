"""
FirstStep — TF-IDF Scholarship Matching Model
==============================================
Loads scholarship data from CSV, ranks results against a student
profile using TF-IDF cosine similarity + structured hard filters
+ soft boost scoring.

Usage:
    python model.py                          # runs demo against CSV
    python model.py --csv path/to/data.csv   # custom CSV path

Dependencies:
    pip install pandas scikit-learn
"""

import argparse
import os
import re
import sys

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ──────────────────────────────────────────────────────────────────────────────
# 1. GPA NORMALISATION
# min_gpa in the CSV is free text — "2:1", "Good", "Merit-based", etc.
# Parse what we can into a 0–4.0 scale; anything unrecognisable = 0.0
# (meaning no hard threshold is applied for that scholarship).
# ──────────────────────────────────────────────────────────────────────────────

GPA_TEXT_MAP = {
    # UK honours grades → 4.0 scale
    "first class":      3.7,
    "1st class":        3.7,
    "first":            3.7,
    "1st":              3.7,
    "upper second":     3.3,
    "2:1":              3.3,
    "second class":     3.0,
    "lower second":     2.7,
    "2:2":              2.7,
    # Vague qualitative
    "strong":           3.3,
    "merit-based":      3.0,
    "merit":            3.0,
    "good":             2.7,
    "above average":    2.7,
    "baccalaureate good": 2.7,
    "consistent":       2.5,
    "satisfactory":     2.0,
}


def parse_gpa(raw: str) -> float:
    """
    Convert a free-text min_gpa value to a numeric threshold (0–4.0 scale).
    Returns 0.0 if unrecognisable (= no threshold enforced).
    """
    if not isinstance(raw, str) or not raw.strip():
        return 0.0

    text = raw.lower().strip()

    # "3.0/4.0" or "3.5/4.0"
    m = re.search(r"(\d+\.?\d*)\s*/\s*4", text)
    if m:
        return min(float(m.group(1)), 4.0)

    # Bare number like "3.5" or "35" (treat 35 as 3.5)
    m = re.match(r"^(\d+\.?\d*)$", text)
    if m:
        val = float(m.group(1))
        return val if val <= 4.0 else val / 10.0

    # Keyword lookup — longest keyword wins to avoid "good" beating "baccalaureate good"
    for keyword, score in sorted(GPA_TEXT_MAP.items(), key=lambda x: -len(x[0])):
        if keyword in text:
            return score

    return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# 2. LOAD & PREPARE SCHOLARSHIP DATA
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = [
    "id", "name", "provider", "country", "level", "field_of_study",
    "min_gpa", "funding_type", "value", "deadline", "eligibility",
    "language_req", "description", "apply_url", "source_url",
    "source_type", "collected_by", "date_added",
]

# Columns whose text gets combined into the TF-IDF blob
TEXT_FIELDS = ["field_of_study", "eligibility", "description"]

# Countries / regions considered broadly "Africa-eligible"
AFRICAN_KEYWORDS = [
    "africa", "african", "gambia", "sub-saharan", "west africa",
    "commonwealth", "developing", "least developed",
]


def load_scholarships(path: str) -> pd.DataFrame:
    """
    Load the cleaned scholarship CSV, validate columns, and derive
    the internal columns the model needs.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Scholarship CSV not found: {path}")

    df = pd.read_csv(path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    # Drop rows with no name (blank rows from Excel exports etc.)
    df = df.dropna(subset=["name"]).reset_index(drop=True)

    # Combined text blob for TF-IDF
    df["_text_blob"] = (
        df["field_of_study"].fillna("") + " " +
        df["eligibility"].fillna("") + " " +
        df["description"].fillna("")
    ).str.lower().str.strip()

    # Numeric GPA threshold
    df["_min_gpa_numeric"] = df["min_gpa"].apply(parse_gpa)

    # Flag scholarships that mention Africa / The Gambia in eligibility text
    eligibility_lower = df["eligibility"].fillna("").str.lower()
    df["_africa_eligible"] = eligibility_lower.apply(
        lambda t: any(kw in t for kw in AFRICAN_KEYWORDS)
    )

    # Normalise language_req to lowercase list for easy matching
    df["_languages"] = df["language_req"].fillna("").apply(
        lambda s: [l.strip().lower() for l in re.split(r"[,/;]", s) if l.strip()]
    )

    # Parse deadline to datetime (NaT if invalid)
    df["_deadline_dt"] = pd.to_datetime(df["deadline"], errors="coerce")

    return df


# ──────────────────────────────────────────────────────────────────────────────
# 3. BUILD TF-IDF VECTORISER
# ──────────────────────────────────────────────────────────────────────────────

def build_vectorizer(df: pd.DataFrame):
    """Fit TF-IDF on all scholarship text blobs. Returns (vectorizer, matrix)."""
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),   # unigrams + bigrams capture "computer science" etc.
        min_df=1,
        sublinear_tf=True,    # log-scale TF dampens very common terms
        stop_words="english",
    )
    matrix = vectorizer.fit_transform(df["_text_blob"])
    return vectorizer, matrix


# ──────────────────────────────────────────────────────────────────────────────
# 4. STUDENT PROFILE
# ──────────────────────────────────────────────────────────────────────────────

def make_profile(
    gpa: float,
    courses: list[str],
    interests: list[str],
    location: str = "Gambia",
    level: str = "Any",
    language: str = "English",
) -> dict:
    """
    Build a student profile dict.

    Parameters
    ----------
    gpa       Numeric GPA on a 4.0 scale, e.g. 3.2
    courses   Subjects studied, e.g. ["Computer Science", "Mathematics"]
    interests Topics of interest, e.g. ["AI", "climate change"]
    location  Home country (used for Africa-eligibility boost)
    level     "Undergraduate" / "Masters" / "PhD" / "Any"
    language  Primary language, e.g. "English" / "French"
    """
    query_text = " ".join(courses + interests).lower()
    return {
        "gpa": gpa,
        "courses": courses,
        "interests": interests,
        "location": location.lower(),
        "level": level,
        "language": language.lower(),
        "_query": query_text,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 5. HARD FILTERS
# ──────────────────────────────────────────────────────────────────────────────

def apply_filters(profile: dict, df: pd.DataFrame) -> pd.DataFrame:
    """
    Return only the scholarships that pass hard eligibility filters.

    Filters applied:
      - GPA threshold (scholarship min_gpa <= student gpa, or no threshold)
      - Study level (must match or scholarship accepts "Any")
      - Language (student's language must appear in scholarship language_req,
                  or scholarship has no language requirement listed)
      - Deadline (expired scholarships are dropped if today's date is known)
    """
    mask = pd.Series([True] * len(df), index=df.index)

    # ── GPA ───────────────────────────────────────────────────────────────────
    mask &= (df["_min_gpa_numeric"] == 0.0) | (profile["gpa"] >= df["_min_gpa_numeric"])

    # ── Study level ───────────────────────────────────────────────────────────
    # Scholarship levels are compound strings ("Masters/PhD", "Undergraduate").
    # Expand synonyms so "Bachelors", "Bachelor", "Undergraduate", "Undergrad"
    # all match each other, and similarly for PhD variants.
    _LEVEL_SYNONYMS: dict[str, set[str]] = {
        "bachelors":     {"bachelors", "bachelor", "undergraduate", "undergrad"},
        "bachelor":      {"bachelors", "bachelor", "undergraduate", "undergrad"},
        "undergraduate": {"bachelors", "bachelor", "undergraduate", "undergrad"},
        "undergrad":     {"bachelors", "bachelor", "undergraduate", "undergrad"},
        "phd":           {"phd", "doctorate", "doctoral"},
        "doctorate":     {"phd", "doctorate", "doctoral"},
        "doctoral":      {"phd", "doctorate", "doctoral"},
    }
    if profile["level"].lower() != "any":
        level_lower = df["level"].str.lower().fillna("any")
        raw = profile["level"].lower()
        targets = _LEVEL_SYNONYMS.get(raw, {raw})
        mask &= level_lower.apply(
            lambda s: any(t in s for t in targets) or "any" in s
        )

    # ── Language ──────────────────────────────────────────────────────────────
    student_lang = profile["language"].lower()

    def lang_ok(langs: list) -> bool:
        # Pass if no language requirement listed, OR student's language is in list
        if not langs:
            return True
        return any(student_lang in l or l in student_lang for l in langs)

    mask &= df["_languages"].apply(lang_ok)

    # ── Deadline (drop clearly expired — more than 30 days in the past) ───────
    today = pd.Timestamp.today().normalize()
    cutoff = today - pd.Timedelta(days=30)
    expired = df["_deadline_dt"].notna() & (df["_deadline_dt"] < cutoff)
    mask &= ~expired

    return df[mask].copy()


# ──────────────────────────────────────────────────────────────────────────────
# 6. BOOST SCORING
# Applied on top of TF-IDF cosine similarity as additive bonuses.
# ──────────────────────────────────────────────────────────────────────────────

AFRICA_BOOST   = 0.15   # scholarship explicitly mentions Africa / Gambia
FULLY_FUNDED_BOOST = 0.10  # fully funded scholarships get a nudge
DEADLINE_SOON_BOOST = 0.05 # deadline within 90 days — still open, but urgent
DEADLINE_LATE_PENALTY = -0.05  # deadline over 18 months away — low urgency


def compute_boosts(profile: dict, df: pd.DataFrame) -> pd.Series:
    """Return a Series of additive boost scores aligned to df.index."""
    boosts = pd.Series(0.0, index=df.index)

    # Africa eligibility boost (only meaningful for Gambian students)
    if "gambia" in profile["location"] or "africa" in profile["location"]:
        boosts += df["_africa_eligible"].astype(float) * AFRICA_BOOST

    # Fully funded boost
    fully_funded = df["funding_type"].fillna("").str.lower().str.contains("fully funded")
    boosts += fully_funded.astype(float) * FULLY_FUNDED_BOOST

    # Deadline proximity
    today = pd.Timestamp.today().normalize()
    days_to_deadline = (df["_deadline_dt"] - today).dt.days

    deadline_soon = days_to_deadline.notna() & (days_to_deadline > 0) & (days_to_deadline <= 90)
    deadline_late = days_to_deadline.notna() & (days_to_deadline > 540)  # >18 months

    boosts += deadline_soon.astype(float) * DEADLINE_SOON_BOOST
    boosts += deadline_late.astype(float) * DEADLINE_LATE_PENALTY

    return boosts


# ──────────────────────────────────────────────────────────────────────────────
# 7. MAIN MATCHING FUNCTION
# ──────────────────────────────────────────────────────────────────────────────

OUTPUT_COLUMNS = [
    "id", "name", "provider", "country", "level",
    "funding_type", "deadline", "apply_url",
    "tfidf_score", "boost_score", "final_score",
]


def match(
    profile: dict,
    df: pd.DataFrame,
    vectorizer,
    matrix,
    top_k: int = 5,
) -> pd.DataFrame:
    """
    Rank scholarships against a student profile.

    Returns a DataFrame of top_k results sorted by final_score descending,
    with columns: id, name, provider, country, level, funding_type,
    deadline, apply_url, tfidf_score, boost_score, final_score.
    """
    # ── Step 1: Hard filters ──────────────────────────────────────────────────
    filtered = apply_filters(profile, df)

    if filtered.empty:
        print("[match] Warning: no scholarships passed hard filters.")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # ── Step 2: TF-IDF cosine similarity ─────────────────────────────────────
    query_vec = vectorizer.transform([profile["_query"]])
    sub_matrix = matrix[filtered.index]
    tfidf_scores = cosine_similarity(query_vec, sub_matrix).flatten()
    filtered["tfidf_score"] = tfidf_scores

    # ── Step 3: Soft boost scoring ────────────────────────────────────────────
    filtered["boost_score"] = compute_boosts(profile, filtered).values

    # ── Step 4: Final score = TF-IDF + boosts (capped at 1.0) ────────────────
    filtered["final_score"] = (filtered["tfidf_score"] + filtered["boost_score"]).clip(upper=1.0)

    # ── Step 5: Rank and return ───────────────────────────────────────────────
    results = (
        filtered
        .sort_values("final_score", ascending=False)
        .head(top_k)[OUTPUT_COLUMNS]
        .reset_index(drop=True)
    )

    return results


# ──────────────────────────────────────────────────────────────────────────────
# 8. EVALUATION — precision@k
# ──────────────────────────────────────────────────────────────────────────────

def precision_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """
    precision@k = (# relevant results in top-k) / k

    ranked_ids   — ordered list of scholarship IDs returned by match()
    relevant_ids — set of IDs judged as good matches in ground_truth.csv
    """
    if k <= 0:
        return 0.0
    top_k = ranked_ids[:k]
    hits = sum(1 for id_ in top_k if id_ in relevant_ids)
    return hits / k


def evaluate_from_csv(
    ground_truth_path: str,
    df: pd.DataFrame,
    vectorizer,
    matrix,
    k_values: list[int] = [3, 5],
) -> pd.DataFrame:
    """
    Run precision@k evaluation over all profiles in ground_truth.csv.

    Expected ground_truth.csv columns:
        profile_id, gpa, level, language, courses, interests, location,
        relevant_ids  (semicolon-separated scholarship IDs)

    Returns a DataFrame with one row per profile and columns for each k value.
    """
    if not os.path.exists(ground_truth_path):
        raise FileNotFoundError(f"ground_truth.csv not found: {ground_truth_path}")

    gt = pd.read_csv(ground_truth_path)
    required = ["profile_id", "gpa", "level", "language", "courses", "interests",
                "location", "relevant_ids"]
    missing = [c for c in required if c not in gt.columns]
    if missing:
        raise ValueError(f"ground_truth.csv missing columns: {missing}")

    rows = []
    for _, row in gt.iterrows():
        profile = make_profile(
            gpa=float(row["gpa"]),
            courses=[c.strip() for c in str(row["courses"]).split(";")],
            interests=[i.strip() for i in str(row["interests"]).split(";")],
            location=str(row["location"]),
            level=str(row["level"]),
            language=str(row["language"]),
        )
        relevant = set(str(row["relevant_ids"]).split(";"))
        results = match(profile, df, vectorizer, matrix, top_k=max(k_values))
        ranked_ids = results["id"].tolist()

        result_row = {"profile_id": row["profile_id"]}
        for k in k_values:
            result_row[f"precision@{k}"] = precision_at_k(ranked_ids, relevant, k)
        rows.append(result_row)

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# 9. ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "clean", "scholarships_clean.csv")

DEMO_PROFILES = [
    make_profile(
        gpa=3.2,
        courses=["Computer Science", "Mathematics", "Data Science"],
        interests=["AI", "machine learning", "software engineering"],
        location="Gambia",
        level="Masters",
        language="English",
    ),
    make_profile(
        gpa=2.8,
        courses=["Medicine", "Biology", "Public Health"],
        interests=["healthcare", "global health", "research"],
        location="Gambia",
        level="Any",
        language="English",
    ),
    make_profile(
        gpa=3.5,
        courses=["Environmental Science", "Climate Studies"],
        interests=["climate change", "sustainability", "agriculture"],
        location="Gambia",
        level="Masters",
        language="English",
    ),
]


def run_demo(csv_path: str):
    print("=" * 65)
    print("  FirstStep — Scholarship Matching Model")
    print("=" * 65)

    print(f"\nLoading scholarships from: {csv_path}")
    df = load_scholarships(csv_path)
    print(f"Loaded {len(df)} scholarships.\n")

    vectorizer, matrix = build_vectorizer(df)

    labels = ["CS / AI student", "Medicine / Public Health student", "Climate / Environment student"]

    for profile, label in zip(DEMO_PROFILES, labels):
        print("-" * 65)
        print(f"Profile: {label}")
        print(f"  GPA: {profile['gpa']}  |  Level: {profile['level']}  |  Language: {profile['language']}")
        print(f"  Courses:   {profile['courses']}")
        print(f"  Interests: {profile['interests']}")
        print()

        results = match(profile, df, vectorizer, matrix, top_k=5)

        if results.empty:
            print("  No matches found after filtering.\n")
            continue

        for i, row in results.iterrows():
            print(f"  {i + 1}. [{row['id']}] {row['name']} ({row['country']})")
            print(f"     Final: {row['final_score']:.3f}  "
                  f"(TF-IDF: {row['tfidf_score']:.3f} + boost: {row['boost_score']:.3f})")
            print(f"     {row['funding_type']}  |  Deadline: {row['deadline']}")
            print(f"     Apply: {row['apply_url']}")
            print()

    # GPA parser sanity check
    print("-" * 65)
    print("GPA parser check:")
    test_cases = [
        "Merit-based (no fixed min)",
        "Consistent academic standing",
        "Strong academic record",
        "Min upper second-class (2:1) honours degree",
        "Baccalaureate 'Good' or above",
        "First class honours",
        "3.0/4.0",
    ]
    for raw in test_cases:
        print(f"  '{raw}' → {parse_gpa(raw)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FirstStep TF-IDF Matching Model")
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help="Path to scholarships_clean.csv (default: data/clean/scholarships_clean.csv)",
    )
    parser.add_argument(
        "--eval",
        default=None,
        help="Path to ground_truth.csv to run precision@k evaluation",
    )
    args = parser.parse_args()

    # If the default CSV doesn't exist, fall back to the raw CSV for dev testing
    csv_path = args.csv
    if not os.path.exists(csv_path):
        fallback = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "Scholarships.csv")
        if os.path.exists(fallback):
            print(f"[model] Clean CSV not found, falling back to raw: {fallback}\n")
            csv_path = fallback
        else:
            print(f"[model] ERROR: No CSV found at {csv_path} or {fallback}")
            sys.exit(1)

    run_demo(csv_path)

    if args.eval:
        print("\n" + "=" * 65)
        print("  Evaluation — precision@k")
        print("=" * 65)
        df = load_scholarships(csv_path)
        vectorizer, matrix = build_vectorizer(df)
        eval_results = evaluate_from_csv(args.eval, df, vectorizer, matrix, k_values=[3, 5])
        print(eval_results.to_string(index=False))
        mean_p3 = eval_results["precision@3"].mean()
        mean_p5 = eval_results["precision@5"].mean()
        print(f"\n  Mean precision@3 = {mean_p3:.3f}")
        print(f"  Mean precision@5 = {mean_p5:.3f}")
