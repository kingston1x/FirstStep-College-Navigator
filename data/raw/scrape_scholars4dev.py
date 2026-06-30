"""
scrape_scholars4dev.py  (v3 — full-text capture + inference)
------------------------------------------------------------
FirstStep Project — Phase 2: Data Collection

Strategy A: instead of hunting for neat "Eligibility:" / "Field of study:"
labels (which scholars4dev does NOT use), this version:

  1. Reliably grabs the WHOLE clean article body — paragraphs AND list items —
     after stripping nav / sidebar / related-posts / comments noise. That body
     text becomes the `description` (never empty) and the fuel for everything else.
  2. INFERS the structured fields from that text by signal, not by label:
       - field_of_study : trigger phrases ("courses in", "studies in", ...) plus
                          a subject-keyword fallback scan.
       - funding_type   : detected from benefit signals (stipend, allowance,
                          tuition, airfare, insurance) — not the literal word
                          "funding", which the pages rarely use.
       - value          : the benefit phrases themselves (amounts, allowances).
       - eligibility    : pulled from bullet (<li>) items and eligibility headings.
  3. Flags weak rows with needs_review=yes so you know what to hand-clean.

Why this design: scholars4dev is a SUMMARY site with bulleted, inconsistent
prose. Capturing everything + inferring is far more robust than per-label regex,
and it gives you complete raw material to clean afterwards.

The parsing functions (infer_*, build_description) take plain text/lists, so they
are unit-testable WITHOUT network access — see test_parsers() at the bottom.

Usage:
    python scrape_scholars4dev.py --pages 3 --output Scholarships.csv
    python scrape_scholars4dev.py --selftest      # run parser tests, no network

Dependencies:
    pip install requests beautifulsoup4 pandas lxml
"""

import argparse
import re
import time
from datetime import date

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ─── Config ───────────────────────────────────────────────────────────────────

BASE_URL = "https://www.scholars4dev.com/category/target-group/africans-scholarships/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
DELAY = 2
COLLECTOR_NAME = "Emmanuel"

SCHEMA = [
    "id", "name", "provider", "country", "level", "field_of_study", "min_gpa",
    "funding_type", "value", "deadline", "eligibility", "language_req",
    "description", "apply_url", "source_url", "source_type", "collected_by",
    "date_added",
]

NOISE_SELECTORS = [
    "script", "style", "nav", "footer", "aside", "form", "noscript",
    ".sharedaddy", ".jp-relatedposts", ".yarpp-related", ".related-posts",
    "#comments", ".comments", ".comment-respond", ".wp-block-buttons",
    ".social", ".sidebar", ".widget", ".breadcrumb", ".author-box",
]

SUBJECT_WORDS = [
    "engineering", "economics", "business administration", "business",
    "computer science", "data science", "information technology", "mathematics",
    "medicine", "public health", "health", "agriculture", "forestry",
    "environmental", "natural sciences", "social sciences", "law", "education",
    "political", "development", "management", "finance", "architecture",
    "urban planning", "arts", "design", "media", "science", "humanities",
    "physics", "chemistry", "biology",
]

# ─── Cleaning maps ────────────────────────────────────────────────────────────

COUNTRY_FIX = {
    "milan, italy": "Italy", "london, uk": "UK", "any country*": "Various",
    "any country (online)": "Online", "any country": "Various",
    "selected countries": "Various", "n/a": "Various",
}

def clean_country(raw: str) -> str:
    key = (raw or "").strip().lower()
    return COUNTRY_FIX.get(key, (raw or "Various").strip())

def clean_level(raw: str) -> str:
    t = (raw or "").lower()
    parts = []
    if "bachelor" in t or "undergrad" in t: parts.append("Bachelors")
    if "master" in t or "postgrad" in t:    parts.append("Masters")
    if "phd" in t or "doctora" in t:        parts.append("PhD")
    return "/".join(parts) if parts else "Any"

# ─── Networking ───────────────────────────────────────────────────────────────

def get_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [ERROR] {url}: {e}")
        return None

# ─── Content extraction (robust, with fallback) ──────────────────────────────

