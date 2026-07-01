"""
explainer.py
------------
FirstStep Project — Phase 5: LLM Explanation Layer
Role: Emmanuel (Kofi)

Takes the top scholarship matches from the TF-IDF model and generates a
human-friendly explanation for WHY each scholarship matches the student.

Uses the Google Gemini API via the unified `google-genai` SDK.

Location:
    This file lives in  backend/explainer.py

Setup:
    pip install google-genai python-dotenv

    Create a .env file in the PROJECT ROOT (FirstStep-College-Navigator/):
        GEMINI_API_KEY=your-key-here
        # optional — override the model if you like:
        # GEMINI_MODEL=gemini-2.5-flash

Integrated usage (called from the Streamlit frontend):
    # frontend/app.py — add project root to path first, then:
    #
    #   import sys
    #   from pathlib import Path
    #   sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    #
    #   from backend.explainer import explain_matches
    #   recommendations = explain_matches(profile, recommendations)
    #
    # (requires an empty  backend/__init__.py  so `backend` is a package)

Standalone test:
    python explainer.py
"""

import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from google import genai


# ─── Environment ──────────────────────────────────────────────────────────────
# Load the .env from the PROJECT ROOT explicitly, so the key is found no matter
# what directory Streamlit or the shell is launched from. Streamlit's working
# directory is not guaranteed to be the project root, which is a common cause of
# "API key not configured" even when a .env exists.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent   # backend/ -> root
_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()   # fall back to the default upward search from CWD


# ─── Model ────────────────────────────────────────────────────────────────────
# Default to a STABLE flash model, not the "-latest" alias.
#   • "gemini-flash-latest" is valid, but it hot-swaps to the newest release
#     (currently Gemini 3.5 Flash) and has been hitting stricter free-tier rate
#     limits — requests can fail with "resource exhausted" on the first call.
#   • "gemini-2.5-flash" is fast, cheap, and free-tier friendly.
# Override any time by setting GEMINI_MODEL in your .env.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


# ─── Client ───────────────────────────────────────────────────────────────────

def get_client():
    """Return a Gemini client. Raises EnvironmentError if the API key is missing."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file (project root) or set it as an "
            "environment variable."
        )
    return genai.Client(api_key=api_key)


# ─── Single scholarship explanation ───────────────────────────────────────────

def explain_one(client, profile: dict, scholarship: dict) -> str:
    """
    Generate a 2-3 sentence explanation of why a scholarship matches a student.
    """

    prompt = f"""You are a scholarship advisor helping a student from {profile.get('location', 'The Gambia')} understand why a scholarship is a good fit for them.

Student Profile:
- GPA: {profile.get('gpa')} / 4.0
- Study Level: {profile.get('level')}
- Courses: {', '.join(profile.get('courses', []))}
- Interests: {', '.join(profile.get('interests', []))}
- Language: {profile.get('language', 'English')}

Scholarship:
- Name: {scholarship.get('name')}
- Provider: {scholarship.get('provider')}
- Country: {scholarship.get('country')}
- Level: {scholarship.get('level')}
- Funding: {scholarship.get('funding_type')}
- Deadline: {scholarship.get('deadline')}
- Match Score: {scholarship.get('final_score')}

Write a 2-3 sentence personalised explanation of why this scholarship is a good match for this student. Be specific — mention their courses or interests directly. Be encouraging but honest. Do not use bullet points. Plain paragraph only."""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    # response.text can be None if the model returns no text (e.g. a safety
    # block or an empty candidate). Guard it so we never call .strip() on None.
    text = getattr(response, "text", None)
    if not text:
        return "Could not generate an explanation for this scholarship."
    return text.strip()


# ─── Batch explanation for all matches ────────────────────────────────────────

def explain_matches(profile: dict, recommendations: list[dict]) -> list[dict]:
    """
    Add an 'explanation' field to each scholarship recommendation.

    Calls Gemini once per scholarship, IN PARALLEL via a thread pool — these
    are independent network I/O calls, so running them concurrently turns a
    top_k=8 request from ~8x single-call latency into roughly 1x (plus a little
    overhead), instead of blocking the whole response on each call in sequence.
    """
    if not recommendations:
        return recommendations

    try:
        client = get_client()
    except EnvironmentError as e:
        print(f"[explainer] Warning: {e}")
        for rec in recommendations:
            rec["explanation"] = "Explanation unavailable — API key not configured."
        return recommendations

    def _explain_with_fallback(scholarship: dict) -> tuple[dict, str]:
        try:
            explanation = explain_one(client, profile, scholarship)
        except Exception as e:
            print(f"[explainer] Failed to explain {scholarship.get('id')}: {e}")
            explanation = "Could not generate explanation at this time."
        return scholarship, explanation

    # Cap workers at a sane ceiling regardless of top_k, to avoid hammering the
    # Gemini API with too many simultaneous requests (rate limits).
    max_workers = min(len(recommendations), 8)
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_explain_with_fallback, s) for s in recommendations]
        for future in as_completed(futures):
            scholarship, explanation = future.result()
            scholarship["explanation"] = explanation
            results.append(scholarship)

    # as_completed() finishes in whatever order calls return, not the order they
    # were submitted — restore the original ranking before returning.
    order = {s.get("id"): i for i, s in enumerate(recommendations)}
    results.sort(key=lambda s: order.get(s.get("id"), 0))

    return results


# ─── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_profile = {
        "gpa": 3.2,
        "courses": ["Computer Science", "Mathematics"],
        "interests": ["AI", "machine learning"],
        "level": "Masters",
        "language": "English",
        "location": "Gambia",
    }

    test_recommendations = [
        {
            "id": "SCH-004",
            "name": "Fulbright Foreign Student Program",
            "provider": "U.S. Department of State",
            "country": "USA",
            "level": "Masters",
            "funding_type": "Fully funded",
            "deadline": "2026-08-06",
            "apply_url": "https://foreign.fulbrightonline.org",
            "tfidf_score": 0.312,
            "boost_score": 0.100,
            "final_score": 0.412,
        },
        {
            "id": "SCH-006",
            "name": "Mastercard Foundation Scholars Program (Cambridge)",
            "provider": "University of Cambridge / Mastercard Foundation",
            "country": "UK",
            "level": "Masters",
            "funding_type": "Fully funded",
            "deadline": "2026-01-07",
            "apply_url": "https://www.mastercardfdn.org",
            "tfidf_score": 0.289,
            "boost_score": 0.150,
            "final_score": 0.439,
        },
    ]

    print("=" * 60)
    print("  FirstStep — LLM Explanation Layer Test (Gemini)")
    print(f"  Model: {MODEL_NAME}")
    print("=" * 60)

    explained = explain_matches(test_profile, test_recommendations)

    for rec in explained:
        print(f"\n[{rec['id']}] {rec['name']}")
        print(f"Score: {rec['final_score']}")
        print(f"\nExplanation:\n{rec['explanation']}")
        print("-" * 60)
