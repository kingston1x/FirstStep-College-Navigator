"""
FirstStep Scholarship Navigator (front-end)
Run: streamlit run app.py
"""

import base64
import html
import os
import time

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
for _k, _v in [("page", "form"), ("results", []), ("last_profile", {})]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Logo (base64 so it embeds cleanly in HTML without static-file serving) ────
# Guarded: if the logo asset is ever missing, the app should still render
# (blank logo) instead of crashing on import before anyone sees a page.
_logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
try:
    with open(_logo_path, "rb") as _f:
        _logo_src = "data:image/png;base64," + base64.b64encode(_f.read()).decode()
except FileNotFoundError:
    _logo_src = ""

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
        padding: 36px 48px 32px;
        margin-bottom: 28px;
        color: #fff;
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        gap: 40px;
    }
    .fs-hero-content { flex: 1; min-width: 0; }
    .fs-hero-logo-right { flex-shrink: 0; }
    .fs-hero-logo-wrap {
        width: 180px;
        height: 103px;
        overflow: hidden;
        border-radius: 14px;
        box-shadow: 0 6px 28px rgba(0,0,0,0.32);
    }
    .fs-hero-logo-img {
        width: 180px;
        display: block;
        position: relative;
        top: -21px;
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
        background: rgba(244,163,0,0.16);
        color: var(--gold);
        font-size: 0.68rem; font-weight: 700;
        letter-spacing: 1.6px; text-transform: uppercase;
        padding: 4px 12px; border-radius: 999px;
        margin-bottom: 14px;
    }
    .fs-hero h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 2.55rem;
        margin: 0 0 14px 0;
        color: #fff;
        letter-spacing: -0.8px;
        line-height: 1.18;
    }
    .fs-hero h1 .accent { color: var(--gold); }
    .fs-hero p {
        margin: 0 0 18px 0;
        color: #B3C5D5;
        font-size: 1rem;
        max-width: 560px;
        line-height: 1.65;
    }
    .fs-trust {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 22px;
    }
    .fs-trust-item {
        color: rgba(255,255,255,0.6);
        font-size: 0.79rem;
        font-weight: 500;
    }
    .fs-trust-item b { color: rgba(255,255,255,0.85); font-weight: 600; }
    .fs-trust-sep {
        color: rgba(255,255,255,0.25);
        font-size: 0.75rem;
    }
    .fs-hero-cta {
        display: inline-block;
        background: var(--gold);
        color: var(--ink) !important;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 0.92rem;
        padding: 12px 26px;
        border-radius: 10px;
        text-decoration: none;
        letter-spacing: 0.2px;
        transition: background 0.15s ease, transform 0.12s ease;
    }
    .fs-hero-cta:hover { background: #e89d00; transform: translateY(-1px); }

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
        max-width: 860px;
        margin-left: auto;
        margin-right: auto;
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

    .fs-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 14px; }
    .fs-tag {
        font-size: 0.73rem; font-weight: 600;
        padding: 4px 10px; border-radius: 999px;
        font-family: 'Space Grotesk', sans-serif;
    }
    .fs-tag-country { background: #EAF1F7; color: #1A3A5C; }
    .fs-tag-funded  { background: #E6F7F1; color: #1A7A5E; }
    .fs-tag-neutral { background: #F0F4F8; color: var(--muted); }

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

    .fs-why {
        background: #FBF6EC;
        border-left: 3px solid var(--gold);
        padding: 10px 14px; border-radius: 8px;
        font-size: 0.88rem; color: #4A3A14;
        margin-bottom: 14px; line-height: 1.6;
    }
    .fs-why b { color: var(--ink); }

    .fs-facts { display: flex; flex-wrap: wrap; gap: 10px 24px; margin-bottom: 16px; }
    .fs-fact { font-size: 0.84rem; }
    .fs-fact .k {
        display: block; color: var(--muted);
        font-size: 0.67rem; text-transform: uppercase;
        letter-spacing: 0.7px; margin-bottom: 2px;
    }
    .fs-fact .v { color: var(--ink); font-weight: 600; }

    .fs-apply {
        display: inline-block; text-decoration: none;
        background: var(--ink); color: #fff !important;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600; font-size: 0.88rem;
        padding: 10px 20px; border-radius: 9px;
        transition: background 0.15s ease;
    }
    .fs-apply:hover { background: var(--go); }

    /* ── Loading screen ───────────────────────────────────────── */
    .fs-loading-screen {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 55vh;
        padding: 40px;
    }
    .fs-loading-inner {
        text-align: center;
        max-width: 460px;
        width: 100%;
    }
    .fs-spinner {
        width: 60px; height: 60px;
        border: 5px solid rgba(15,42,67,0.08);
        border-top-color: var(--gold);
        border-radius: 50%;
        animation: fs-spin 0.85s linear infinite;
        margin: 0 auto 32px;
    }
    @keyframes fs-spin { to { transform: rotate(360deg); } }
    .fs-loading-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.55rem; font-weight: 700;
        color: var(--ink); margin: 0 0 10px;
    }
    .fs-loading-sub {
        color: var(--muted); font-size: 0.92rem;
        margin: 0 0 32px; line-height: 1.65;
    }
    .fs-loading-steps {
        display: flex; flex-direction: column; gap: 12px;
        text-align: left;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 18px 20px;
    }
    .fs-loading-step {
        display: flex; align-items: center; gap: 12px;
        font-size: 0.86rem; color: var(--muted);
    }
    .fs-loading-dot {
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #D0D8E4;
        flex-shrink: 0;
        animation: fs-pulse 1.6s ease-in-out infinite;
    }
    .fs-loading-dot.active {
        background: var(--gold);
        animation: fs-pulse 0.9s ease-in-out infinite;
    }
    @keyframes fs-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.45; transform: scale(0.85); }
    }

    /* ── Results page header ──────────────────────────────────── */
    .fs-results-header {
        display: flex;
        align-items: center;
        gap: 18px;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 16px 22px;
        margin-bottom: 22px;
    }
    .fs-results-logo-wrap {
        width: 80px; height: 46px;
        overflow: hidden; border-radius: 8px;
        flex-shrink: 0;
    }
    .fs-results-logo-img {
        width: 80px; display: block;
        position: relative; top: -9px;
    }
    .fs-results-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.15rem; font-weight: 700;
        color: var(--ink); margin: 0 0 2px;
    }
    .fs-results-sub {
        font-size: 0.82rem; color: var(--muted); margin: 0;
    }
    .fs-results-count {
        font-size: 0.84rem; font-weight: 600;
        color: var(--muted); margin-bottom: 16px;
    }
    .fs-results-cards { max-width: 860px; margin: 0 auto; }

    /* Helper caption under GPA */
    .fs-gpa-hint { font-size: 0.76rem; color: var(--muted); margin-top: -6px; margin-bottom: 8px; }

    /* ── Mobile ───────────────────────────────────────────────── */
    @media (max-width: 768px) {
        .fs-hero { padding: 24px 22px 22px; flex-direction: column; gap: 20px; }
        .fs-hero h1 { font-size: 1.8rem; }
        .fs-hero-logo-right { order: -1; align-self: flex-start; }
        .fs-hero-logo-wrap { width: 140px; height: 80px; }
        .fs-hero-logo-img { width: 140px; top: -16px; }
        .fs-trust { gap: 4px; }
        .fs-trust-item { font-size: 0.76rem; }
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
        .fs-results-header { flex-wrap: wrap; gap: 12px; }
        .fs-loading-screen { padding: 24px 16px; }
        .fs-loading-title { font-size: 1.3rem; }
    }
    @media (max-width: 480px) {
        .fs-hero h1 { font-size: 1.55rem; }
        .fs-empty-wrap { padding: 30px 20px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helper: build a scholarship card HTML string ──────────────────────────────
def _fact(label: str, value: str) -> str:
    if not str(value).strip():
        return ""
    return (
        f'<div class="fs-fact">'
        f'<span class="k">{html.escape(label)}</span>'
        f'<span class="v">{html.escape(str(value))}</span>'
        f'</div>'
    )


def _build_card(r: dict) -> str:
    s = r["scholarship"]
    match_pct = min(int(round(r["match_score"] / 0.5 * 100)), 100)
    why = html.escape(r["explanation"])

    if match_pct >= 70:
        badge_cls, badge_label = "strong", f"{match_pct}% Strong Match"
    elif match_pct >= 40:
        badge_cls, badge_label = "good", f"{match_pct}% Good Match"
    else:
        badge_cls, badge_label = "fair", f"{match_pct}% Partial Match"

    country = s.get("country", "")
    funding = s.get("funding_type", "")
    lvl = s.get("level", "")

    tags = ""
    if country:
        tags += f'<span class="fs-tag fs-tag-country">{html.escape(country)}</span>'
    if "fully" in funding.lower():
        tags += '<span class="fs-tag fs-tag-funded">Fully Funded</span>'
    elif funding:
        tags += f'<span class="fs-tag fs-tag-neutral">{html.escape(funding)}</span>'
    if lvl:
        tags += f'<span class="fs-tag fs-tag-neutral">{html.escape(lvl)}</span>'

    facts = "".join([
        _fact("Deadline", s.get("deadline", "")),
        _fact("Min GPA",  s.get("min_gpa", "")),
        _fact("Value",    s.get("value", "")),
    ])

    return f"""
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
           href="{html.escape(s.get('apply_url', '#'))}"
           target="_blank" rel="noopener noreferrer">View Details</a>
    </div>
    """


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FORM
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "form":

    st.markdown(
        f"""
        <div class="fs-hero">
            <div class="fs-hero-content">
                <div class="fs-tag">Scholarship Navigator</div>
                <h1>Find Scholarships That<br><span class="accent">Match Your Academic Profile</span></h1>
                <p>Tell us your field of study and interests we'll instantly rank the best
                scholarships for you from our global database and explain exactly why each one fits.</p>
                <div class="fs-trust">
                    <span class="fs-trust-item"><b>&#10003; Personalized Matches</b></span>
                    <span class="fs-trust-sep">&middot;</span>
                    <span class="fs-trust-item"><b>&#10003; Global Database</b></span>
                    <span class="fs-trust-sep">&middot;</span>
                    <span class="fs-trust-item"><b>&#10003; Instant Results</b></span>
                </div>
                <a class="fs-hero-cta" href="#" onclick="
                    var el = window.parent.document.querySelector('input');
                    if(el) el.scrollIntoView({{behavior:'smooth', block:'center'}});
                    return false;">Find Matching Scholarships</a>
            </div>
            <div class="fs-hero-logo-right">
                <div class="fs-hero-logo-wrap">
                    <img src="{_logo_src}" class="fs-hero-logo-img" alt="FirstStep Logo"/>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1.6], gap="large")

    with left:
        # Profile completion reads session state from previous render
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

        bar_color = "#1E8E6F" if completion >= 70 else "#F4A300" if completion >= 30 else "#CBD5E0"

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
                st.session_state.last_profile = {
                    "gpa":       float(gpa),
                    "courses":   courses,
                    "interests": ", ".join(interests),
                    "locations": locations,
                    "level":     level,
                    "language":  language,
                }
                st.session_state.page = "loading"
                st.rerun()

        st.caption(
            "Fields marked * are required. Study level and language filter out "
            "scholarships you cannot apply to."
        )

    with right:
        st.markdown('<div class="fs-eyebrow">Your Matches</div>', unsafe_allow_html=True)
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


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LOADING
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "loading":
    profile = st.session_state.get("last_profile", {})
    courses_display = html.escape(profile.get("courses", "your field"))

    st.markdown(
        f"""
        <div class="fs-loading-screen">
            <div class="fs-loading-inner">
                <div class="fs-spinner"></div>
                <h2 class="fs-loading-title">Finding Your Matches</h2>
                <p class="fs-loading-sub">
                    Scanning our global scholarship database for
                    <strong>{courses_display}</strong> students...
                </p>
                <div class="fs-loading-steps">
                    <div class="fs-loading-step">
                        <span class="fs-loading-dot active"></span>
                        <span>Analyzing your academic profile</span>
                    </div>
                    <div class="fs-loading-step">
                        <span class="fs-loading-dot active"></span>
                        <span>Matching scholarships to your interests</span>
                    </div>
                    <div class="fs-loading-step">
                        <span class="fs-loading-dot"></span>
                        <span>Ranking by best fit</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    results = get_recommendations(profile, top_k=8)
    st.session_state.results = results

    # Brief pause so the loading screen is visible while CSS animation plays
    time.sleep(2)

    st.session_state.page = "results"
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: RESULTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "results":
    profile = st.session_state.get("last_profile", {})
    results = st.session_state.results

    n = len(results)
    level_str    = profile.get("level", "")
    language_str = profile.get("language", "")
    courses_str  = profile.get("courses", "")
    sub_parts    = [p for p in [courses_str, level_str, language_str] if p and p != "Any"]

    # Header bar
    hcol, bcol = st.columns([5, 1])
    with hcol:
        st.markdown(
            f"""
            <div class="fs-results-header">
                <div class="fs-results-logo-wrap">
                    <img src="{_logo_src}" class="fs-results-logo-img" alt="FirstStep Logo"/>
                </div>
                <div>
                    <div class="fs-results-title">
                        {n} Scholarship{"s" if n != 1 else ""} Found
                    </div>
                    <div class="fs-results-sub">
                        {" &middot; ".join(html.escape(p) for p in sub_parts)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with bcol:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("Search Again", type="primary", use_container_width=True):
            st.session_state.page = "form"
            st.rerun()

    # Results
    if not results:
        st.markdown(
            """
            <div class="fs-empty-wrap" style="max-width:560px; margin:0 auto;">
                <div class="fs-empty-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30"
                         viewBox="0 0 24 24" fill="none" stroke="#5B6B7B"
                         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="m21 21-4.35-4.35"/>
                    </svg>
                </div>
                <h3>No scholarships matched</h3>
                <p>Try widening your study level or language, or leave destinations
                empty to search across all countries.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="fs-results-count">Showing {n} match{"es" if n != 1 else ""}, strongest first</div>',
            unsafe_allow_html=True,
        )
        for r in results:
            st.markdown(_build_card(r), unsafe_allow_html=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(
    "FirstStep · Scholarship and College Navigator for Gambian students. "
    "Scholarship details are indicative. Always confirm deadlines and eligibility "
    "on the official site before applying."
)