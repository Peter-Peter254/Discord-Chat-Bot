import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import urllib.parse

BASE_URL = "https://docs.railway.app"
OUTPUT_FILE = "railway_docs_full.json"
CACHE_FILE = "visited_urls.json"

# ------------------ HELPERS ------------------

def is_valid_internal_link(href):
    if not href:
        return False
    if href.startswith("#") or "mailto:" in href or "javascript:" in href:
        return False
    if href.startswith("/"):
        return True
    return False

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_cache(cache_set):
    with open(CACHE_FILE, "w") as f:
        json.dump(sorted(cache_set), f)

async def extract_links(page, url):
    await page.goto(url)
    await page.wait_for_load_state("networkidle")
    soup = BeautifulSoup(await page.content(), "html.parser")
    return {
        urllib.parse.urlparse(a["href"]).path.rstrip("/")
        for a in soup.find_all("a", href=True)
        if is_valid_internal_link(a["href"])
    }

async def scrape_page(page, path):
    full_url = BASE_URL + path
    print(f"🔍 Scraping {full_url}")
    await page.goto(full_url)
    await page.wait_for_load_state("networkidle")
    soup = BeautifulSoup(await page.content(), "html.parser")
    main = soup.find("main")

    if not main:
        return None

    title = soup.find("title").text.strip()
    content = main.get_text(separator="\n").strip()

    return {
        "url": full_url,
        "title": title,
        "content": content
    }

# ------------------ MAIN ------------------

async def run():
    scraped_docs = []
    visited = load_cache()
    to_visit = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Step 1: Start with homepage
        print("🌐 Discovering from homepage...")
        to_visit |= await extract_links(page, BASE_URL)

        # Step 2: Depth-1 crawl – visit each and extract more links
        print("🔄 Depth-1 crawling...")
        first_level = to_visit.copy()
        for path in first_level:
            if path in visited:
                continue
            try:
                more_links = await extract_links(page, BASE_URL + path)
                to_visit |= more_links
            except Exception as e:
                print(f"⚠️ Error expanding {path}: {e}")

        print(f"📎 Total unique pages to visit: {len(to_visit)}")

        # Step 3: Scrape everything not in cache
        for path in sorted(to_visit):
            if path in visited:
                continue
            try:
                doc = await scrape_page(page, path)
                if doc:
                    scraped_docs.append(doc)
                    visited.add(path)
            except Exception as e:
                print(f"❌ Failed to scrape {path}: {e}")

        await browser.close()

    # Save scraped docs and updated cache
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(scraped_docs, f, indent=2, ensure_ascii=False)
    save_cache(visited)

    print(f"\n✅ Scraped {len(scraped_docs)} new pages. Cached {len(visited)} total URLs.")

if __name__ == "__main__":
    asyncio.run(run())
