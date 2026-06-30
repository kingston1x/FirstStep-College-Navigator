"""
FirstStep Scholarship Navigator (front-end)
Run: streamlit run app.py
"""

import html

import streamlit as st

from recommender import get_recommendations, available_countries

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FirstStep Scholarship Navigator",
    page_icon="FS",
    layout="wide",
)

DESTINATIONS = available_countries()

INTEREST_OPTIONS = sorted([
    "AI and Machine Learning", "Software Engineering", "Data Science", "Cybersecurity",
    "Public Health", "Medicine", "Healthcare", "Epidemiology", "Global Health",
    "Environmental Science", "Climate Change", "Sustainability", "Renewable Energy",
    "Business", "Entrepreneurship", "Finance", "Economics", "Management",
    "Development Studies", "International Relations", "Governance", "Public Policy",
    "Education", "Teaching", "Literacy", "Curriculum Development",
    "Engineering", "Technology", "Innovation", "Robotics",
    "Agriculture", "Food Security", "Rural Development",
    "Arts and Culture", "Design", "Media", "Film", "Fashion",
    "Mathematics", "Physics", "Chemistry", "Biology",
    "Research", "Science Communication", "Academic Writing",
    "Law", "Human Rights", "Social Justice",
    "Architecture", "Urban Planning", "Infrastructure",
])

