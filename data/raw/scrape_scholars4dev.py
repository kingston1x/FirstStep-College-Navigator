"""
scrape_scholars4dev.py
----------------------
FirstStep Project — Phase 2: Data Collection
Role: Emmanuel (Kofi) — Data Collection

Scrapes scholarship listings from scholars4dev.com (African students category)
and appends new records to the existing Scholarships.csv file.

Usage:
    scrape_scholars4dev.py
    scrape_scholars4dev.py --pages 5
    scrape_scholars4dev.py --output my_output.csv
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import argparse
from datetime import date

# ─── Config ───────────────────────────────────────────────────────────────────

BASE_URL = "https://www.scholars4dev.com/category/target-group/africans-scholarships/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
DELAY_BETWEEN_REQUESTS = 2   # seconds — be polite to the server
COLLECTOR_NAME = "Emmanuel"  # your name for the collected_by column

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_page(url):
    """Fetch a page and return a BeautifulSoup object, or None on failure."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [ERROR] Failed to fetch {url}: {e}")
        return None


def extract_listing_entries(soup):
    """
    Extract scholarship entries from a listing page.
    Each entry has a title link, provider (em tag), level, country, and deadline.
    Returns a list of dicts with basic info + the detail URL.
    """
    entries = []

    # scholars4dev uses <h2> or <h3> tags with anchor links for titles
    # Try both selectors
    title_tags = soup.select("h2 a[href*='scholars4dev.com'], h3 a[href*='scholars4dev.com']")

    for tag in title_tags:
        title = tag.get_text(strip=True)
        url = tag["href"]

        # Walk up to find the containing block
        block = tag.find_parent(["div", "article", "section"])
        if not block:
            continue

        text = block.get_text(" ", strip=True)

        # Provider — usually in <em> near the title
        provider_tag = block.find("em")
        provider = provider_tag.get_text(strip=True) if provider_tag else "N/A"

        # Study level
        level_match = re.search(
            r"(Bachelor[s]?|Master[s]?|PhD|Postgraduate|Undergraduate|Any)[^\n,]{0,30}Degree",
            text, re.IGNORECASE
        )
        level = level_match.group(0).strip() if level_match else "Any"

        # Country
        country_match = re.search(r"Study in:\s*([^\n\r]+?)(?:\s{2,}|Next|Course|$)", text)
        country = country_match.group(1).strip() if country_match else "N/A"

        # Deadline (raw string from listing — will be kept as-is)
        deadline_match = re.search(r"Deadline:\s*([^\n\r]+?)(?:\s{2,}|Study|$)", text)
        deadline_raw = deadline_match.group(1).strip() if deadline_match else "N/A"

        entries.append({
            "title": title,
            "provider": provider,
            "level": level,
            "country": country,
            "deadline_raw": deadline_raw,
            "source_url": url,
        })

    return entries


def scrape_detail_page(url):
    """
    Visit an individual scholarship page to pull richer fields:
    - description, eligibility, field_of_study, language_req, apply_url
    Returns a dict of extra fields (all default to "N/A" on failure).
    """
    defaults = {
        "description": "N/A",
        "eligibility": "N/A",
        "field_of_study": "N/A",
        "language_req": "N/A",
        "apply_url": url,
        "funding_type": "N/A",
        "value": "N/A",
    }

    soup = get_page(url)
    if not soup:
        return defaults

    # Main content area
    content_div = soup.select_one(".entry-content, .post-content, main article")
    if not content_div:
        return defaults

    text = content_div.get_text(" ", strip=True)

    # Description — first meaningful paragraph
    paragraphs = [p.get_text(strip=True) for p in content_div.find_all("p") if len(p.get_text(strip=True)) > 40]
    description = paragraphs[0] if paragraphs else text[:200]

    # Eligibility — look for common keywords
    elig_match = re.search(
        r"(?:Eligibility|Open to|Available to|Who can apply)[:\s]*(.{30,300}?)(?:\n|\.|;|$)",
        text, re.IGNORECASE
    )
    eligibility = elig_match.group(1).strip() if elig_match else "International students eligible"

    # Fields of study
    field_match = re.search(
        r"(?:field[s]? of study|subject[s]?|discipline[s]?|program[s]?)[:\s]*(.{10,200}?)(?:\n|$)",
        text, re.IGNORECASE
    )
    field_of_study = field_match.group(1).strip() if field_match else "All fields"

    # Language requirement
    lang_match = re.search(
        r"(?:language|IELTS|TOEFL|English|French|German)[^.]{0,100}(?:required|proficiency|test)[^.]{0,50}",
        text, re.IGNORECASE
    )
    language_req = lang_match.group(0).strip() if lang_match else "English"

    # Apply URL — find "Apply" or "Apply Now" link
    apply_link = content_div.find("a", string=re.compile(r"apply|application", re.IGNORECASE))
    apply_url = apply_link["href"] if apply_link and apply_link.get("href") else url

    # Funding type + value
    funding_type = "N/A"
    value = "N/A"
    if re.search(r"full[ly][\s-]fund", text, re.IGNORECASE):
        funding_type = "Fully funded"
        # Try to extract what's covered
        value_match = re.search(
            r"(?:cover[s]?|include[s]?|compris)[:\s]*(.{20,200}?)(?:\n|$)",
            text, re.IGNORECASE
        )
        value = value_match.group(1).strip() if value_match else "Full funding"
    elif re.search(r"partial|tuition only|partial fund", text, re.IGNORECASE):
        funding_type = "Partially funded"
        value = "Partial funding"

    return {
        "description": description[:300],
        "eligibility": eligibility[:250],
        "field_of_study": field_of_study[:200],
        "language_req": language_req[:100],
        "apply_url": apply_url,
        "funding_type": funding_type,
        "value": value[:200],
    }