def extract_body(soup):
    """
    Return (paragraphs, list_items, full_text) for the main article body.
    Tries known containers, strips noise, and falls back to the densest block.
    """
    candidates = []
    for sel in [".entry-content", ".post-content", "article .entry",
                "article", ".post", "#content", "main"]:
        candidates.extend(soup.select(sel))
    if not soup.select_one(".entry-content, article, .post"):
        candidates.append(soup.body or soup)

    best, best_len = None, 0
    for node in candidates:
        if node is None:
            continue
        clone = BeautifulSoup(str(node), "html.parser")
        for sel in NOISE_SELECTORS:
            for bad in clone.select(sel):
                bad.decompose()
        text_len = len(clone.get_text(" ", strip=True))
        if text_len > best_len:
            best, best_len = clone, text_len

    if best is None:
        return [], [], ""

    paras = [p.get_text(" ", strip=True) for p in best.find_all("p")
             if len(p.get_text(strip=True)) > 40]
    lis = [li.get_text(" ", strip=True) for li in best.find_all("li")
           if len(li.get_text(strip=True)) > 15]
    full = re.sub(r"\s+", " ", best.get_text(" ", strip=True))
    return paras, lis, full

# ─── Field inference (text-only, unit-testable) ──────────────────────────────

def build_description(paras, lis, full):
    if paras:
        text = " ".join(paras)
    elif full:
        text = full
    else:
        text = " ".join(lis)
    return re.sub(r"\s+", " ", text).strip()[:900]

def infer_field_of_study(full):
    trig = re.search(
        r"(?:courses?|studies|degree programmes?|programs?|study programmes?|"
        r"disciplines?|fields? of study|in the fields? of|subjects?)\s+"
        r"(?:in|of|:)?\s+(.{12,220}?)(?:\.\s|;\s(?:[A-Z])|\bSee\b|$)", full, re.I)
    if trig:
        cand = trig.group(1).strip(" .:;")
        if len(cand) >= 10:
            return cand[:200], False
    found = []
    low = full.lower()
    for w in SUBJECT_WORDS:
        if w in low:
            found.append(w.title())
    if found:
        return "; ".join(dict.fromkeys(found))[:200], False
    return "Various fields", True

def infer_funding(full):
    low = full.lower()
    explicit_full = re.search(r"full[ly\s-]*fund|full scholarship|"
                              r"covers? (?:all|full|tuition and living)", low)
    benefit_signals = sum(bool(re.search(p, low)) for p in [
        r"stipend", r"monthly (?:payment|allowance|stipend)", r"tuition",
        r"travel allowance|airfare|air ticket|flight", r"insurance",
        r"living (?:allowance|expenses|costs)", r"accommodation",
    ])
    if explicit_full or benefit_signals >= 2:
        return "Fully Funded", False
    if re.search(r"tuition[- ]free|no tuition", low):
        return "Tuition-Free", False
    if re.search(r"partial|tuition (?:fee )?(?:reduction|waiver)|discount|"
                 r"contribution towards", low):
        return "Partial", False
    if re.search(r"stipend|allowance|fellowship|bursary", low):
        return "Stipend", False
    return "N/A", True

def infer_value(full):
    bits = []
    for m in re.findall(r"(?:€|£|\$|EUR|USD|GBP)\s?[\d,\.]+(?:\s?euros?)?"
                        r"|[\d,\.]+\s?euros?", full, re.I):
        bits.append(m.strip())
    perks = {
        "monthly stipend": r"monthly (?:payment|stipend|allowance)|stipend",
        "tuition": r"tuition",
        "travel allowance": r"travel allowance|airfare|air ticket|flight",
        "health insurance": r"health.{0,20}insurance|insurance",
        "accommodation": r"accommodation|housing",
        "living allowance": r"living (?:allowance|expenses|costs)",
    }
    for label, pat in perks.items():
        if re.search(pat, full, re.I):
            bits.append(label)
    seen, out = set(), []
    for b in bits:
        k = b.lower()
        if k not in seen:
            seen.add(k); out.append(b)
    return (", ".join(out)[:200]) if out else "N/A"

