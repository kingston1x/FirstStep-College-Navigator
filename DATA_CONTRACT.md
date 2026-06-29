# FirstStep — Data Contract (Front-end ⇄ Back-end)

This is the agreement between Joshua's Streamlit front-end and Kofi's backend /
Cday's ranking model. As long as both sides honour the shapes below, either
side can be developed and swapped independently. **Do not change these field
names without telling the whole team** — the UI reads them directly.

---

## 1. Request — what the front-end sends

The front-end calls `recommender.get_recommendations(profile, top_k)`.
When wired to the live backend, this becomes:

```
POST {BACKEND_URL}/recommend
Content-Type: application/json
```

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

| Field        | Type        | Notes                                                        |
|--------------|-------------|-------------------------------------------------------------|
| `gpa`        | number      | 0.0–5.0 scale.                                              |
| `courses`    | string      | Free text. Part of the TF-IDF query corpus.                |
| `interests`  | string      | Free text. Part of the TF-IDF query corpus.                |
| `locations`  | string[]    | Preferred destination countries. May be empty (= no filter).|
| `top_k`      | integer     | Max number of ranked results to return.                    |

---

## 2. Response — what the back-end returns

A JSON object with a `results` array, each item in this shape:

```json
{
  "results": [
    {
      "scholarship": {
        "id": "UK-001",
        "name": "Chevening Scholarship",
        "provider": "UK Government (FCDO)",
        "country": "United Kingdom",
        "level": "Master's",
        "field_of_study": "Any field; leadership, public policy...",
        "min_gpa": "Upper second-class (2:1) honours equivalent",
        "funding_type": "Fully funded",
        "value": "Full tuition, monthly stipend, travel...",
        "deadline": "Early November (annual)",
        "eligibility": "Citizen of a Chevening-eligible country...",
        "language_req": "IELTS / English proficiency",
        "description": "The UK government's flagship global scholarship...",
        "apply_url": "https://www.chevening.org/apply/",
        "source_url": "https://www.chevening.org/",
        "source_type": "official",
        "collected_by": "Joshua",
        "date_added": "2026-06-23"
      },
      "match_score": 0.594,
      "explanation": "It's in the United Kingdom, one of your preferred destinations; it lines up with your interest in leadership."
    }
  ]
}
```

### Result object

| Field           | Type   | Used by the UI for                              |
|-----------------|--------|-------------------------------------------------|
| `scholarship`   | object | The card body (see the 18 fields below).        |
| `match_score`   | number | The match-strength meter (0.0–1.0 → percentage).|
| `explanation`   | string | The "Why this fits you" line. **This is where Kofi's LLM layer plugs in** — the front-end just displays the string. |

### Scholarship object — the 18 columns

These are exactly the columns in `FirstStep_Scholarship_Data_Template.xlsx` and
`frontend/data/scholarships.json`, so the scraper, the dataset, and the UI all
speak the same language:

`id`, `name`, `provider`, `country`, `level`, `field_of_study`, `min_gpa`,
`funding_type`, `value`, `deadline`, `eligibility`, `language_req`,
`description`, `apply_url`, `source_url`, `source_type`, `collected_by`,
`date_added`.

The UI currently displays: `name`, `provider`, `country`, `level`,
`funding_type`, `deadline`, `min_gpa`, `apply_url`. The free-text fields
(`field_of_study`, `description`, `eligibility`) are the TF-IDF corpus on the
model side.

---

## 3. The swap

When the backend is ready, the only change on the front-end is the body of
`get_recommendations()` in `frontend/recommender.py` — replace the local mock
scorer with the `POST /recommend` call (the commented `_call_backend` example
is already in that file). `app.py` does not change at all.
