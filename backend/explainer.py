"""
explainer.py
------------
FirstStep Project — Phase 5: LLM Explanation Layer
Role: Emmanuel (Kofi)

Takes the top scholarship matches from the TF-IDF model and generates
a human-friendly explanation for WHY each scholarship matches the student.

Uses the Google Gemini API (gemini-2.0-flash — fast and free-tier friendly).

Setup:
    pip install google-genai python-dotenv

    Create a .env file in the project root:
        GEMINI_API_KEY=your-key-here

Usage (standalone test):
    python explainer.py

Integrated usage (called from app.py):
    from explainer import explain_matches
    explanations = explain_matches(profile, recommendations)
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-flash-latest"

# ─── Client ───────────────────────────────────────────────────────────────────

def get_client():
    """Return a Gemini client. Raises if API key is missing."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file or set it as an environment variable."
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

    return response.text.strip()


# ─── Batch explanation for all matches ────────────────────────────────────────

def explain_matches(profile: dict, recommendations: list[dict]) -> list[dict]:
    """
    Add an 'explanation' field to each scholarship recommendation.
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

    results = []
    for scholarship in recommendations:
        try:
            explanation = explain_one(client, profile, scholarship)
        except Exception as e:
            print(f"[explainer] Failed to explain {scholarship.get('id')}: {e}")
            explanation = "Could not generate explanation at this time."

        scholarship["explanation"] = explanation
        results.append(scholarship)

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
    print("=" * 60)

    explained = explain_matches(test_profile, test_recommendations)

    for rec in explained:
        print(f"\n[{rec['id']}] {rec['name']}")
        print(f"Score: {rec['final_score']}")
        print(f"\nExplanation:\n{rec['explanation']}")
        print("-" * 60)
