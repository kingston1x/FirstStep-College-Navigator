"""
FirstStep — Scholarship Navigator (front-end)

A student fills in their profile (GPA, courses, interests, preferred
destinations) and gets ranked scholarship matches, each with a plain-language
reason it fits. The ranking comes from recommender.get_recommendations(),
which is a local mock today and becomes Kofi's backend call later — this file
does not change when that swap happens.

Run:  streamlit run app.py
"""

import html

import streamlit as st

from recommender import get_recommendations, available_countries

# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="FirstStep Scholarship Navigator",
    page_icon="FS",
    layout="wide",
)

# Destinations are pulled from the actual dataset, so the picker always
# reflects the scholarships we really have.
DESTINATIONS = available_countries()

# --------------------------------------------------------------------------
# Styling — deep navy + gold "departure board" identity
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

    :root {
        --ink:    #0F2A43;
        --gold:   #F4A300;
        --go:     #1E8E6F;
        --muted:  #5B6B7B;
        --line:   #E2E8F0;
        --surface:#FFFFFF;
        --bg:     #F3F5F8;
    }

    .stApp { background: var(--bg); }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--ink); }

    /* Hero band */
    .fs-hero {
        background: linear-gradient(135deg, #0F2A43 0%, #18456B 100%);
        border-radius: 16px;
        padding: 30px 34px;
        margin-bottom: 26px;
        color: #fff;
    }
    .fs-hero h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 2.05rem;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
        color: #fff;
    }
    .fs-hero .accent { color: var(--gold); }
    .fs-hero p { margin: 0; color: #C9D6E3; font-size: 1.02rem; max-width: 640px; }

    /* Section labels */
    .fs-eyebrow {
        font-family: 'Space Grotesk', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-size: 0.72rem;
        font-weight: 600;
        color: var(--muted);
        margin-bottom: 10px;
    }

    /* Result card */
    .fs-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 20px 22px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px rgba(15,42,67,0.04);
    }
    .fs-card-top {
        display: flex; justify-content: space-between;
        align-items: flex-start; gap: 16px;
    }
    .fs-card h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.18rem; font-weight: 600;
        margin: 0 0 2px 0; color: var(--ink);
    }
    .fs-provider { color: var(--muted); font-size: 0.86rem; margin-bottom: 12px; }

    /* Destination tag */
    .fs-dest {
        display: inline-block; white-space: nowrap;
        background: #EAF1F7; color: var(--ink);
        font-size: 0.74rem; font-weight: 600;
        padding: 5px 11px; border-radius: 999px;
        font-family: 'Space Grotesk', sans-serif;
    }

    /* Match meter (the signature element) */
    .fs-meter-wrap { margin: 4px 0 14px 0; }
    .fs-meter-label {
        display: flex; justify-content: space-between;
        font-size: 0.74rem; color: var(--muted);
        margin-bottom: 5px; font-weight: 500;
    }
    .fs-meter-score { color: var(--gold); font-weight: 700; }
    .fs-meter-track {
        height: 8px; background: #ECEFF3;
        border-radius: 999px; overflow: hidden;
    }
    .fs-meter-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--gold) 0%, #FFC44D 100%);
        border-radius: 999px;
    }

    /* Why-it-fits line */
    .fs-why {
        background: #FBF6EC;
        border-left: 3px solid var(--gold);
        padding: 11px 14px; border-radius: 8px;
        font-size: 0.92rem; color: #4A3A14;
        margin-bottom: 14px; line-height: 1.5;
    }
    .fs-why b { color: var(--ink); }

    /* Fact grid */
    .fs-facts { display: flex; flex-wrap: wrap; gap: 10px 26px; margin-bottom: 16px; }
    .fs-fact { font-size: 0.86rem; }
    .fs-fact .k {
        display: block; color: var(--muted);
        font-size: 0.7rem; text-transform: uppercase;
        letter-spacing: 0.6px; margin-bottom: 2px;
    }
    .fs-fact .v { color: var(--ink); font-weight: 500; }

    /* Apply button */
    .fs-apply {
        display: inline-block; text-decoration: none;
        background: var(--ink); color: #fff !important;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600; font-size: 0.9rem;
        padding: 9px 18px; border-radius: 9px;
        transition: background 0.15s ease;
    }
    .fs-apply:hover { background: var(--go); }

    /* Empty / intro state */
    .fs-empty {
        background: var(--surface); border: 1px dashed var(--line);
        border-radius: 14px; padding: 40px 30px; text-align: center;
        color: var(--muted);
    }
    .fs-empty .big { font-size: 2rem; margin-bottom: 8px; }

    /* Tighten Streamlit's default form chrome a little */
    div[data-testid="stForm"] {
        background: var(--surface); border: 1px solid var(--line);
        border-radius: 14px; padding: 6px 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Hero
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="fs-hero">
        <h1>FirstStep<span class="accent">.</span></h1>
        <p>Tell us where you stand and where you want to go, and we'll rank the
        scholarships that fit you best from across our database and explain why
        each one made the list.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Layout: profile (left)  |  matches (right)
# --------------------------------------------------------------------------
left, right = st.columns([0.95, 1.55], gap="large")

with left:
    st.markdown('<div class="fs-eyebrow">Your profile</div>', unsafe_allow_html=True)
    with st.form("profile_form"):
        gpa = st.slider(
            "GPA (4.0 scale)", min_value=0.0, max_value=4.0, value=3.0, step=0.1,
            help="Use your cumulative GPA on a 4.0 scale.",
        )
        courses = st.text_input(
            "Courses / field of study :red[*]",
            placeholder="e.g. computer science, mathematics, data science",
        )
        interests = st.text_input(
            "Interests :red[*]",
            placeholder="e.g. AI, software engineering, research",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            level = st.selectbox(
                "Study level",
                options=["Any", "Bachelors", "Masters", "PhD"],
                index=0,
                help="The level of study you're applying for.",
            )
        with col_b:
            language = st.selectbox(
                "Language",
                options=["English", "French", "German"],
                index=0,
                help="Your primary language of study.",
            )
        locations = st.multiselect(
            "Preferred destinations",
            options=DESTINATIONS,
            default=[],
            help="Leave empty to consider every destination in the dataset.",
        )
        submitted = st.form_submit_button("Find my scholarships", type="primary")

    st.caption(
        "Tip: filling in courses and interests sharpens the match. "
        "Study level and language filter out scholarships you can't apply to."
    )

with right:
    st.markdown('<div class="fs-eyebrow">Your matches</div>', unsafe_allow_html=True)

    if not submitted:
        st.markdown(
            """
            <div class="fs-empty">
                <div>Fill in your profile and press <b>Find my scholarships</b>.<br>
                Your ranked matches will appear here.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        missing = []
        if not courses.strip():
            missing.append("Courses / field of study")
        if not interests.strip():
            missing.append("Interests")

        if missing:
            fields = " and ".join(missing)
            st.warning(
                f"Please fill in **{fields}** before searching. "
                "These fields help us find scholarships that are relevant to you."
            )
            st.stop()

        profile = {
            "gpa": gpa,
            "courses": courses,
            "interests": interests,
            "locations": locations,
            "level": level,
            "language": language,
        }
        results = get_recommendations(profile, top_k=8)

        if not results:
            st.markdown(
                '<div class="fs-empty">No scholarships matched your profile. '
                'Try widening your study level, language, or destinations.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption(f"Showing the top {len(results)} matches, strongest first.")
            for r in results:
                s = r["scholarship"]
                # Display scaling: raw TF-IDF scores sit ~0.1-0.5, so a strong
                # match (~0.5) reads as 100%. match_score itself stays raw.
                pct = min(int(round(r["match_score"] / 0.5 * 100)), 100)
                why = html.escape(r["explanation"])

                def fact(label, value):
                    return (
                        f'<div class="fs-fact"><span class="k">{html.escape(label)}</span>'
                        f'<span class="v">{html.escape(str(value))}</span></div>'
                    )

                facts = "".join([
                    fact("Level", s.get("level", "")),
                    fact("Funding", s.get("funding_type", "")),
                    fact("Deadline", s.get("deadline", "")),
                    fact("GPA / grade", s.get("min_gpa", "")),
                ])

                card = f"""
                <div class="fs-card">
                    <div class="fs-card-top">
                        <div>
                            <h3>{html.escape(s.get("name", "Untitled"))}</h3>
                            <div class="fs-provider">{html.escape(s.get("provider", ""))}</div>
                        </div>
                        <span class="fs-dest">{html.escape(s.get("country", ""))}</span>
                    </div>
                    <div class="fs-meter-wrap">
                        <div class="fs-meter-label">
                            <span>Match strength</span>
                            <span class="fs-meter-score">{pct}%</span>
                        </div>
                        <div class="fs-meter-track">
                            <div class="fs-meter-fill" style="width:{pct}%;"></div>
                        </div>
                    </div>
                    <div class="fs-why"><b>Why this fits you:</b> {why}</div>
                    <div class="fs-facts">{facts}</div>
                    <a class="fs-apply" href="{html.escape(s.get("apply_url", "#"))}"
                       target="_blank" rel="noopener noreferrer">Apply / learn more</a>
                </div>
                """
                st.markdown(card, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------
st.caption(
    "FirstStep · Scholarship and College Navigator for Gambian students. "
    "Scholarship details are indicative. Always confirm deadlines and eligibility "
    "on the official site before applying."
)
