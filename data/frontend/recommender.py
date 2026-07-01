"""
recommender.py — adapter between the Streamlit UI and the FirstStep backend API.

The UI calls get_recommendations(profile, top_k) and gets back results in the
DATA_CONTRACT shape: { scholarship, match_score, explanation }. This version
no longer runs the model locally — it calls the Flask backend over HTTP so
the frontend always sees the same data and matching logic as everyone else
on the team.

Flow:
  UI profile  ->  POST /recommend (ranking + scores)
              ->  GET /scholarships (full records, cached)
              ->  join by id -> destination post-filter -> contract shape
"""

from __future__ import annotations

import functools
import os
from typing import Any

import requests

# Point this at wherever the Flask backend is running.
# Locally: http://localhost:5000   |  Deployed: set API_BASE_URL env var.
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000").rstrip("/")

# Backend's hard cap on /recommend's top_k (see app.py validation).
_MAX_API_TOP_K = 20

REQUEST_TIMEOUT = 10  # seconds


class BackendUnavailable(Exception):
    """Raised when the FirstStep API can't be reached or returns an error."""


_STOP = {
    "and", "the", "for", "but", "with", "from", "are", "has", "was", "not",
    "can", "all", "any", "its", "our", "you", "your", "that", "this", "have",
    "been", "will", "more", "also", "such", "their", "study",
}


def _split(text: str) -> list[str]:
    """Split a comma/semicolon string into a clean list."""
    return [t.strip() for t in str(text or "").replace(";", ",").split(",") if t.strip()]


@functools.lru_cache(maxsize=1)
def _all_scholarships() -> dict[str, dict[str, Any]]:
    """
    Fetch the full scholarship dataset once and cache it for the session.
    Used to join full records (description, eligibility, etc.) onto the
    ranked/scored results that /recommend returns.

    NOTE: cached for the life of the process — if the backend dataset gets
    updated, restart the Streamlit app (or wire this to st.cache_data with a
    TTL instead of lru_cache if that's a problem in practice).
    """
    try:
        resp = requests.get(f"{API_BASE_URL}/scholarships", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise BackendUnavailable(f"Could not reach FirstStep API at {API_BASE_URL}: {e}") from e

    payload = resp.json()
    if not payload.get("success"):
        raise BackendUnavailable(f"API returned an error: {payload}")

    return {row["id"]: row for row in payload["scholarships"]}


def available_countries() -> list[str]:
    """Distinct destination countries present in the dataset (for the picker)."""
    rows = _all_scholarships().values()
    return sorted({str(r.get("country", "")).strip() for r in rows if str(r.get("country", "")).strip()})


def _explanation(full: dict[str, Any], query_terms: set[str]) -> str:
    """
    Plain-language 'why this fits' line. Placeholder until this is swapped
    for Kofi's Gemini explainer layer — the UI just displays this string,
    so swapping it later changes nothing here.
    """
    bits: list[str] = []
    blob = f"{full.get('field_of_study', '')} {full.get('description', '')}".lower()
    shared = sorted({t for t in query_terms if len(t) > 2 and t not in _STOP and t in blob})
    if shared:
        bits.append(f"it lines up with your interest in {', '.join(shared[:3])}")
    if "fully funded" in str(full.get("funding_type", "")).lower():
        bits.append("it's fully funded")
    country = str(full.get("country", "")).strip()
    if country and country.lower() not in ("various", "online"):
        bits.append(f"it's based in {country}")
    if not bits:
        return f"A general fit for your profile — check the eligibility for {full.get('name', 'this scholarship')}."
    s = "; ".join(bits)
    return s[0].upper() + s[1:] + "."


def get_recommendations(profile: dict[str, Any], top_k: int = 8) -> list[dict[str, Any]]:
    """
    Rank scholarships for a student profile by calling the FirstStep backend.

    profile keys:
        gpa        float (4.0 scale)
        courses    str   (comma-separated)
        interests  str   (comma-separated)
        locations  list[str]  preferred destination countries (empty = all)
        level      str   ("Any" / "Bachelors" / "Masters" / "PhD")
        language   str   ("English" / "French" / ...)

    Returns list of { scholarship: {...18 fields}, match_score: float, explanation: str }
    sorted by match strength.

    Raises BackendUnavailable if the API can't be reached — callers should
    catch this and show a friendly "backend offline" message in the UI
    rather than crashing.
    """
    courses = _split(profile.get("courses"))
    interests = _split(profile.get("interests"))
    prefs = {c.strip().lower() for c in profile.get("locations", []) if str(c).strip()}

    # Ask for the max the API allows — we post-filter by destination locally,
    # so requesting fewer than the cap risks under-filling top_k once the
    # destination filter is applied.
    request_k = _MAX_API_TOP_K if prefs else min(top_k, _MAX_API_TOP_K)

    body = {
        "gpa": float(profile.get("gpa") or 0.0),
        "courses": courses or ["General"],
        "interests": interests or ["General"],
        "level": profile.get("level") or "Any",
        "language": profile.get("language") or "English",
        "location": "Gambia",  # home country — drives the Africa-eligibility boost
        "top_k": request_k,
    }

    try:
        resp = requests.post(f"{API_BASE_URL}/recommend", json=body, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise BackendUnavailable(f"Could not reach FirstStep API at {API_BASE_URL}: {e}") from e

    payload = resp.json()
    if not payload.get("success"):
        raise BackendUnavailable(f"API returned an error: {payload}")

    ranked = payload.get("recommendations", [])
    if not ranked:
        return []

    by_id = _all_scholarships()
    query_terms = set(" ".join(courses + interests).lower().split())

    results: list[dict[str, Any]] = []
    for r in ranked:
        full = by_id.get(r["id"])
        if full is None:
            continue  # shouldn't happen, but don't let a stale cache crash the UI
        country = str(full.get("country", ""))
        if prefs and country.lower() not in prefs and country.lower() not in ("various", "online"):
            continue
        # /recommend now returns a real Gemini-generated explanation per item
        # (from explainer.py). Use it when present; fall back to the local
        # placeholder only if the backend couldn't produce one (e.g. missing
        # API key, explainer.py not loaded, or a per-item Gemini failure).
        api_explanation = str(r.get("explanation") or "").strip()
        fallback_needed = (
            not api_explanation
            or api_explanation.lower().startswith(("explanation unavailable", "could not generate"))
        )
        explanation = _explanation(full, query_terms) if fallback_needed else api_explanation

        results.append({
            "scholarship": full,
            "match_score": float(r["final_score"]),
            "explanation": explanation,
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