def infer_eligibility(lis, full):
    elig_kw = re.compile(
        r"degree|bachelor|master|nationals?|citizens?|applicants?|years?.{0,10}experience|"
        r"eligible|must (?:be|have)|open to|developing countr|under \d|graduate", re.I)
    bullets = [li for li in lis if elig_kw.search(li)]
    if bullets:
        return (" • ".join(b.strip(" •-") for b in bullets[:6]))[:400], False
    m = re.search(
        r"(?:open to|available to|eligible|who can apply|applicants? (?:must|should)|"
        r"nationals? of|citizens? of|graduates? (?:from|with))(.{30,300}?)(?:\.\s|$)",
        full, re.I)
    if m:
        return m.group(0).strip()[:400], False
    return "International students; verify country eligibility on the official site.", True

def infer_language(full):
    low = full.lower()
    if re.search(r"\bfrench\b", low):
        return "French/English" if "english" in low else "French"
    if re.search(r"\bgerman\b", low):
        return "German/English" if "english" in low else "German"
    return "English"

# ─── Listing page ─────────────────────────────────────────────────────────────

def extract_listing_entries(soup):
    entries = []
    for tag in soup.select("h2 a[href*='scholars4dev.com'], h3 a[href*='scholars4dev.com']"):
        title = tag.get_text(strip=True)
        url = tag.get("href", "")
        if not title or "/category/" in url:
            continue
        block = tag.find_parent(["div", "article", "section"])
        text = block.get_text(" ", strip=True) if block else ""
        provider = "N/A"
        if block and block.find("em"):
            provider = block.find("em").get_text(strip=True)
        lvl = re.search(r"(Bachelor[s]?|Master[s]?|PhD|Postgraduate|Undergraduate)", text, re.I)
        country = re.search(r"Study in:\s*([^\n\r]+?)(?:\s{2,}|Next|Course|Deadline|$)", text)
        deadline = re.search(r"Deadline:\s*([^\n\r]+?)(?:\s{2,}|Study|$)", text)
        entries.append({
            "title": title, "provider": provider,
            "level": clean_level(lvl.group(0) if lvl else ""),
            "country": clean_country(country.group(1) if country else "N/A"),
            "deadline_raw": deadline.group(1).strip() if deadline else "N/A",
            "source_url": url,
        })
    return entries

# ─── Detail page (orchestrates the inference) ────────────────────────────────

def scrape_detail_page(url, _soup=None):
    soup = _soup or get_page(url)
    if not soup:
        return {"description": "", "eligibility": "", "field_of_study": "",
                "language_req": "English", "apply_url": url, "funding_type": "N/A",
                "value": "N/A", "needs_review": "yes"}
    paras, lis, full = extract_body(soup)
    description = build_description(paras, lis, full)
    field, f_weak = infer_field_of_study(full)
    funding, fund_weak = infer_funding(full)
    value = infer_value(full)
    eligibility, e_weak = infer_eligibility(lis, full)
    language = infer_language(full)
    apply_url = url
    a = soup.find("a", string=re.compile(r"apply|official website|official link", re.I))
    if a and a.get("href"):
        apply_url = a["href"]
    needs_review = "yes" if (len(description) < 60 or f_weak or fund_weak or e_weak) else "no"
    return {"description": description, "eligibility": eligibility,
            "field_of_study": field, "language_req": language, "apply_url": apply_url,
            "funding_type": funding, "value": value, "needs_review": needs_review}

# ─── ID + existing data ───────────────────────────────────────────────────────

def generate_id(existing_ids):
    nums = [int(m.group(1)) for sid in existing_ids
            if (m := re.match(r"SCH-(\d+)", str(sid)))]
    return f"SCH-{(max(nums)+1) if nums else 1:03d}"

def load_existing_csv(path):
    try:
        df = pd.read_csv(path)
        print(f"Loaded {len(df)} existing scholarships from {path}")
        return df, set(df["source_url"].dropna().tolist())
    except FileNotFoundError:
        print(f"No existing file at {path} — creating new.")
        return pd.DataFrame(), set()

# ─── Main ─────────────────────────────────────────────────────────────────────

