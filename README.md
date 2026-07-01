# FirstStep — College & Scholarship Navigator 🎓

**AI-powered scholarship and college matching for Gambian students.**

FirstStep helps students discover scholarships and higher-education opportunities that actually fit their profile — GPA, coursework, interests, and preferred study destinations — instead of scrolling through generic scholarship lists.

---

## What it does

1. A student enters their profile: GPA, courses, interests, and preferred destination countries.
2. The matching engine scores every scholarship in the dataset against that profile using TF-IDF text similarity over fields like field of study, description, and eligibility.
3. Each result comes back ranked with a **match score** (0–100%) and a short, human-readable **explanation** of *why* it's a good fit (e.g. *"It's in the United Kingdom, one of your preferred destinations; it lines up with your interest in leadership."*).

The project is split so the frontend, the matching model, and the data pipeline can be built and improved independently — see [`DATA_CONTRACT.md`](./DATA_CONTRACT.md) for the exact interface everything agrees on.

---

## Project structure

| File / Folder | Purpose |
|---|---|
| `app.py` | Main application entry point (Streamlit UI) |
| `matcher.py` | Core matching/ranking engine — scores scholarships against a student profile |
| `explainer.py` | Generates the natural-language "why this fits you" explanation for each match |
| `cleaner.py` | Cleans and normalizes the raw scholarship dataset |
| `evaluate.py` / `evaluation/` | Scripts and results for evaluating match quality |
| `data/` | Scholarship dataset(s) |
| `DATA_CONTRACT.md` | The request/response contract between the frontend and the matching backend |
| `requirements.txt` | Python dependencies |
| `test.bat` | Windows helper script for running tests |

---

## Getting started

**Requirements:** Python 3.9+

```bash
# 1. Clone the repo
git clone https://github.com/kingston1x/FirstStep-College-Navigator.git
cd FirstStep-College-Navigator

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

> If `app.py` isn't a Streamlit entry point in your local copy, check the top of the file for the exact run command — adjust accordingly.

---

## How matching works

A request looks like this:

```json
{
  "profile": {
    "gpa": 3.6,
    "courses": "computer science, networking, cloud computing",
    "interests": "AI, software engineering, leadership",
    "locations": ["United Kingdom", "Türkiye"]
  },
  "top_k": 8
}
```

And a response returns ranked scholarships, each with a `match_score` and an `explanation` string:

```json
{
  "results": [
    {
      "scholarship": {
        "name": "Chevening Scholarship",
        "provider": "UK Government (FCDO)",
        "country": "United Kingdom",
        "level": "Master's",
        "funding_type": "Fully funded",
        "deadline": "Early November (annual)"
      },
      "match_score": 0.594,
      "explanation": "It's in the United Kingdom, one of your preferred destinations; it lines up with your interest in leadership."
    }
  ]
}
```

Full field definitions and the 18-column scholarship schema are documented in [`DATA_CONTRACT.md`](./DATA_CONTRACT.md).

---

## Roadmap ideas

- [ ] Expand the scholarship dataset beyond the initial curated set
- [ ] Add filtering by funding type, degree level, and deadline
- [ ] Deploy a hosted version for students to use directly

---

## Contributing

Issues and pull requests are welcome. If you're adding scholarships to the dataset, please follow the column schema in `DATA_CONTRACT.md` so the matcher and UI keep working without changes.

---

## License

No license file is currently included in this repository — add one (e.g. MIT) if you intend for others to reuse this code.
