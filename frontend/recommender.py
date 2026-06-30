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
