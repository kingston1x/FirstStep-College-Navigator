#!/usr/bin/env bash
# FirstStep integrated frontend (real model + data). Run from your repo root:
#   bash setup_firststep_integrated.sh
set -euo pipefail
echo "Writing integrated FirstStep frontend..."
mkdir -p frontend/data frontend/.streamlit
# remove the old mock dataset if present
rm -f frontend/data/scholarships.json

cat > 'frontend/app.py' << 'FS_FILE_EOF'
"""
FirstStep — Scholarship Navigator (front-end)

A student fills in their profile (GPA, courses, interests, preferred
destinations) and gets ranked scholarship matches, each with a plain-language
reason it fits. The ranking comes from recommender.get_recommendations(),
which is a local mock today and becomes Kofi's backend call later — this file
does not change when that swap happens.

Run:  streamlit run app.py
"""

import html

import streamlit as st

from recommender import get_recommendations, available_countries

# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="FirstStep — Scholarship Navigator",
    page_icon="🎓",
    layout="wide",
)

# Destinations are pulled from the actual dataset, so the picker always
# reflects the scholarships we really have.
DESTINATIONS = available_countries()

# --------------------------------------------------------------------------
# Styling — deep navy + gold "departure board" identity
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

    :root {
        --ink:    #0F2A43;
        --gold:   #F4A300;
        --go:     #1E8E6F;
        --muted:  #5B6B7B;
        --line:   #E2E8F0;
        --surface:#FFFFFF;
        --bg:     #F3F5F8;
    }

    .stApp { background: var(--bg); }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--ink); }

    /* Hero band */
    .fs-hero {
        background: linear-gradient(135deg, #0F2A43 0%, #18456B 100%);
        border-radius: 16px;
        padding: 30px 34px;
        margin-bottom: 26px;
        color: #fff;
    }
    .fs-hero h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 2.05rem;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
        color: #fff;
    }
    .fs-hero .accent { color: var(--gold); }
    .fs-hero p { margin: 0; color: #C9D6E3; font-size: 1.02rem; max-width: 640px; }

    /* Section labels */
    .fs-eyebrow {
        font-family: 'Space Grotesk', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-size: 0.72rem;
        font-weight: 600;
        color: var(--muted);
        margin-bottom: 10px;
    }

    /* Result card */
    .fs-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 20px 22px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px rgba(15,42,67,0.04);
    }
    .fs-card-top {
        display: flex; justify-content: space-between;
        align-items: flex-start; gap: 16px;
    }
    .fs-card h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.18rem; font-weight: 600;
        margin: 0 0 2px 0; color: var(--ink);
    }
    .fs-provider { color: var(--muted); font-size: 0.86rem; margin-bottom: 12px; }

    /* Destination tag */
    .fs-dest {
        display: inline-block; white-space: nowrap;
        background: #EAF1F7; color: var(--ink);
        font-size: 0.74rem; font-weight: 600;
        padding: 5px 11px; border-radius: 999px;
        font-family: 'Space Grotesk', sans-serif;
    }

    /* Match meter (the signature element) */
    .fs-meter-wrap { margin: 4px 0 14px 0; }
    .fs-meter-label {
        display: flex; justify-content: space-between;
        font-size: 0.74rem; color: var(--muted);
        margin-bottom: 5px; font-weight: 500;
    }
    .fs-meter-score { color: var(--gold); font-weight: 700; }
    .fs-meter-track {
        height: 8px; background: #ECEFF3;
        border-radius: 999px; overflow: hidden;
    }
    .fs-meter-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--gold) 0%, #FFC44D 100%);
        border-radius: 999px;
    }

    /* Why-it-fits line */
    .fs-why {
        background: #FBF6EC;
        border-left: 3px solid var(--gold);
        padding: 11px 14px; border-radius: 8px;
        font-size: 0.92rem; color: #4A3A14;
        margin-bottom: 14px; line-height: 1.5;
    }
    .fs-why b { color: var(--ink); }

    /* Fact grid */
    .fs-facts { display: flex; flex-wrap: wrap; gap: 10px 26px; margin-bottom: 16px; }
    .fs-fact { font-size: 0.86rem; }
    .fs-fact .k {
        display: block; color: var(--muted);
        font-size: 0.7rem; text-transform: uppercase;
        letter-spacing: 0.6px; margin-bottom: 2px;
    }
    .fs-fact .v { color: var(--ink); font-weight: 500; }

    /* Apply button */
    .fs-apply {
        display: inline-block; text-decoration: none;
        background: var(--ink); color: #fff !important;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600; font-size: 0.9rem;
        padding: 9px 18px; border-radius: 9px;
        transition: background 0.15s ease;
    }
    .fs-apply:hover { background: var(--go); }

    /* Empty / intro state */
    .fs-empty {
        background: var(--surface); border: 1px dashed var(--line);
        border-radius: 14px; padding: 40px 30px; text-align: center;
        color: var(--muted);
    }
    .fs-empty .big { font-size: 2rem; margin-bottom: 8px; }

    /* Tighten Streamlit's default form chrome a little */
    div[data-testid="stForm"] {
        background: var(--surface); border: 1px solid var(--line);
        border-radius: 14px; padding: 6px 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Hero
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="fs-hero">
        <h1>FirstStep<span class="accent">.</span></h1>
        <p>Tell us where you stand and where you want to go, and we'll rank the
        scholarships that fit you best from across our database — and explain why
        each one made the list.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Layout: profile (left)  |  matches (right)
# --------------------------------------------------------------------------
left, right = st.columns([0.95, 1.55], gap="large")

with left:
    st.markdown('<div class="fs-eyebrow">Your profile</div>', unsafe_allow_html=True)
    with st.form("profile_form"):
        gpa = st.slider(
            "GPA (4.0 scale)", min_value=0.0, max_value=4.0, value=3.0, step=0.1,
            help="Use your cumulative GPA on a 4.0 scale.",
        )
        courses = st.text_input(
            "Courses / field of study",
            placeholder="e.g. computer science, mathematics, data science",
        )
        interests = st.text_input(
            "Interests",
            placeholder="e.g. AI, software engineering, research",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            level = st.selectbox(
                "Study level",
                options=["Any", "Bachelors", "Masters", "PhD"],
                index=0,
                help="The level of study you're applying for.",
            )
        with col_b:
            language = st.selectbox(
                "Language",
                options=["English", "French", "German"],
                index=0,
                help="Your primary language of study.",
            )
        locations = st.multiselect(
            "Preferred destinations",
            options=DESTINATIONS,
            default=[],
            help="Leave empty to consider every destination in the dataset.",
        )
        submitted = st.form_submit_button("Find my scholarships", type="primary")

    st.caption(
        "Tip: filling in courses and interests sharpens the match. "
        "Study level and language filter out scholarships you can't apply to."
    )

with right:
    st.markdown('<div class="fs-eyebrow">Your matches</div>', unsafe_allow_html=True)

    if not submitted:
        st.markdown(
            """
            <div class="fs-empty">
                <div class="big">🧭</div>
                <div>Fill in your profile and press <b>Find my scholarships</b>.<br>
                Your ranked matches will appear here.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        profile = {
            "gpa": gpa,
            "courses": courses,
            "interests": interests,
            "locations": locations,
            "level": level,
            "language": language,
        }
        results = get_recommendations(profile, top_k=8)

        if not results:
            st.markdown(
                '<div class="fs-empty">No scholarships matched your profile. '
                'Try widening your study level, language, or destinations.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption(f"Showing the top {len(results)} matches, strongest first.")
            for r in results:
                s = r["scholarship"]
                # Display scaling: raw TF-IDF scores sit ~0.1-0.5, so a strong
                # match (~0.5) reads as 100%. match_score itself stays raw.
                pct = min(int(round(r["match_score"] / 0.5 * 100)), 100)
                why = html.escape(r["explanation"])

                def fact(label, value):
                    return (
                        f'<div class="fs-fact"><span class="k">{html.escape(label)}</span>'
                        f'<span class="v">{html.escape(str(value))}</span></div>'
                    )

                facts = "".join([
                    fact("Level", s.get("level", "—")),
                    fact("Funding", s.get("funding_type", "—")),
                    fact("Deadline", s.get("deadline", "—")),
                    fact("GPA / grade", s.get("min_gpa", "—")),
                ])

                card = f"""
                <div class="fs-card">
                    <div class="fs-card-top">
                        <div>
                            <h3>{html.escape(s.get("name", "Untitled"))}</h3>
                            <div class="fs-provider">{html.escape(s.get("provider", ""))}</div>
                        </div>
                        <span class="fs-dest">📍 {html.escape(s.get("country", ""))}</span>
                    </div>
                    <div class="fs-meter-wrap">
                        <div class="fs-meter-label">
                            <span>Match strength</span>
                            <span class="fs-meter-score">{pct}%</span>
                        </div>
                        <div class="fs-meter-track">
                            <div class="fs-meter-fill" style="width:{pct}%;"></div>
                        </div>
                    </div>
                    <div class="fs-why"><b>Why this fits you:</b> {why}</div>
                    <div class="fs-facts">{facts}</div>
                    <a class="fs-apply" href="{html.escape(s.get("apply_url", "#"))}"
                       target="_blank" rel="noopener noreferrer">Apply / learn more →</a>
                </div>
                """
                st.markdown(card, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "FirstStep · Scholarship & College Navigator for Gambian students. "
    "Scholarship details are indicative — always confirm deadlines and eligibility "
    "on the official site before applying."
)
FS_FILE_EOF

cat > 'frontend/recommender.py' << 'FS_FILE_EOF'
"""
recommender.py — adapter between the Streamlit UI and Cday's TF-IDF model.

The UI calls get_recommendations(profile, top_k) and gets back results in the
DATA_CONTRACT shape: { scholarship, match_score, explanation }. Internally this
now drives the REAL model (matcher.py) over the cleaned dataset — no mock.

Flow:
  UI profile  ->  matcher.make_profile  ->  matcher.match (TF-IDF + filters)
              ->  destination post-filter  ->  join back to full records
              ->  contract shape for the UI
"""

from __future__ import annotations

import functools
import os
from typing import Any

import pandas as pd

import matcher  # Cday's fixed TF-IDF model

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "scholarships_clean.csv")

# 18 columns the UI may display
SCHEMA = [
    "id", "name", "provider", "country", "level", "field_of_study", "min_gpa",
    "funding_type", "value", "deadline", "eligibility", "language_req",
    "description", "apply_url", "source_url", "source_type", "collected_by",
    "date_added",
]


@functools.lru_cache(maxsize=1)
def _load():
    """Load dataset + fit the TF-IDF vectorizer once (cached)."""
    df = matcher.load_scholarships(DATA_PATH)
    vec, mat = matcher.build_vectorizer(df)
    return df, vec, mat


def available_countries() -> list[str]:
    """Distinct destination countries present in the dataset (for the picker)."""
    df, _, _ = _load()
    return sorted({str(c).strip() for c in df["country"].dropna() if str(c).strip()})


def _split(text: str) -> list[str]:
    """Split a comma/semicolon string into a clean list."""
    return [t.strip() for t in str(text or "").replace(";", ",").split(",") if t.strip()]


def _explanation(row: pd.Series, query_terms: set[str]) -> str:
    """
    Plain-language 'why this fits' line. Placeholder for Kofi's LLM layer —
    the UI just displays this string, so swapping it later changes nothing here.
    """
    bits: list[str] = []
    blob = f"{row.get('field_of_study','')} {row.get('description','')}".lower()
    shared = sorted({t for t in query_terms if len(t) > 2 and t in blob})
    if shared:
        bits.append(f"it lines up with your interest in {', '.join(shared[:3])}")
    if "fully funded" in str(row.get("funding_type", "")).lower():
        bits.append("it's fully funded")
    country = str(row.get("country", "")).strip()
    if country and country.lower() not in ("various", "online"):
        bits.append(f"it's based in {country}")
    if not bits:
        return f"A general fit for your profile — check the eligibility for {row.get('name','this scholarship')}."
    s = "; ".join(bits)
    return s[0].upper() + s[1:] + "."


def get_recommendations(profile: dict[str, Any], top_k: int = 8) -> list[dict[str, Any]]:
    """
    Rank scholarships for a student profile using the real model.

    profile keys:
        gpa        float (4.0 scale)
        courses    str   (comma-separated)
        interests  str   (comma-separated)
        locations  list[str]  preferred destination countries (empty = all)
        level      str   ("Any" / "Bachelors" / "Masters" / "PhD")
        language   str   ("English" / "French" / ...)

    Returns list of { scholarship: {...18 fields}, match_score: float, explanation: str }
    sorted by match strength. Non-qualifying scholarships are hidden by the model's
    hard filters (strict mode).
    """
    df, vec, mat = _load()

    courses = _split(profile.get("courses"))
    interests = _split(profile.get("interests"))

    cday_profile = matcher.make_profile(
        gpa=float(profile.get("gpa") or 0.0),
        courses=courses,
        interests=interests,
        location="Gambia",  # home country (drives the Africa-eligibility boost)
        level=(profile.get("level") or "Any"),
        language=(profile.get("language") or "English"),
    )

    # Rank everything that passes the hard filters, then post-filter by destination.
    ranked = matcher.match(cday_profile, df, vec, mat, top_k=len(df))
    if ranked.empty:
        return []

    prefs = {c.strip().lower() for c in profile.get("locations", []) if str(c).strip()}
    query_terms = set(" ".join(courses + interests).lower().split())
    by_id = {r["id"]: r for _, r in df.iterrows()}

    results: list[dict[str, Any]] = []
    for _, r in ranked.iterrows():
        full = by_id.get(r["id"])
        if full is None:
            continue
        country = str(full.get("country", ""))
        if prefs and country.lower() not in prefs:
            continue
        scholarship = {k: ("" if pd.isna(full.get(k)) else full.get(k)) for k in SCHEMA}
        results.append({
            "scholarship": scholarship,
            "match_score": float(r["final_score"]),
            "explanation": _explanation(full, query_terms),
        })
        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    demo = {"gpa": 3.2, "courses": "Computer Science, Data Science",
            "interests": "AI, software engineering", "locations": [],
            "level": "Masters", "language": "English"}
    for r in get_recommendations(demo, top_k=5):
        s = r["scholarship"]
        print(f"{r['match_score']:.3f}  {s['name']} ({s['country']})")
        print(f"        {r['explanation']}")
FS_FILE_EOF

cat > 'frontend/matcher.py' << 'FS_FILE_EOF'
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
    # FIX: scholarship levels are compound strings ("Masters/PhD",
    # "Bachelors/Masters"), so use substring matching instead of exact equality.
    if profile["level"].lower() != "any":
        level_lower = df["level"].str.lower().fillna("any")
        target = profile["level"].lower()
        mask &= level_lower.apply(lambda s: target in s or "any" in s)

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

# Boosts are deliberately SMALL so TF-IDF text relevance leads the ranking and
# boosts only nudge near-ties. (Previously these were 0.15/0.10, large enough to
# outrank genuine topic relevance — a fully-funded but off-topic scholarship
# could beat an on-topic one. Reduced so relevance dominates.)
AFRICA_BOOST   = 0.05   # scholarship explicitly mentions Africa / Gambia
FULLY_FUNDED_BOOST = 0.03  # fully funded scholarships get a small nudge
DEADLINE_SOON_BOOST = 0.02 # deadline within 90 days — still open, but urgent
DEADLINE_LATE_PENALTY = -0.02  # deadline over 18 months away — low urgency


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

DEFAULT_CSV = os.path.join(
    os.path.dirname(__file__), "data", "clean", "scholarships_clean.csv"
)

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
        fallback = os.path.join(os.path.dirname(__file__), "data", "raw", "Scholarships.csv")
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
FS_FILE_EOF

cat > 'frontend/requirements.txt' << 'FS_FILE_EOF'
streamlit>=1.30
pandas>=2.0
scikit-learn>=1.3
FS_FILE_EOF

cat > 'frontend/README.md' << 'FS_FILE_EOF'
# FirstStep — Front-end

The Streamlit interface for FirstStep, the scholarship navigator for Gambian
students. A student enters their profile (GPA, courses, interests, study level,
language, preferred destinations) and gets ranked scholarship matches, each with
a plain-language reason it fits.

Owner: Joshua · Part of the FirstStep group project.

## Run it
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

## Files
| File | Purpose |
|------|---------|
| `app.py` | The Streamlit UI — profile form + ranked result cards. |
| `recommender.py` | Adapter: turns the UI profile into a model call and the model output into card data. |
| `matcher.py` | Cday's TF-IDF model (level filter + boosts fixed). Does the actual ranking. |
| `data/scholarships_clean.csv` | The 34-scholarship dataset (single source of truth). |
| `.streamlit/config.toml` | Theme. |

## How it fits together
UI → `recommender.get_recommendations(profile)` → `matcher.match()` (TF-IDF +
hard filters + boosts) → results joined back to full records → cards.

The model HIDES scholarships a student doesn't qualify for (strict mode). The
"why this fits" text is generated in `recommender.py` for now and is the seam
where Kofi's LLM explanation layer plugs in later — `app.py` won't change.

Scholarship details are indicative; always confirm on the official site.
FS_FILE_EOF

cat > 'frontend/data/scholarships_clean.csv' << 'FS_FILE_EOF'
id,name,provider,country,level,field_of_study,min_gpa,funding_type,value,deadline,eligibility,language_req,description,apply_url,source_url,source_type,collected_by,date_added
SCH-008,DAAD Scholarships in Germany for Development-Related Postgraduate Courses,DAAD,Germany,Masters/PhD,Economics; Public Policy; Development Studies; Engineering; Public Health; Agriculture; Environmental Sciences,Good academic standing,Fully Funded,"Monthly stipend, tuition, travel allowance, health insurance",Aug-Oct 2026 (annual),Open to graduates from developing countries including African and Gambian students; usually requires two years of relevant work experience,English/German,"DAAD-funded master's and PhD scholarships at German universities in development-related fields, for professionals from developing countries who want to drive sustainable development at home. Fully funded with stipend, tuition and travel.",https://www.scholars4dev.com/1002/daad-scholarships-for-postgraduate-courses-with-special-relevance-to-developing-countries/,https://www.scholars4dev.com/1002/daad-scholarships-for-postgraduate-courses-with-special-relevance-to-developing-countries/,Official,Emmanuel,2026-06-29
SCH-009,Rhodes Scholarships at Oxford University for International Students,Rhodes Scholarship Fund,UK,Masters/PhD,Any field of study offered at the University of Oxford,Good academic standing,Fully Funded,"Full tuition and college fees, annual living stipend, airfare","varies, July-Oct 2026 (annual)",Outstanding international students with a strong academic record and proven leadership; age and country eligibility apply,English,"The Rhodes Scholarship funds exceptional students for postgraduate study at the University of Oxford, selecting on academic excellence, leadership and service. Fully funded covering fees, a living stipend and travel.",https://www.scholars4dev.com/3667/rhodes-international-scholarships-at-oxford-university/,https://www.scholars4dev.com/3667/rhodes-international-scholarships-at-oxford-university/,Official,Emmanuel,2026-06-29
SCH-010,University of Sydney International Stipend Scholarship (USYDIS),University of Sydney,Australia,Masters/PhD,Research-based Master's and PhD across all disciplines,Good academic standing,Stipend,Living-allowance stipend for the duration of research study,11 Sept/18 Dec 2026,International students undertaking research degrees who meet admission and academic merit requirements,English,"A living-allowance stipend supporting international students pursuing research master's or PhD study at the University of Sydney, awarded on academic merit across all research disciplines.",https://www.scholars4dev.com/2053/international-scholarships-at-university-of-sydney/,https://www.scholars4dev.com/2053/international-scholarships-at-university-of-sydney/,Official,Emmanuel,2026-06-29
SCH-011,Fulbright Foreign Student Program in USA,USA Government,US,Masters/PhD,Most academic fields except clinical medicine,Good academic standing,Fully Funded,"Tuition, living stipend, airfare, health benefits","varies, Feb-Oct 2026",Non-US graduate students and young professionals; applied through the US Embassy in the home country; commitment to return home after study,English,"The US government's flagship Fulbright program funds international students for graduate study in the United States, selecting on academic merit and leadership. Fully funded and applied for through the home-country US Embassy.",https://www.scholars4dev.com/2876/usa-fulbright-scholarships-for-international-students/,https://www.scholars4dev.com/2876/usa-fulbright-scholarships-for-international-students/,Official,Emmanuel,2026-06-29
SCH-012,DAAD Helmut-Schmidt Masters Scholarships for Public Policy and Good Governance,DAAD,Germany,Masters,Public Policy; Good Governance; Political Science; Public Administration; Law; Economics; Development,Good academic standing,Fully Funded,"Monthly stipend, tuition, travel, health insurance",31 July 2026 (annual),Graduates from developing countries committed to public-sector and governance careers in their home country,English,"A fully funded DAAD master's scholarship in public policy and good governance for future leaders from developing countries, designed to strengthen democratic governance and development back home.",https://www.scholars4dev.com/1010/daad-ms-scholarships-for-public-policy-and-good-governance-ppgg/,https://www.scholars4dev.com/1010/daad-ms-scholarships-for-public-policy-and-good-governance-ppgg/,Official,Emmanuel,2026-06-29
SCH-013,Adelaide Global Academic Excellence Scholarships for International Students,University of Adelaide,Australia,Bachelors/Masters,Most undergraduate and postgraduate coursework programs,Good academic standing,Partial,Partial tuition fee reduction based on academic merit,22 May 2026 (annual),High-achieving international students who meet the University of Adelaide entry requirements,English,"A merit-based tuition reduction for high-achieving international students at the University of Adelaide, awarded automatically on academic results across most programs.",https://www.scholars4dev.com/6711/university-of-adelaide-scholarships-for-international-students/,https://www.scholars4dev.com/6711/university-of-adelaide-scholarships-for-international-students/,Official,Emmanuel,2026-06-29
SCH-014,University of New South Wales International Scholarships,University of New South Wales,Australia,Bachelors/Masters,Most undergraduate and postgraduate programs,Good academic standing,Partial,Partial tuition scholarship awarded on academic merit,18 June 2026 (Annual),International students with strong academic results who meet UNSW entry requirements,English,"Merit-based tuition scholarships for international students at UNSW Sydney, recognising strong academic achievement across a wide range of programs.",https://www.scholars4dev.com/23382/unsw-international-scholarships/,https://www.scholars4dev.com/23382/unsw-international-scholarships/,Official,Emmanuel,2026-06-29
SCH-015,The Glenmore Medical Postgraduate Scholarship at the University of Edinburgh,University of Edinburgh,UK,Masters,Medicine; Medical Sciences; Public Health; Clinical postgraduate programs,Good academic standing,Partial,Contribution towards postgraduate medical tuition fees,28 May 2026 (annual),International postgraduate students admitted to eligible medical programmes at the University of Edinburgh,English,"A postgraduate award for international students studying medicine and medical sciences at the University of Edinburgh, contributing towards tuition for taught medical master's programmes.",https://www.scholars4dev.com/15839/the-glenmore-medical-postgraduate-scholarship-at-the-university-of-edinburgh/,https://www.scholars4dev.com/15839/the-glenmore-medical-postgraduate-scholarship-at-the-university-of-edinburgh/,Official,Emmanuel,2026-06-29
SCH-016,Bocconi Graduate Graduate Award,Bocconi University,Italy,Masters,Economics; Finance; Management; Business; Data Science; Law,Good academic standing,Partial,Full or partial tuition waiver based on merit and need,2026-04-29,International students admitted to Bocconi master's programmes; awarded on merit and financial need,English,"Merit- and need-based tuition awards for international students in economics, finance, management and data science master's programmes at Bocconi University in Milan.",https://www.scholars4dev.com/7574/scholarships-in-italy-for-international-students-at-bocconi-univiersity/,https://www.scholars4dev.com/7574/scholarships-in-italy-for-international-students-at-bocconi-univiersity/,Official,Emmanuel,2026-06-29
SCH-017,Australia Research Training Program (RTP) Scholarships,Australian Government,Australia,Masters/PhD,Research Master's and PhD across all disciplines,Good academic standing,Fully Funded,"Tuition offset, living stipend, health cover","varies, April-Oct (annual)",Domestic and international students undertaking research degrees at participating Australian universities,English,Australian Government Research Training Program scholarships fund research master's and PhD students with tuition support and a living stipend at Australian universities across all research fields.,https://www.scholars4dev.com/3023/international-postgraduate-scholarships-at-australian-universities/,https://www.scholars4dev.com/3023/international-postgraduate-scholarships-at-australian-universities/,Official,Emmanuel,2026-06-29
SCH-018,IOE Centenary Masters Scholarships,IOE/ISH,UK,Masters,Education; Teaching; Pedagogy; Social Sciences,Good academic standing,Fully Funded,Tuition fees and accommodation,4 May 2026 (annual),"Students from developing countries admitted to a UCL Institute of Education master's, not ordinarily resident in the UK",English,"Fully funded master's scholarships at UCL's Institute of Education in London for students from lower-income countries, covering tuition and accommodation, focused on education and teaching.",https://www.scholars4dev.com/10515/ioe-ish-centenary-masters-scholarships-for-international-students/,https://www.scholars4dev.com/10515/ioe-ish-centenary-masters-scholarships-for-international-students/,Official,Emmanuel,2026-06-29
SCH-019,Italian Government Scholarships for Foreign Students,Italian Government,Italy,Masters/PhD,Arts; Sciences; Engineering; Humanities; Music; Design,Good academic standing,Stipend,"Monthly maintenance allowance, tuition fee exemption, health insurance",26 March 2026 (annual),International students and researchers; some programmes require Italian language proficiency,Italian/English,"Italian Government scholarships for foreign students offering a monthly allowance, tuition exemption and insurance for study at Italian universities and institutes across many disciplines.",https://www.scholars4dev.com/3282/italian-government-scholarships-for-international-students/,https://www.scholars4dev.com/3282/italian-government-scholarships-for-international-students/,Official,Emmanuel,2026-06-29
SCH-020,Padua International Excellence Scholarship Programme,University of Padua,Italy,Bachelors/Masters,Most master's and bachelor's degree programmes,Good academic standing,Partial,Annual scholarship instalments based on merit,10 Apr/2 May 2026 (annual),High-achieving international students enrolling at the University of Padua,English/Italian,"Merit scholarships for outstanding international students at the University of Padua, paid as annual instalments across a broad range of bachelor's and master's programmes.",https://www.scholars4dev.com/23000/padova-international-excellence-scholarship-programme/,https://www.scholars4dev.com/23000/padova-international-excellence-scholarship-programme/,Official,Emmanuel,2026-06-29
SCH-021,Glasgow International Leadership Scholarships,Glasgow University,UK,Masters,Most postgraduate taught master's programmes,Good academic standing,Partial,Tuition fee discount for international students,admissions deadline (annual),International students holding an offer for an eligible Glasgow master's programme,English,"A tuition discount for international postgraduate students at the University of Glasgow, recognising academic excellence and leadership across most taught master's programmes.",https://www.scholars4dev.com/22676/glasgow-international-leadership-scholarship/,https://www.scholars4dev.com/22676/glasgow-international-leadership-scholarship/,Official,Emmanuel,2026-06-29
SCH-022,Melbourne International Undergraduate Scholarships,University of Melbourne,Australia,Bachelors,Undergraduate programs across all faculties,Good academic standing,Partial,Partial tuition fee remission based on merit,31 May/31 Oct 2026,International undergraduate students with outstanding academic results,English,"Merit-based tuition scholarships for international undergraduate students at the University of Melbourne, awarded on academic excellence across all faculties.",https://www.scholars4dev.com/16130/melbourne-international-undergraduate-scholarships/,https://www.scholars4dev.com/16130/melbourne-international-undergraduate-scholarships/,Official,Emmanuel,2026-06-29
SCH-023,Rotary Foundation Global Scholarship Grants for Development,Rotary Foundation,Various,Masters/PhD,Peacebuilding; Disease prevention; Water and sanitation; Maternal and child health; Education; Economic and community development; Environment,Good academic standing,Fully Funded,Funds tuition and related costs for graduate study in a Rotary area of focus,Rolling**,Graduate students whose study aligns with a Rotary area of focus and who are sponsored by a local Rotary club,English,"Rotary Foundation global grants fund graduate study and projects addressing Rotary's areas of focus such as health, clean water, education and community development, in partnership with local Rotary clubs.",https://www.scholars4dev.com/3902/rotary-international-ambassadorial-scholarships/,https://www.scholars4dev.com/3902/rotary-international-ambassadorial-scholarships/,Official,Emmanuel,2026-06-29
SCH-024,UAL/ISH International Postgraduate Scholarships,University of the Arts London,UK,Masters,Art; Design; Fashion; Media; Communication; Creative Arts,Good academic standing,Partial,Tuition contribution and accommodation support,27 March/26 June 2026 (annual),International postgraduate students at University of the Arts London facing financial need,English,"Scholarships for international postgraduate students at University of the Arts London in art, design and media, offering tuition support and accommodation for talented creatives.",https://www.scholars4dev.com/11659/ishual-graduate-scholarships-for-international-students/,https://www.scholars4dev.com/11659/ishual-graduate-scholarships-for-international-students/,Official,Emmanuel,2026-06-29
SCH-026,University of the People Online Tuition Free Degrees,University of the People,Online,Bachelors,Computer Science; Business Administration; Health Science; Education,Good academic standing,Tuition-Free,Tuition-free online degrees; small assessment fees may apply,19 Mar/28 May 2026 (annual),"Students worldwide with a high-school qualification and English proficiency, including students in The Gambia",English,"An accredited, tuition-free online university offering degrees in computer science, business, health science and education, making higher education accessible to students anywhere, including across Africa.",https://www.scholars4dev.com/3630/free-online-education-at-university-of-the-people/,https://www.scholars4dev.com/3630/free-online-education-at-university-of-the-people/,Official,Emmanuel,2026-06-29
SCH-027,Manaaki New Zealand Scholarships for International Students,NZAID,New Zealand,Bachelors/Masters/PhD,Sustainable Development; Agriculture; Public Sector; Renewable Energy; Health; Education,Good academic standing,Fully Funded,"Tuition, living allowance, airfare, establishment grant, insurance",31 March 2026 (annual),"Citizens of eligible developing countries including African nations, committed to returning home to contribute to development",English,"New Zealand Government scholarships funding students from developing countries, including Africa, for study in fields tied to home-country development. Fully funded with tuition, living costs and travel.",https://www.scholars4dev.com/2786/new-zealand-development-scholarships-for-africans-asians-latin-americans-and-pacific-islanders/,https://www.scholars4dev.com/2786/new-zealand-development-scholarships-for-africans-asians-latin-americans-and-pacific-islanders/,Official,Emmanuel,2026-06-29
SCH-028,Aga Khan Foundation International Scholarship Programme,Aga Khan Foundation,Various,Masters/PhD,Most postgraduate fields,Good academic standing,Partial,50% grant and 50% loan covering tuition and living costs,31 Mar 2026 (annual),"Outstanding students from selected developing countries with no other means of funding, at postgraduate level",English/French,"The Aga Khan Foundation International Scholarship Programme supports outstanding postgraduate students from developing countries on a 50% grant, 50% loan basis, for study in any field.",https://www.scholars4dev.com/2467/aga-khan-international-scholarships-for-developing-countrie/,https://www.scholars4dev.com/2467/aga-khan-international-scholarships-for-developing-countrie/,Official,Emmanuel,2026-06-29
SCH-029,Australia Awards Scholarships,Australian Government,Australia,Bachelors/Masters/PhD,Health; Education; Governance; Infrastructure; Agriculture; Development,Good academic standing,Fully Funded,"Full tuition, return airfare, living allowance, health cover",30 April 2026 (annual),"Citizens of eligible developing countries including African nations, committed to contributing to development at home",English,"Australia Awards are fully funded Australian Government scholarships for students from developing countries, including Africa, prioritising fields linked to home-country development. Covers tuition, travel and living costs.",https://www.scholars4dev.com/3253/australia-awards-scholarships/,https://www.scholars4dev.com/3253/australia-awards-scholarships/,Official,Emmanuel,2026-06-29
SCH-030,Government of Flanders Master Mind Scholarships for International Students,Government of Flanders,Belgium,Masters,All master's programmes at Flemish universities,Good academic standing,Partial,Annual grant towards tuition and living costs,Feb-April 2026 (annual),Outstanding international students enrolling in a master's programme in Flanders,English,"Government of Flanders scholarships rewarding outstanding international students for master's study at Flemish universities in Belgium, contributing to tuition and living costs.",https://www.scholars4dev.com/14865/government-of-flanders-master-mind-scholarships-for-international-students/,https://www.scholars4dev.com/14865/government-of-flanders-master-mind-scholarships-for-international-students/,Official,Emmanuel,2026-06-29
SCH-031,Science@Leuven Scholarships for International Students,K.U. Leuven Faculty of Science,Belgium,Masters,Science; Mathematics; Physics; Chemistry; Biology; Computer Science,Good academic standing,Partial,Full or partial scholarship towards tuition and living costs,15 Feb 2026 (annual),International students with excellent results applying to a master's in the Faculty of Science at KU Leuven,English,"Scholarships for international students pursuing a master's in the sciences at KU Leuven in Belgium, awarded on academic excellence and covering part or all of study costs.",https://www.scholars4dev.com/3222/science-scholarships-for-international-students-at-ku-leuven/,https://www.scholars4dev.com/3222/science-scholarships-for-international-students-at-ku-leuven/,Official,Emmanuel,2026-06-29
SCH-032,Université Paris-Saclay International Master’s Scholarships,Université Paris-Saclay,France,Masters,Science; Engineering; Mathematics; Computer Science; Economics,Good academic standing,Stipend,Monthly stipend for the duration of the master's programme,25/31 March 2026 (annual),International students admitted to an eligible Paris-Saclay master's programme,English/French,"Universite Paris-Saclay offers monthly-stipend scholarships to international master's students in science, engineering and related fields at one of France's leading research universities.",https://www.scholars4dev.com/15259/universite-paris-saclay-international-masters-scholarships-2/,https://www.scholars4dev.com/15259/universite-paris-saclay-international-masters-scholarships-2/,Official,Emmanuel,2026-06-29
SCH-033,Joint Japan World Bank Graduate Scholarship Program,Japan Gov’t/World Bank,Various,Masters,Economics; Public Policy; Health; Education; Infrastructure; Development,Good academic standing,Fully Funded,"Tuition, monthly living stipend, airfare, health insurance",27 Feb/29 May 2026 (annual),Professionals from developing countries with several years of development-related work experience pursuing a development-related master's,English,"The Joint Japan/World Bank Graduate Scholarship Program fully funds mid-career professionals from developing countries for a development-related master's, building expertise that supports home-country development.",https://www.scholars4dev.com/2735/japan-world-bank-graduate-scholarships-for-development-related-studies/,https://www.scholars4dev.com/2735/japan-world-bank-graduate-scholarships-for-development-related-studies/,Official,Emmanuel,2026-06-29
SCH-034,VLIR-UOS ICP Connect Scholarships in Belgium,VLIR-UOS,Belgium,Masters,Public Health; Agriculture; Water; Governance; Development-relevant Master's,Good academic standing,Fully Funded,"Tuition, living allowance, travel, insurance",1/28 Feb 2026 (annual),"Students from eligible developing countries, including African nations, applying to selected master's programmes in Flanders",English,"VLIR-UOS scholarships fully fund students from developing countries for development-focused master's programmes at universities in Flanders, Belgium, to help tackle global development challenges.",https://www.scholars4dev.com/2257/vlir-uos-masters-scholarships-for-developing-countries/,https://www.scholars4dev.com/2257/vlir-uos-masters-scholarships-for-developing-countries/,Official,Emmanuel,2026-06-29
SCH-035,University of Geneva Excellence Masters Fellowships,University of Geneva,Switzerland,Masters,Science; Chemistry; Physics; Biology; Computer Science; Mathematics,Good academic standing,Stipend,Per-semester excellence fellowship towards study costs,28 Feb 2026 (annual),Top international students admitted to a Faculty of Science master's at the University of Geneva,English/French,"Excellence fellowships for outstanding international students in the sciences at the University of Geneva, providing a per-semester stipend to support master's study in Switzerland.",https://www.scholars4dev.com/13822/university-of-geneva-excellence-masters-fellowships/,https://www.scholars4dev.com/13822/university-of-geneva-excellence-masters-fellowships/,Official,Emmanuel,2026-06-29
SCH-036,York University International Student Scholarships,York University,Canada,Bachelors,Undergraduate programs across faculties,Good academic standing,Partial,Renewable entrance scholarship towards tuition,26 Jan 2026 (annual),High-achieving international undergraduate applicants to York University,English,"Renewable entrance scholarships for high-achieving international undergraduate students at York University in Canada, recognising academic excellence across faculties.",https://www.scholars4dev.com/3410/international-undergraduate-scholarships-at-york-university/,https://www.scholars4dev.com/3410/international-undergraduate-scholarships-at-york-university/,Official,Emmanuel,2026-06-29
SCH-037,Macquarie Vice-Chancellor’s International Scholarships,Macquarie University,Australia,Bachelors/Masters,Most undergraduate and postgraduate coursework programs,Good academic standing,Partial,Partial tuition scholarship awarded on merit,Ongoing (annual),International students with strong academic results commencing at Macquarie University,English,Macquarie University Vice-Chancellor's scholarships offer partial tuition support to international students with strong academic records across most coursework programs.,https://www.scholars4dev.com/1398/macquarie-university-scholarships-for-international-students/,https://www.scholars4dev.com/1398/macquarie-university-scholarships-for-international-students/,Official,Emmanuel,2026-06-29
SCH-002,Chinese Government Scholarship (CSC),China Scholarship Council,China,Any,Engineering; Computer Science; Medicine (MBBS); Business; Agriculture,Consistent academic standing,Fully Funded,Tuition + accommodation + monthly stipend + insurance,2026-03-31,Open to non-Chinese citizens; African students eligible via Type A/B routes,Chinese Or English,"China's national fully funded scholarship covering tuition, housing and stipend.",https://www.campuschina.org,https://www.campuschina.org,Official,Joshua,2026-06-23
SCH-003,Moroccan Government Scholarship (AMCI),Agence Marocaine de Coopération Internationale,Morocco,Any,Science; Engineering; Humanities; Social Sciences; Medicine,Good academic standing,Fully Funded,Tuition + housing support + healthcare,2026-07-22,Available through partner-country nominations,French,Scholarship for international students at Moroccan public universities.,https://www.amci.ma,https://www.amci.ma,Official,Joshua,2026-06-23
SCH-004,Fulbright Foreign Student Program,U.S. Department of State,US,Masters,Most fields,Strong academic record,Fully Funded,Tuition + living stipend + airfare + health benefits,2026-08-06,Graduate students and young professionals,English,Prestigious U.S. scholarship for international graduate study.,https://foreign.fulbrightonline.org,https://foreign.fulbrightonline.org,Official,Joshua,2026-06-23
SCH-005,Commonwealth Shared Scholarship,Commonwealth Scholarship Commission,UK,Masters,Development-related Master's fields,Upper second-class degree,Fully Funded,Tuition + airfare + living stipend,2025-12-10,Citizens of eligible Commonwealth countries,English,UK government and university funded Master's scholarships.,https://cscuk.fcdo.gov.uk,https://cscuk.fcdo.gov.uk,Official,Joshua,2026-06-23
SCH-006,Mastercard Foundation Scholars Program at University of Cambridge,University of Cambridge / Mastercard Foundation,UK,Masters,Climate science and related Master's programs,Strong academic merit,Fully Funded,Full tuition + stipend + travel,2026-01-07,African students with leadership potential,English,Supports talented African students pursuing graduate study at Cambridge.,https://www.mastercardfdn.org,https://www.mastercardfdn.org,Official,Joshua,2026-06-23
FS_FILE_EOF

cat > 'frontend/.streamlit/config.toml' << 'FS_FILE_EOF'
[theme]
primaryColor = "#F4A300"
backgroundColor = "#F3F5F8"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#0F2A43"
font = "sans serif"

[server]
headless = true
FS_FILE_EOF

echo ""
echo "Done. Files:"
find frontend -type f | sort
echo ""
echo "Next: cd frontend && pip install -r requirements.txt && streamlit run app.py"
