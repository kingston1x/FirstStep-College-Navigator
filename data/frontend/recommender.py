"""
recommender.py — the matching layer the front-end calls.

RIGHT NOW this is a self-contained MOCK so the UI runs and demos without
waiting on the backend. It loads the local scholarships.json, scores each
scholarship against the student's profile with a lightweight keyword + rule
scorer, and returns ranked results in the agreed contract shape.

LATER (when Kofi's backend + Cday's TF-IDF model are live) you do NOT rewrite
the UI. You only replace the body of `get_recommendations()` with a call to
the backend. The function signature and the returned shape stay identical.
See DATA_CONTRACT.md and the `_call_backend` example at the bottom of this file.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "scholarships.json")

# A tiny stopword list so common words don't inflate keyword overlap.
_STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "to", "in", "for", "with", "on",
    "any", "all", "study", "studies", "student", "students", "field", "fields",
    "i", "am", "my", "want", "interested", "like", "love", "would", "be",
}


def load_scholarships(path: str = DATA_PATH) -> list[dict[str, Any]]:
    """Read the local scholarship dataset."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _tokens(text: str) -> set[str]:
    """Lowercase word tokens with stopwords removed."""
    words = re.findall(r"[a-z]+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _parse_min_gpa(min_gpa_text: str) -> float | None:
    """
    The dataset stores min_gpa as free text (e.g. "70%", "Upper second-class
    (2:1)"). Pull out a rough numeric floor on a 5.0 scale so we can flag
    feasibility. Returns None when nothing numeric is present.
    """
    if not min_gpa_text:
        return None
    text = min_gpa_text.lower()

    # Percentage like "70%" -> map onto a 5.0 scale.
    pct = re.search(r"(\d{2})\s*%", text)
    if pct:
        return round(float(pct.group(1)) / 20.0, 2)  # 100% -> 5.0

    # Common UK honours bands -> rough 5.0-scale equivalents.
    if "first" in text:
        return 4.5
    if "2:1" in text or "upper second" in text:
        return 3.7
    if "2:2" in text or "lower second" in text:
        return 3.0
    return None


def _explain(profile: dict[str, Any], sch: dict[str, Any], shared: set[str],
             country_match: bool, gpa_ok: bool | None) -> str:
    """
    Build a plain-language reason this scholarship was matched.

    This is a PLACEHOLDER for the LLM explanation Kofi's layer will generate.
    Keep it human and specific so the demo reads well even before the LLM lands.
    """
    bits: list[str] = []
    if country_match:
        bits.append(f"it's in {sch['country']}, one of your preferred destinations")
    if shared:
        topics = ", ".join(sorted(shared)[:3])
        bits.append(f"it lines up with your interest in {topics}")
    if gpa_ok is True:
        bits.append("your GPA clears its stated requirement")
    elif gpa_ok is False:
        bits.append("its grade bar looks above your current GPA, so treat it as a reach")

    if not bits:
        return (f"A general match on level and field. Check the eligibility "
                f"rules for {sch['name']} to confirm you qualify.")
    reason = "; ".join(bits)
    return reason[0].upper() + reason[1:] + "."


def get_recommendations(profile: dict[str, Any], top_k: int = 8) -> list[dict[str, Any]]:
    """
    Rank scholarships for a student profile.

    Parameters
    ----------
    profile : dict with keys
        gpa        : float   (e.g. 3.4 on a 5.0 scale)
        courses    : str     (free text, e.g. "computer science, networking")
        interests  : str     (free text, e.g. "AI, software, scholarships abroad")
        locations  : list[str] preferred destination countries (may be empty)
    top_k : how many ranked results to return.

    Returns
    -------
    list of result objects in the DATA_CONTRACT shape:
        { "scholarship": {...}, "match_score": float 0..1, "explanation": str }
    sorted by match_score descending.
    """
    scholarships = load_scholarships()

    profile_tokens = _tokens(
        f"{profile.get('courses', '')} {profile.get('interests', '')}"
    )
    prefs = {c.strip().lower() for c in profile.get("locations", []) if c.strip()}
    student_gpa = profile.get("gpa")

    results: list[dict[str, Any]] = []
    for sch in scholarships:
        corpus = _tokens(
            f"{sch.get('field_of_study', '')} {sch.get('description', '')} "
            f"{sch.get('eligibility', '')}"
        )
        shared = profile_tokens & corpus

        # --- score components (all 0..1) ---
        # 1) keyword overlap with the student's courses + interests
        overlap = len(shared) / max(len(profile_tokens), 1)
        keyword_score = min(overlap * 1.5, 1.0)  # gentle boost, capped

        # 2) destination preference
        country_match = sch.get("country", "").strip().lower() in prefs if prefs else False
        country_score = 1.0 if country_match else (0.0 if prefs else 0.4)

        # 3) GPA feasibility
        floor = _parse_min_gpa(sch.get("min_gpa", ""))
        if floor is None or student_gpa is None:
            gpa_ok: bool | None = None
            gpa_score = 0.6  # unknown -> neutral
        elif student_gpa >= floor:
            gpa_ok = True
            gpa_score = 1.0
        else:
            gpa_ok = False
            gpa_score = 0.25  # still show it, flagged as a reach

        # weighted blend; weights chosen so field relevance leads, then fit
        match_score = round(
            0.50 * keyword_score + 0.25 * country_score + 0.25 * gpa_score, 3
        )

        results.append({
            "scholarship": sch,
            "match_score": match_score,
            "explanation": _explain(profile, sch, shared, country_match, gpa_ok),
        })

    results.sort(key=lambda r: r["match_score"], reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# WHEN THE BACKEND IS READY — swap the body of get_recommendations() for this.
# Nothing in app.py changes, because the returned shape is identical.
#
# import requests
# BACKEND_URL = os.environ.get("FIRSTSTEP_API", "http://localhost:8000")
#
# def _call_backend(profile, top_k=8):
#     resp = requests.post(f"{BACKEND_URL}/recommend",
#                          json={"profile": profile, "top_k": top_k}, timeout=15)
#     resp.raise_for_status()
#     return resp.json()["results"]   # must match DATA_CONTRACT.md
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    # Quick self-test so you can run `python recommender.py` and eyeball output.
    demo = {
        "gpa": 3.6,
        "courses": "computer science, networking, cloud computing",
        "interests": "AI, software engineering, leadership",
        "locations": ["United Kingdom", "Türkiye"],
    }
    for r in get_recommendations(demo, top_k=5):
        s = r["scholarship"]
        print(f"{r['match_score']:>5}  {s['name']} ({s['country']})")
        print(f"        {r['explanation']}")
