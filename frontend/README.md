# FirstStep — Front-end

The Streamlit interface for FirstStep, the scholarship & college navigator for
Gambian students. A student enters their profile (GPA, courses, interests,
preferred destinations) and gets ranked scholarship matches, each with a
plain-language reason it fits.

Owner: Joshua · Part of the FirstStep group project.

## Run it

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## What's here

| File | Purpose |
|------|---------|
| `app.py` | The Streamlit UI — profile form + ranked result cards. |
| `recommender.py` | The matching layer the UI calls. A working **mock** today; becomes Kofi's backend call later (signature unchanged). |
| `data/scholarships.json` | 14 real scholarships across the UK, Türkiye, China, Morocco and the US — the demo dataset (also Joshua's Phase 1/2 data). |
| `.streamlit/config.toml` | Theme so Streamlit's own widgets match the navy/gold identity. |

## How it connects to the rest of the team

The UI never talks to the model directly — it calls
`recommender.get_recommendations(profile, top_k)`, which returns results in the
shape defined in [`../DATA_CONTRACT.md`](../DATA_CONTRACT.md).

- **Today:** that function scores the local dataset itself, so the app runs
  standalone with no backend.
- **Later:** swap the body of `get_recommendations()` for a `POST /recommend`
  call to Kofi's backend (the example is already commented in the file). The
  match scores come from Cday's TF-IDF + cosine model, and the `explanation`
  string comes from Kofi's LLM layer. `app.py` doesn't change.

## Notes

Scholarship details (especially deadlines) are indicative and flagged for
verification — confirming them is Phase 2 (manual data collection). Always
check the official site before applying.
