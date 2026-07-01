"""
app.py
------
FirstStep Project — Phase 4: Backend Development
Role: Emmanuel (Kofi)

Flask API that wraps the TF-IDF scholarship matcher (matcher.py).
Loads the model once at startup, then serves recommendations via REST endpoints.

Endpoints:
    GET  /                        Health check
    GET  /scholarships            List all scholarships
    POST /recommend               Match scholarships to a student profile
    GET  /scholarship/<id>        Get a single scholarship by ID

Usage:
    pip install flask flask-cors
    python app.py

    # or in production:
    pip install gunicorn
    gunicorn app:app
"""

import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Import the matcher ────────────────────────────────────────────────────────
# matcher.py must be in the same folder as app.py
try:
    from matcher import load_scholarships, build_vectorizer, make_profile, match
except ImportError:
    print("[ERROR] matcher.py not found. Make sure it's in the same folder as app.py.")
    sys.exit(1)

# ─── App setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)   # allow Streamlit frontend to call this API cross-origin

# ─── Load model at startup (once) ─────────────────────────────────────────────
# Adjust this path to wherever your clean CSV lives in the project

CSV_PATH = os.environ.get(
    "SCHOLARSHIPS_CSV",
    os.path.join(os.path.dirname(__file__), "data", "clean", "Scholarships_clean.csv")
)

print(f"[startup] Loading scholarships from: {CSV_PATH}")

try:
    SCHOLARSHIPS_DF = load_scholarships(CSV_PATH)
    VECTORIZER, MATRIX = build_vectorizer(SCHOLARSHIPS_DF)
    print(f"[startup] Loaded {len(SCHOLARSHIPS_DF)} scholarships. Model ready.\n")
except FileNotFoundError as e:
    print(f"[ERROR] {e}")
    print("Set the SCHOLARSHIPS_CSV environment variable to point to your CSV file.")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Failed to load model: {e}")
    sys.exit(1)

# ─── Helper ───────────────────────────────────────────────────────────────────

def df_to_records(df):
    """Convert DataFrame to a clean list of dicts, dropping internal _ columns."""
    cols = [c for c in df.columns if not c.startswith("_")]
    return df[cols].to_dict(orient="records")


def error(message, status=400):
    return jsonify({"success": False, "error": message}), status


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    """Health check — confirms the API is running and model is loaded."""
    return jsonify({
        "success": True,
        "message": "FirstStep Scholarship API is running.",
        "scholarships_loaded": len(SCHOLARSHIPS_DF),
    })


@app.route("/scholarships", methods=["GET"])
def list_scholarships():
    """
    Return all scholarships in the dataset.

    Optional query params:
        country   — filter by country (case-insensitive)
        level     — filter by study level (e.g. Masters, PhD)
        funded    — "true" to return only fully funded scholarships
        limit     — max number of results (default: all)
    """
    df = SCHOLARSHIPS_DF.copy()

    country = request.args.get("country", "").strip().lower()
    if country:
        df = df[df["country"].str.lower().str.contains(country, na=False)]

    level = request.args.get("level", "").strip().lower()
    if level:
        df = df[df["level"].str.lower().str.contains(level, na=False)]

    funded = request.args.get("funded", "").strip().lower()
    if funded == "true":
        df = df[df["funding_type"].str.lower().str.contains("fully funded", na=False)]

    limit = request.args.get("limit", None)
    if limit:
        try:
            df = df.head(int(limit))
        except ValueError:
            return error("'limit' must be an integer.")

    return jsonify({
        "success": True,
        "count": len(df),
        "scholarships": df_to_records(df),
    })


@app.route("/scholarship/<scholarship_id>", methods=["GET"])
def get_scholarship(scholarship_id):
    """Return a single scholarship by its ID (e.g. SCH-002)."""
    row = SCHOLARSHIPS_DF[SCHOLARSHIPS_DF["id"] == scholarship_id]

    if row.empty:
        return error(f"Scholarship '{scholarship_id}' not found.", status=404)

    return jsonify({
        "success": True,
        "scholarship": df_to_records(row)[0],
    })


@app.route("/recommend", methods=["POST"])
def recommend():
    """
    Match scholarships to a student profile using TF-IDF cosine similarity.

    Expected JSON body:
    {
        "gpa": 3.2,
        "courses": ["Computer Science", "Mathematics"],
        "interests": ["AI", "machine learning"],
        "level": "Masters",
        "language": "English",
        "location": "Gambia",
        "top_k": 5
    }

    Returns top_k matched scholarships ranked by final_score.
    """
    data = request.get_json()

    if not data:
        return error("Request body must be JSON.")

    # ── Validate required fields ───────────────────────────────────────────────
    required = ["gpa", "courses", "interests"]
    missing = [f for f in required if f not in data]
    if missing:
        return error(f"Missing required fields: {missing}")

    # ── Validate types ─────────────────────────────────────────────────────────
    try:
        gpa = float(data["gpa"])
    except (ValueError, TypeError):
        return error("'gpa' must be a number (e.g. 3.2).")

    if not (0.0 <= gpa <= 4.0):
        return error("'gpa' must be between 0.0 and 4.0.")

    courses = data["courses"]
    interests = data["interests"]

    if not isinstance(courses, list) or not courses:
        return error("'courses' must be a non-empty list of strings.")
    if not isinstance(interests, list) or not interests:
        return error("'interests' must be a non-empty list of strings.")

    level    = data.get("level", "Any")
    language = data.get("language", "English")
    location = data.get("location", "Gambia")
    top_k    = data.get("top_k", 5)

    try:
        top_k = int(top_k)
        if top_k < 1 or top_k > 20:
            raise ValueError
    except (ValueError, TypeError):
        return error("'top_k' must be an integer between 1 and 20.")

    # ── Build profile and run matcher ──────────────────────────────────────────
    try:
        profile = make_profile(
            gpa=gpa,
            courses=courses,
            interests=interests,
            location=location,
            level=level,
            language=language,
        )

        results = match(
            profile=profile,
            df=SCHOLARSHIPS_DF,
            vectorizer=VECTORIZER,
            matrix=MATRIX,
            top_k=top_k,
        )
    except Exception as e:
        return error(f"Matching failed: {str(e)}", status=500)

    if results.empty:
        return jsonify({
            "success": True,
            "count": 0,
            "message": "No scholarships matched your profile. Try broadening your criteria.",
            "recommendations": [],
        })

    # Round scores for clean output
    results["tfidf_score"] = results["tfidf_score"].round(4)
    results["boost_score"] = results["boost_score"].round(4)
    results["final_score"] = results["final_score"].round(4)

    return jsonify({
        "success": True,
        "count": len(results),
        "profile": {
            "gpa": gpa,
            "level": level,
            "language": language,
            "location": location,
            "courses": courses,
            "interests": interests,
        },
        "recommendations": results.to_dict(orient="records"),
    })


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    print(f"[app] Starting FirstStep API on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