def generate_id(existing_ids):
    """Generate the next SCH-XXX ID based on existing ones."""
    nums = []
    for sid in existing_ids:
        match = re.match(r"SCH-(\d+)", str(sid))
        if match:
            nums.append(int(match.group(1)))
    next_num = (max(nums) + 1) if nums else 7
    return f"SCH-{next_num:03d}"


def load_existing_csv(filepath):
    """Load existing CSV, return DataFrame and set of existing source_urls."""
    try:
        df = pd.read_csv(filepath)
        existing_urls = set(df["source_url"].dropna().tolist())
        print(f"Loaded {len(df)} existing scholarships from {filepath}")
        return df, existing_urls
    except FileNotFoundError:
        print(f"No existing file at {filepath} — will create a new one.")
        return pd.DataFrame(), set()


# ─── Main Scraper ─────────────────────────────────────────────────────────────

def run_scraper(pages=3, output_file="Scholarships.csv"):
    print("=" * 60)
    print("  FirstStep — scholars4dev Scholarship Scraper")
    print("  Phase 2: Data Collection | Collector:", COLLECTOR_NAME)
    print("=" * 60)

    existing_df, existing_urls = load_existing_csv(output_file)
    new_records = []
    today = date.today().isoformat()

    for page_num in range(1, pages + 1):
        # Build paginated URL
        if page_num == 1:
            page_url = BASE_URL
        else:
            page_url = f"{BASE_URL}page/{page_num}/"

        print(f"\n[Page {page_num}/{pages}] Fetching: {page_url}")
        soup = get_page(page_url)
        if not soup:
            print("  Skipping page — fetch failed.")
            continue

        entries = extract_listing_entries(soup)
        print(f"  Found {len(entries)} entries on this page.")

        for i, entry in enumerate(entries):
            source_url = entry["source_url"]

            # Skip if already in our dataset
            if source_url in existing_urls:
                print(f"  [{i+1}/{len(entries)}] SKIP (already exists): {entry['title'][:60]}")
                continue

            print(f"  [{i+1}/{len(entries)}] Scraping detail: {entry['title'][:55]}...")
            detail = scrape_detail_page(source_url)
            time.sleep(DELAY_BETWEEN_REQUESTS)  # be polite

            # Build full record matching your CSV schema exactly
            all_ids = list(existing_df["id"]) if not existing_df.empty else []
            all_ids += [r["id"] for r in new_records]
            new_id = generate_id(all_ids)

            record = {
                "id": new_id,
                "name": entry["title"],
                "provider": entry["provider"],
                "country": entry["country"],
                "level": entry["level"],
                "field_of_study": detail["field_of_study"],
                "min_gpa": "Good academic standing",  # default; update manually if found
                "funding_type": detail["funding_type"],
                "value": detail["value"],
                "deadline": entry["deadline_raw"],
                "eligibility": detail["eligibility"],
                "language_req": detail["language_req"],
                "description": detail["description"],
                "apply_url": detail["apply_url"],
                "source_url": source_url,
                "source_type": "Official",
                "collected_by": COLLECTOR_NAME,
                "date_added": today,
            }

            new_records.append(record)
            existing_urls.add(source_url)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    # ─── Save results ──────────────────────────────────────────────────────────
    if not new_records:
        print("\n⚠️  No new scholarships found. CSV unchanged.")
        return

    new_df = pd.DataFrame(new_records)

    if not existing_df.empty:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_csv(output_file, index=False)

    print("\n" + "=" * 60)
    print(f"✅  Done! Added {len(new_records)} new scholarships.")
    print(f"📄  Total in CSV: {len(combined_df)}")
    print(f"💾  Saved to: {output_file}")
    print("=" * 60)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape scholars4dev for African scholarships")
    parser.add_argument(
        "--pages", type=int, default=3,
        help="Number of listing pages to scrape (default: 3, ~30 scholarships)"
    )
    parser.add_argument(
        "--output", type=str, default="Scholarships.csv",
        help="Output CSV file path (default: Scholarships.csv)"
    )
    args = parser.parse_args()

    run_scraper(pages=args.pages, output_file=args.output)