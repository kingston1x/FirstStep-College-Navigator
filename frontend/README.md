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