# ── Session state ─────────────────────────────────────────────────────────────
for _k, _v in [("search_done", False), ("results", [])]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

    :root {
        --ink:     #0F2A43;
        --gold:    #F4A300;
        --go:      #1E8E6F;
        --muted:   #5B6B7B;
        --line:    #E2E8F0;
        --surface: #FFFFFF;
        --bg:      #F3F5F8;
    }

    .stApp { background: var(--bg); }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--ink); }

    /* ── Hero ─────────────────────────────────────────────────── */
    .fs-hero {
        background: linear-gradient(135deg, #0B1F33 0%, #163352 55%, #1A4A6E 100%);
        border-radius: 20px;
        padding: 44px 48px 40px;
        margin-bottom: 28px;
        color: #fff;
        position: relative;
        overflow: hidden;
    }
    .fs-hero::before {
        content: '';
        position: absolute;
        top: -80px; right: -80px;
        width: 260px; height: 260px;
        background: rgba(244,163,0,0.07);
        border-radius: 50%;
        pointer-events: none;
    }
    .fs-hero::after {
        content: '';
        position: absolute;
        bottom: -40px; left: 40%;
        width: 160px; height: 160px;
        background: rgba(30,142,111,0.07);
        border-radius: 50%;
        pointer-events: none;
    }
    .fs-tag {
        display: inline-block;
        background: rgba(244,163,0,0.18);
        color: var(--gold);
        font-size: 0.7rem; font-weight: 700;
        letter-spacing: 1.6px; text-transform: uppercase;
        padding: 4px 12px; border-radius: 999px;
        margin-bottom: 16px;
    }
    .fs-hero h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        margin: 0 0 12px 0;
        letter-spacing: -1px;
        color: #fff;
        line-height: 1.15;
    }
    .fs-hero .accent { color: var(--gold); }
    .fs-hero p {
        margin: 0 0 26px 0;
        color: #B3C5D5;
        font-size: 1.05rem;
        max-width: 560px;
        line-height: 1.65;
    }
    .fs-trust { display: flex; gap: 20px; flex-wrap: wrap; }
    .fs-trust-item {
        display: flex; align-items: center; gap: 8px;
        color: #C0D0DF; font-size: 0.86rem; font-weight: 500;
    }
    .fs-trust-check {
        width: 20px; height: 20px;
        background: var(--go);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.62rem; font-weight: 700; color: #fff;
        flex-shrink: 0;
    }

    /* ── Eyebrow ──────────────────────────────────────────────── */
    .fs-eyebrow {
        font-family: 'Space Grotesk', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1.6px;
        font-size: 0.68rem;
        font-weight: 700;
        color: var(--muted);
        margin-bottom: 14px;
    }

    /* ── Completion bar ───────────────────────────────────────── */
    .fs-completion {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 20px;
    }
    .fs-completion-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 8px;
        font-size: 0.8rem; font-weight: 600; color: var(--muted);
    }
    .fs-completion-pct { color: var(--ink); font-weight: 700; font-size: 0.9rem; }
    .fs-completion-track {
        height: 6px; background: #E8EDF2;
        border-radius: 999px; overflow: hidden;
    }
    .fs-completion-fill { height: 100%; border-radius: 999px; transition: width 0.3s ease; }

    /* ── Primary CTA button ───────────────────────────────────── */
    .stButton > button[kind="primary"] {
        height: 52px !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        background-color: var(--ink) !important;
        border-color: var(--ink) !important;
        border-radius: 12px !important;
        letter-spacing: 0.2px;
        transition: background-color 0.18s ease, transform 0.12s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: var(--go) !important;
        border-color: var(--go) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="primary"]:active { transform: translateY(0) !important; }

    /* ── Form chrome ──────────────────────────────────────────── */
    div[data-testid="stForm"] { background: transparent; border: none; padding: 0; }

    /* ── Empty state ──────────────────────────────────────────── */
    .fs-empty-wrap {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 44px 32px 40px;
        text-align: center;
        margin-bottom: 20px;
    }
    .fs-empty-icon {
        width: 68px; height: 68px;
        background: #EBF2F8;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 20px;
    }
    .fs-empty-wrap h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.2rem; font-weight: 700;
        color: var(--ink); margin: 0 0 8px 0;
    }
    .fs-empty-wrap p {
        color: var(--muted); font-size: 0.9rem;
        line-height: 1.65; max-width: 340px; margin: 0 auto;
    }

    /* ── How it works ─────────────────────────────────────────── */
    .fs-how {
        display: flex;
        border-top: 1px solid var(--line);
        margin-top: 30px; padding-top: 28px;
        gap: 0;
    }
    .fs-how-step {
        flex: 1; text-align: center; padding: 0 18px;
        border-right: 1px solid var(--line);
    }
    .fs-how-step:last-child { border-right: none; }
    .fs-how-num {
        width: 34px; height: 34px;
        background: var(--ink); color: #fff;
        border-radius: 50%;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700; font-size: 0.88rem;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 12px;
    }
    .fs-how-step h4 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.84rem; font-weight: 700;
        color: var(--ink); margin: 0 0 5px 0;
    }
    .fs-how-step p {
        font-size: 0.78rem; color: var(--muted); margin: 0; line-height: 1.55;
    }

    /* ── Stats bar ────────────────────────────────────────────── */
    .fs-stats {
        display: flex;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        overflow: hidden;
    }
    .fs-stat { flex: 1; text-align: center; padding: 18px 10px; border-right: 1px solid var(--line); }
    .fs-stat:last-child { border-right: none; }
    .fs-stat-num {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.4rem; font-weight: 700;
        color: var(--ink); display: block;
    }
    .fs-stat-label { font-size: 0.74rem; color: var(--muted); font-weight: 500; display: block; margin-top: 3px; }

    /* ── Result cards ─────────────────────────────────────────── */
    .fs-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 20px 22px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(15,42,67,0.05);
        transition: box-shadow 0.18s ease, transform 0.12s ease;
    }
    .fs-card:hover {
        box-shadow: 0 6px 20px rgba(15,42,67,0.1);
        transform: translateY(-1px);
    }
    .fs-card-top {
        display: flex; justify-content: space-between;
        align-items: flex-start; gap: 12px; margin-bottom: 10px;
    }
    .fs-card h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.05rem; font-weight: 700;
        margin: 0 0 3px 0; color: var(--ink); line-height: 1.3;
    }
    .fs-provider { color: var(--muted); font-size: 0.82rem; }

    /* Match badge */
    .fs-badge-match {
        display: inline-block;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.76rem; font-weight: 700;
        padding: 5px 11px; border-radius: 8px;
        white-space: nowrap; flex-shrink: 0;
    }
    .fs-badge-match.strong { background: #E6F7F1; color: #1A7A5E; }
    .fs-badge-match.good   { background: #FFF8E6; color: #A07000; }
    .fs-badge-match.fair   { background: #F0F4F8; color: var(--muted); }

    /* Tag chips */
    .fs-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 14px; }
    .fs-tag {
        font-size: 0.73rem; font-weight: 600;
        padding: 4px 10px; border-radius: 999px;
        font-family: 'Space Grotesk', sans-serif;
    }
    .fs-tag-country { background: #EAF1F7; color: #1A3A5C; }
    .fs-tag-funded  { background: #E6F7F1; color: #1A7A5E; }
    .fs-tag-neutral { background: #F0F4F8; color: var(--muted); }

    /* Meter */
    .fs-meter-wrap { margin: 0 0 14px 0; }
    .fs-meter-label {
        display: flex; justify-content: space-between;
        font-size: 0.72rem; color: var(--muted);
        margin-bottom: 5px; font-weight: 500;
    }
    .fs-meter-score { color: var(--gold); font-weight: 700; }
    .fs-meter-track { height: 6px; background: #ECEFF3; border-radius: 999px; overflow: hidden; }
    .fs-meter-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--gold) 0%, #FFC44D 100%);
        border-radius: 999px;
    }

    /* Why it fits */
    .fs-why {
        background: #FBF6EC;
        border-left: 3px solid var(--gold);
        padding: 10px 14px; border-radius: 8px;
        font-size: 0.88rem; color: #4A3A14;
        margin-bottom: 14px; line-height: 1.6;
    }
    .fs-why b { color: var(--ink); }

    /* Fact grid */
    .fs-facts { display: flex; flex-wrap: wrap; gap: 10px 24px; margin-bottom: 16px; }
    .fs-fact { font-size: 0.84rem; }
    .fs-fact .k {
        display: block; color: var(--muted);
        font-size: 0.67rem; text-transform: uppercase;
        letter-spacing: 0.7px; margin-bottom: 2px;
    }
    .fs-fact .v { color: var(--ink); font-weight: 600; }

    /* Apply CTA */
    .fs-apply {
        display: inline-block; text-decoration: none;
        background: var(--ink); color: #fff !important;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600; font-size: 0.88rem;
        padding: 10px 20px; border-radius: 9px;
        transition: background 0.15s ease;
    }
    .fs-apply:hover { background: var(--go); }

    /* Results header */
    .fs-results-count {
        font-size: 0.84rem; font-weight: 600;
        color: var(--muted); margin-bottom: 16px;
    }

    /* Helper caption under GPA */
    .fs-gpa-hint { font-size: 0.76rem; color: var(--muted); margin-top: -6px; margin-bottom: 8px; }

    /* ── Mobile ───────────────────────────────────────────────── */
    @media (max-width: 768px) {
        .fs-hero { padding: 28px 24px; }
        .fs-hero h1 { font-size: 1.85rem; }
        .fs-trust { gap: 12px; }
        .fs-trust-item { font-size: 0.8rem; }
        .fs-how { flex-direction: column; gap: 0; }
        .fs-how-step {
            border-right: none;
            border-bottom: 1px solid var(--line);
            padding: 14px 0;
        }
        .fs-how-step:last-child { border-bottom: none; }
        .fs-stats { flex-wrap: wrap; }
        .fs-stat { min-width: 50%; border-right: none; border-bottom: 1px solid var(--line); }
        .fs-card-top { flex-direction: column; gap: 8px; }
        .fs-badge-match { align-self: flex-start; }
    }
    @media (max-width: 480px) {
        .fs-hero h1 { font-size: 1.55rem; }
        .fs-empty-wrap { padding: 30px 20px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="fs-hero">
        <div class="fs-tag">Scholarship Navigator</div>
        <h1>Find Your Perfect<br><span class="accent">Scholarship Match</span></h1>
        <p>Tell us about your academic profile and we'll instantly match you with
        the best scholarship opportunities from our global database.</p>
        <div class="fs-trust">
            <div class="fs-trust-item">
                <div class="fs-trust-check">&#10003;</div>
                <span>Personalized Scholarship Matches</span>
            </div>
            <div class="fs-trust-item">
                <div class="fs-trust-check">&#10003;</div>
                <span>Global Scholarship Database</span>
            </div>
            <div class="fs-trust-item">
                <div class="fs-trust-check">&#10003;</div>
                <span>Instant Recommendations</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Layout ────────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1.6], gap="large")

with left:
    # Profile completion (reads session state set by previous renders)
    courses_val   = str(st.session_state.get("fs_courses", "") or "")
    interests_val = st.session_state.get("fs_interests", []) or []
    gpa_val       = float(st.session_state.get("fs_gpa", 0.0) or 0.0)
    level_val     = st.session_state.get("fs_level", "Any") or "Any"
    locations_val = st.session_state.get("fs_locations", []) or []

    completion = 0
    if courses_val.strip():  completion += 30
    if interests_val:        completion += 30
    if gpa_val > 0:          completion += 15
    if level_val != "Any":   completion += 15
    if locations_val:        completion += 10

    if completion >= 70:
        bar_color = "#1E8E6F"
    elif completion >= 30:
        bar_color = "#F4A300"
    else:
        bar_color = "#CBD5E0"

    st.markdown(
        f"""
        <div class="fs-completion">
            <div class="fs-completion-header">
                <span>Profile Completion</span>
                <span class="fs-completion-pct">{completion}%</span>
            </div>
            <div class="fs-completion-track">
                <div class="fs-completion-fill"
                     style="width:{completion}%; background:{bar_color};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="fs-eyebrow">Your Profile</div>', unsafe_allow_html=True)

    courses = st.text_input(
        "Field of Study :red[*]",
        key="fs_courses",
        placeholder="e.g. Computer Science, Public Health, Engineering",
    )

    interests = st.multiselect(
        "Interests :red[*]",
        options=INTEREST_OPTIONS,
        key="fs_interests",
        help="Select the areas you are most passionate about.",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        level = st.selectbox(
            "Study Level",
            options=["Any", "Bachelors", "Masters", "PhD"],
            key="fs_level",
        )
    with col_b:
        language = st.selectbox(
            "Language",
            options=["English", "French", "German"],
            key="fs_language",
        )

    locations = st.multiselect(
        "Preferred Destinations",
        options=DESTINATIONS,
        key="fs_locations",
        help="Leave empty to see scholarships from all destinations.",
    )

    gpa = st.number_input(
        "GPA (4.0 Scale)",
        min_value=0.0,
        max_value=4.0,
        value=0.0,
        step=0.01,
        format="%.2f",
        key="fs_gpa",
    )
    st.markdown('<div class="fs-gpa-hint">Enter GPA between 0.00 and 4.00</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if st.button("Find Matching Scholarships", type="primary", use_container_width=True):
        missing = []
        if not courses.strip():
            missing.append("Field of Study")
        if not interests:
            missing.append("Interests")

        if missing:
            st.warning(
                f"Please fill in **{' and '.join(missing)}** to find your scholarships."
            )
        else:
            interests_str = ", ".join(interests)
            profile = {
                "gpa":       float(gpa),
                "courses":   courses,
                "interests": interests_str,
                "locations": locations,
                "level":     level,
                "language":  language,
            }
            with st.spinner("Finding your best matches..."):
                st.session_state.results = get_recommendations(profile, top_k=8)
            st.session_state.search_done = True

    st.caption(
        "Fields marked * are required. Study level and language filter out "
        "scholarships you cannot apply to."
    )

# ── Right panel ───────────────────────────────────────────────────────────────
with right:
    st.markdown('<div class="fs-eyebrow">Your Matches</div>', unsafe_allow_html=True)

    if not st.session_state.search_done:
        st.markdown(
            """
            <div class="fs-empty-wrap">
                <div class="fs-empty-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30"
                         viewBox="0 0 24 24" fill="none" stroke="#0F2A43"
                         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="m21 21-4.35-4.35"/>
                    </svg>
                </div>
                <h3>No scholarships yet</h3>
                <p>Complete your profile and we'll instantly find scholarships
                tailored to your interests and academic goals.</p>
                <div class="fs-how">
                    <div class="fs-how-step">
                        <div class="fs-how-num">1</div>
                        <h4>Fill Your Profile</h4>
                        <p>Tell us your field, interests, and academic level</p>
                    </div>
                    <div class="fs-how-step">
                        <div class="fs-how-num">2</div>
                        <h4>We Match Instantly</h4>
                        <p>Our model ranks scholarships by how well they fit you</p>
                    </div>
                    <div class="fs-how-step">
                        <div class="fs-how-num">3</div>
                        <h4>Apply with Confidence</h4>
                        <p>See exactly why each scholarship is right for you</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="fs-stats">
                <div class="fs-stat">
                    <span class="fs-stat-num">29+</span>
                    <span class="fs-stat-label">Scholarships</span>
                </div>
                <div class="fs-stat">
                    <span class="fs-stat-num">15+</span>
                    <span class="fs-stat-label">Countries</span>
                </div>
                <div class="fs-stat">
                    <span class="fs-stat-num">100%</span>
                    <span class="fs-stat-label">Free to Use</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        results = st.session_state.results

        if not results:
            st.markdown(
                """
                <div class="fs-empty-wrap">
                    <div class="fs-empty-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30"
                             viewBox="0 0 24 24" fill="none" stroke="#5B6B7B"
                             stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="11" cy="11" r="8"/>
                            <path d="m21 21-4.35-4.35"/>
                        </svg>
                    </div>
                    <h3>No scholarships matched</h3>
                    <p>Try widening your study level or language, or leave
                    destinations empty to search across all countries.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="fs-results-count">'
                f'Showing {len(results)} matches, strongest first'
                f'</div>',
                unsafe_allow_html=True,
            )

            for r in results:
                s = r["scholarship"]
                match_pct = min(int(round(r["match_score"] / 0.5 * 100)), 100)
                why = html.escape(r["explanation"])

                if match_pct >= 70:
                    badge_cls, badge_label = "strong", f"{match_pct}% Strong Match"
                elif match_pct >= 40:
                    badge_cls, badge_label = "good", f"{match_pct}% Good Match"
                else:
                    badge_cls, badge_label = "fair", f"{match_pct}% Partial Match"

                country  = s.get("country", "")
                funding  = s.get("funding_type", "")
                lvl      = s.get("level", "")

                tags = ""
                if country:
                    tags += f'<span class="fs-tag fs-tag-country">{html.escape(country)}</span>'
                if "fully" in funding.lower():
                    tags += '<span class="fs-tag fs-tag-funded">Fully Funded</span>'
                elif funding:
                    tags += f'<span class="fs-tag fs-tag-neutral">{html.escape(funding)}</span>'
                if lvl:
                    tags += f'<span class="fs-tag fs-tag-neutral">{html.escape(lvl)}</span>'

                def fact(label, value):
                    if not str(value).strip():
                        return ""
                    return (
                        f'<div class="fs-fact">'
                        f'<span class="k">{html.escape(label)}</span>'
                        f'<span class="v">{html.escape(str(value))}</span>'
                        f'</div>'
                    )

                facts = "".join([
                    fact("Deadline",  s.get("deadline", "")),
                    fact("Min GPA",   s.get("min_gpa", "")),
                    fact("Value",     s.get("value", "")),
                ])

                card = f"""
                <div class="fs-card">
                    <div class="fs-card-top">
                        <div>
                            <h3>{html.escape(s.get("name", "Untitled"))}</h3>
                            <div class="fs-provider">{html.escape(s.get("provider", ""))}</div>
                        </div>
                        <span class="fs-badge-match {badge_cls}">{badge_label}</span>
                    </div>
                    <div class="fs-tags">{tags}</div>
                    <div class="fs-meter-wrap">
                        <div class="fs-meter-label">
                            <span>Match strength</span>
                            <span class="fs-meter-score">{match_pct}%</span>
                        </div>
                        <div class="fs-meter-track">
                            <div class="fs-meter-fill" style="width:{match_pct}%;"></div>
                        </div>
                    </div>
                    <div class="fs-why"><b>Why this fits you:</b> {why}</div>
                    <div class="fs-facts">{facts}</div>
                    <a class="fs-apply"
                       href="{html.escape(s.get("apply_url", "#"))}"
                       target="_blank" rel="noopener noreferrer">View Details</a>
                </div>
                """
                st.markdown(card, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(
    "FirstStep · Scholarship and College Navigator for Gambian students. "
    "Scholarship details are indicative. Always confirm deadlines and eligibility "
    "on the official site before applying."
)