<<<<<<< HEAD
def run_scraper(pages=3, output_file=" data/raw/Scholarships.csv"):
=======
def run_scraper(pages=3, output_file="data/raw/Scholarships.csv"):
>>>>>>> kofi-fork
    print("=" * 60)
    print("  FirstStep — scholars4dev Scraper v3 | Collector:", COLLECTOR_NAME)
    print("=" * 60)
    existing_df, existing_urls = load_existing_csv(output_file)
    new_records, today = [], date.today().isoformat()
    for page in range(1, pages + 1):
        page_url = BASE_URL if page == 1 else f"{BASE_URL}page/{page}/"
        print(f"\n[Page {page}/{pages}] {page_url}")
        soup = get_page(page_url)
        if not soup:
            continue
        entries = extract_listing_entries(soup)
        print(f"  {len(entries)} entries found.")
        for i, e in enumerate(entries):
            if e["source_url"] in existing_urls:
                print(f"  [{i+1}] SKIP (exists): {e['title'][:50]}")
                continue
            print(f"  [{i+1}] Scraping: {e['title'][:50]}...")
            d = scrape_detail_page(e["source_url"])
            time.sleep(DELAY)
            all_ids = (list(existing_df["id"]) if not existing_df.empty else []) \
                      + [r["id"] for r in new_records]
            new_records.append({
                "id": generate_id(all_ids), "name": e["title"],
                "provider": e["provider"], "country": e["country"], "level": e["level"],
                "field_of_study": d["field_of_study"], "min_gpa": "Good academic standing",
                "funding_type": d["funding_type"], "value": d["value"],
                "deadline": e["deadline_raw"], "eligibility": d["eligibility"],
                "language_req": d["language_req"], "description": d["description"],
                "apply_url": d["apply_url"], "source_url": e["source_url"],
                "source_type": "Official", "collected_by": COLLECTOR_NAME,
                "date_added": today, "needs_review": d["needs_review"],
            })
            existing_urls.add(e["source_url"])
        time.sleep(DELAY)
    if not new_records:
        print("\nNo new scholarships found. CSV unchanged.")
        return
    new_df = pd.DataFrame(new_records)
    combined = pd.concat([existing_df, new_df], ignore_index=True) \
        if not existing_df.empty else new_df
    cols = [c for c in SCHEMA if c in combined.columns] + \
           (["needs_review"] if "needs_review" in combined.columns else [])
    combined[cols].to_csv(output_file, index=False)
    review = (new_df["needs_review"] == "yes").sum()
    print("\n" + "=" * 60)
    print(f"  Added {len(new_records)}. Total: {len(combined)}. {review} need review.")
    print(f"  Saved to: {output_file}")
    print("=" * 60)

# ─── Offline parser self-test (real scholars4dev DAAD text) ──────────────────

def test_parsers():
    real = (
        "The German Academic Exchange Service (DAAD) scholarships offer foreign "
        "graduates from development and newly industrialized countries from all "
        "disciplines and with at least two years' professional experience the chance "
        "to take a postgraduate or Master's degree at a state or state-recognized "
        "German university. Masters or PhD courses in Economic Sciences/Business "
        "Administration/Political Economics; Development Cooperation; Engineering and "
        "Related Sciences; Mathematics; Regional and Urban Planning; Agricultural and "
        "Forest Sciences; Natural and Environmental Sciences; Medicine and Public "
        "Health; Social Sciences, Education and Law; and Media Studies. The "
        "scholarships include monthly payments of 750 euros for graduates or 1,000 "
        "euros for doctoral candidates; payments towards health, accident and personal "
        "liability insurance cover; and travel allowance."
    )
    lis = [
        "Is currently working either for a public authority or a state or private company in a developing country",
        "Holds a Bachelor's degree (normally four years) in a related subject",
        "Has completed an academic degree with far above average results and at least two years of related professional experience",
    ]
    field, _ = infer_field_of_study(real)
    funding, _ = infer_funding(real)
    value = infer_value(real)
    elig, _ = infer_eligibility(lis, real)
    print("field_of_study :", field)
    print("funding_type   :", funding)
    print("value          :", value)
    print("eligibility    :", elig[:160], "...")
    print("description len:", len(build_description([real], lis, real)))
    assert funding == "Fully Funded"
    assert "engineering" in field.lower() or "economic" in field.lower()
    assert value != "N/A"
    assert "bachelor" in elig.lower()
    print("\nPARSER SELF-TEST PASSED — fields extract correctly from real page text.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scrape scholars4dev (v3)")
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--output", type=str, default="data/raw/Scholarships.csv")
    ap.add_argument("--selftest", action="store_true", help="run offline parser tests")
    args = ap.parse_args()
    if args.selftest:
        test_parsers()
    else:
        run_scraper(pages=args.pages, output_file=args.output)
