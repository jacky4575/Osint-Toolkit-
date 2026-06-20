#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║         SOURCING ENGINE — hunter.py v1.0             ║
║   Meesho Supplier Scraper | Built for Termux         ║
╚══════════════════════════════════════════════════════╝

SETUP (run once in Termux):
    pkg install python
    pip install requests beautifulsoup4

RUN:
    python hunter.py
    python hunter.py --keyword "cargo pants" --max 10
    python hunter.py --file keywords.txt
"""

import sys
import time
import json
import csv
import random
import argparse
import os
from datetime import datetime
from urllib.parse import quote_plus, urljoin

# ── Dependency check ─────────────────────────────────
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("\n[!] Missing packages. Run:")
    print("    pip install requests beautifulsoup4\n")
    sys.exit(1)

# ── Config ────────────────────────────────────────────
BASE_URL = "https://www.meesho.com"

HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.meesho.com/",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.meesho.com/",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.meesho.com/",
        "Connection": "keep-alive",
    },
]

# Filter thresholds (adjust as needed)
MIN_RATING   = 4.2
MIN_REVIEWS  = 500
MAX_PRICE    = 600
SLEEP_MIN    = 10   # seconds between requests (anti-ban)
SLEEP_MAX    = 20

COLORS = {
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "red":    "\033[91m",
    "cyan":   "\033[96m",
    "white":  "\033[97m",
    "dim":    "\033[2m",
    "reset":  "\033[0m",
    "bold":   "\033[1m",
}

def c(text, color):
    return f"{COLORS.get(color,'')}{text}{COLORS['reset']}"

def banner():
    print(c("""
╔══════════════════════════════════════════════════════╗
║      ⚡  SOURCING ENGINE — hunter.py v1.0            ║
║         Meesho Supplier Scraper for Termux           ║
╚══════════════════════════════════════════════════════╝""", "green"))
    print(c(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", "dim"))

def log(msg, level="ok"):
    icons = {"ok": c("✓", "green"), "info": c("→", "cyan"),
             "warn": c("!", "yellow"), "error": c("✗", "red")}
    ts = c(f"[{datetime.now().strftime('%H:%M:%S')}]", "dim")
    print(f"  {ts} {icons.get(level,'·')} {msg}")

# ── Core Scraper ──────────────────────────────────────

def get_headers():
    return random.choice(HEADERS_POOL)

def build_search_url(keyword, page=1):
    encoded = quote_plus(keyword)
    return f"{BASE_URL}/search?q={encoded}&page={page}"

def parse_price(raw):
    """Extract integer price from strings like '₹349' or 'Rs. 349'"""
    try:
        cleaned = ''.join(ch for ch in raw if ch.isdigit() or ch == '.')
        return float(cleaned) if cleaned else None
    except Exception:
        return None

def parse_rating(raw):
    """Extract float rating from strings like '4.5 ★' or '4.5'"""
    try:
        cleaned = raw.strip().split()[0]
        return float(cleaned)
    except Exception:
        return None

def parse_reviews(raw):
    """Extract review count from strings like '1.2k reviews' or '1200'"""
    try:
        r = raw.lower().replace(',', '').replace('reviews', '').replace('ratings', '').strip()
        if 'k' in r:
            return int(float(r.replace('k', '')) * 1000)
        return int(float(r))
    except Exception:
        return 0

def scrape_meesho_page(keyword, page=1, session=None):
    """
    Scrape one page of Meesho search results.
    Returns list of raw product dicts.
    """
    url = build_search_url(keyword, page)
    log(f"Fetching: {c(url, 'cyan')}", "info")

    try:
        if session is None:
            session = requests.Session()

        resp = session.get(url, headers=get_headers(), timeout=20)

        if resp.status_code == 429:
            log("Rate limited (429). Sleeping 60s...", "warn")
            time.sleep(60)
            return []

        if resp.status_code != 200:
            log(f"HTTP {resp.status_code} for {url}", "error")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        products = []

        # ── Strategy 1: JSON-LD / __NEXT_DATA__ (most reliable) ──
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if script_tag:
            try:
                data = json.loads(script_tag.string)
                # Navigate the Next.js page props
                page_props = (data.get("props", {})
                                  .get("pageProps", {})
                                  .get("data", {}))

                # Try common keys where Meesho embeds product lists
                product_lists = (
                    page_props.get("products") or
                    page_props.get("catalogList") or
                    page_props.get("searchData", {}).get("catalog_list_data") or
                    []
                )

                for item in product_lists:
                    try:
                        name = (item.get("name") or
                                item.get("product_name") or
                                item.get("catalogName", ""))
                        price_raw = (item.get("price") or
                                     item.get("mrp") or
                                     item.get("finalPrice") or "")
                        rating_raw = str(item.get("rating", "") or
                                         item.get("average_rating", ""))
                        reviews_raw = str(item.get("ratingCount") or
                                          item.get("rating_count") or
                                          item.get("total_ratings", "0"))
                        slug = (item.get("slug") or
                                item.get("product_url_slug") or "")
                        product_url = f"{BASE_URL}/{slug}" if slug else ""

                        image_url = (item.get("images", [{}])[0].get("url", "") if
                                     isinstance(item.get("images"), list) else
                                     item.get("image_url", ""))

                        products.append({
                            "name": name,
                            "price_raw": str(price_raw),
                            "rating_raw": rating_raw,
                            "reviews_raw": reviews_raw,
                            "product_url": product_url,
                            "image_url": image_url,
                            "source": "json",
                        })
                    except Exception:
                        continue

                if products:
                    log(f"Parsed {len(products)} products from JSON data", "ok")
                    return products

            except (json.JSONDecodeError, KeyError):
                pass  # Fall through to HTML parsing

        # ── Strategy 2: HTML CSS class scraping (fallback) ──
        # Meesho uses dynamic classes; we try common patterns
        selectors_to_try = [
            # Card containers
            ("div", {"class": lambda c: c and "ProductCard" in " ".join(c)}),
            ("div", {"class": lambda c: c and "Card__" in " ".join(c)}),
            ("div", {"data-testid": "product-card"}),
            ("div", {"class": lambda c: c and "product" in " ".join(c).lower()}),
        ]

        cards = []
        for tag, attrs in selectors_to_try:
            cards = soup.find_all(tag, attrs)
            if cards:
                log(f"Found {len(cards)} product cards via HTML selectors", "ok")
                break

        for card in cards[:20]:  # Limit to first 20 per page
            try:
                # Name
                name_el = (card.find("p", {"class": lambda c: c and "name" in " ".join(c).lower()}) or
                           card.find("h3") or card.find("h4") or
                           card.find("p"))
                name = name_el.get_text(strip=True) if name_el else ""

                # Price
                price_el = (card.find("h5") or
                            card.find("span", {"class": lambda c: c and "price" in " ".join(c).lower()}) or
                            card.find("p", {"class": lambda c: c and "price" in " ".join(c).lower()}))
                price_raw = price_el.get_text(strip=True) if price_el else ""

                # Rating
                rating_el = card.find("span", {"class": lambda c: c and "rating" in " ".join(c).lower()})
                rating_raw = rating_el.get_text(strip=True) if rating_el else ""

                # Reviews
                reviews_el = card.find("span", {"class": lambda c: c and ("review" in " ".join(c).lower() or "rating" in " ".join(c).lower())})
                reviews_raw = reviews_el.get_text(strip=True) if reviews_el else "0"

                # Link
                link_el = card.find("a", href=True)
                product_url = urljoin(BASE_URL, link_el["href"]) if link_el else ""

                # Image
                img_el = card.find("img")
                image_url = img_el.get("src", "") if img_el else ""

                if name:
                    products.append({
                        "name": name,
                        "price_raw": price_raw,
                        "rating_raw": rating_raw,
                        "reviews_raw": reviews_raw,
                        "product_url": product_url,
                        "image_url": image_url,
                        "source": "html",
                    })
            except Exception:
                continue

        return products

    except requests.exceptions.ConnectionError:
        log("No internet connection. Check your network.", "error")
        return []
    except requests.exceptions.Timeout:
        log("Request timed out. Retrying is recommended.", "warn")
        return []
    except Exception as e:
        log(f"Unexpected error: {e}", "error")
        return []

# ── Filter & Score ─────────────────────────────────────

def process_products(raw_products, keyword):
    """Parse, filter, and score raw product dicts."""
    leads = []

    for item in raw_products:
        price   = parse_price(item.get("price_raw", ""))
        rating  = parse_rating(item.get("rating_raw", ""))
        reviews = parse_reviews(item.get("reviews_raw", "0"))
        name    = item.get("name", "Unknown Product")
        url     = item.get("product_url", "")
        img     = item.get("image_url", "")

        # Apply filters
        if price is None or price <= 0:
            continue
        if price > MAX_PRICE:
            continue
        if rating is not None and rating < MIN_RATING:
            continue
        if reviews < MIN_REVIEWS:
            continue

        # Score: weighted formula
        score = 0
        if rating:
            score += (rating / 5.0) * 40          # 40 pts for rating
        score += min(reviews / 5000, 1.0) * 30    # 30 pts for review count
        score += max(0, (MAX_PRICE - price) / MAX_PRICE) * 30  # 30 pts cheaper = better

        leads.append({
            "keyword":     keyword,
            "name":        name[:80],
            "price":       int(price),
            "rating":      rating if rating else "N/A",
            "reviews":     reviews,
            "score":       round(score, 1),
            "product_url": url,
            "image_url":   img,
            "scraped_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    # Sort by score descending
    leads.sort(key=lambda x: x["score"], reverse=True)
    return leads

# ── Output ─────────────────────────────────────────────

def print_leads(leads, keyword):
    if not leads:
        log(f"No leads passed filters for: {keyword}", "warn")
        return

    print(c(f"\n  ┌─ TOP LEADS for \"{keyword}\" ({'─'*30}┐", "green"))
    for i, p in enumerate(leads, 1):
        gold = p["score"] >= 75
        tag  = c(" ★ GOLD LEAD", "yellow") if gold else ""
        print(c(f"\n  │  #{i}{tag}", "green"))
        print(f"  │   Name    : {c(p['name'], 'white')}")
        print(f"  │   Price   : {c('₹' + str(p['price']), 'cyan')}")
        print(f"  │   Rating  : {c(str(p['rating']) + ' ⭐', 'yellow')}")
        print(f"  │   Reviews : {c(str(p['reviews']), 'white')}")
        print(f"  │   Score   : {c(str(p['score']) + '/100', 'green')}")
        print(f"  │   Link    : {c(p['product_url'] or 'N/A', 'cyan')}")
    print(c(f"\n  └{'─'*50}┘\n", "green"))

def save_csv(all_leads, filename="sourcing_leads.csv"):
    if not all_leads:
        return
    fieldnames = ["keyword", "name", "price", "rating", "reviews",
                  "score", "product_url", "image_url", "scraped_at"]
    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(all_leads)
    log(f"Saved {len(all_leads)} leads → {c(filename, 'cyan')}", "ok")

def save_json(all_leads, filename="sourcing_leads.json"):
    if not all_leads:
        return
    existing = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.extend(all_leads)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    log(f"Saved {len(all_leads)} leads → {c(filename, 'cyan')}", "ok")

# ── Main Engine ────────────────────────────────────────

def hunt(keywords, max_results=10, pages=2, output_csv=True, output_json=True):
    banner()
    session = requests.Session()
    all_leads = []

    total = len(keywords)
    for idx, keyword in enumerate(keywords, 1):
        print(c(f"\n  ══ [{idx}/{total}] Hunting: \"{keyword}\" ══", "bold"))
        keyword_leads = []

        for page in range(1, pages + 1):
            log(f"Page {page}/{pages}", "info")
            raw = scrape_meesho_page(keyword, page=page, session=session)

            if raw:
                filtered = process_products(raw, keyword)
                log(f"Passed filters: {len(filtered)}/{len(raw)} products", "ok")
                keyword_leads.extend(filtered)
            else:
                log("No products parsed from this page.", "warn")

            # Anti-ban sleep between pages
            if page < pages:
                delay = random.randint(SLEEP_MIN, SLEEP_MAX)
                log(f"Sleeping {delay}s (anti-ban)...", "info")
                time.sleep(delay)

        # Deduplicate by URL within keyword results
        seen_urls = set()
        unique_leads = []
        for lead in keyword_leads:
            url = lead["product_url"]
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_leads.append(lead)
            elif not url:
                unique_leads.append(lead)  # Keep if no URL (from HTML parse)

        top_leads = unique_leads[:max_results]
        print_leads(top_leads, keyword)
        all_leads.extend(top_leads)

        # Sleep between keywords
        if idx < total:
            delay = random.randint(SLEEP_MIN, SLEEP_MAX)
            log(f"Next keyword in {delay}s...", "info")
            time.sleep(delay)

    # Save outputs
    print(c("\n  ══ SAVING RESULTS ══", "bold"))
    if output_csv:
        save_csv(all_leads, "sourcing_leads.csv")
    if output_json:
        save_json(all_leads, "sourcing_leads.json")

    # Summary
    gold = [l for l in all_leads if l["score"] >= 75]
    print(c(f"""
  ╔══════════════════════════════════╗
  ║         HUNT COMPLETE ✓          ║
  ║  Total Leads  : {str(len(all_leads)).ljust(16)}║
  ║  Gold Leads   : {str(len(gold)).ljust(16)}║
  ║  Keywords     : {str(total).ljust(16)}║
  ╚══════════════════════════════════╝
""", "green"))

    return all_leads

# ── CLI Entry Point ────────────────────────────────────

def main():
    # Must declare global before any use of these names in this function
    global MIN_RATING, MIN_REVIEWS, MAX_PRICE

    parser = argparse.ArgumentParser(
        description="Meesho Supplier Scraper — Sourcing Engine hunter.py",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python hunter.py
  python hunter.py --keyword "cargo pants"
  python hunter.py --keyword "oversized shirt" --max 5 --pages 3
  python hunter.py --file keywords.txt
  python hunter.py --min-rating 4.5 --min-reviews 1000 --max-price 500
        """
    )
    parser.add_argument("--keyword", "-k", type=str,
                        help="Single keyword to search")
    parser.add_argument("--file", "-f", type=str,
                        help="Text file with one keyword per line")
    parser.add_argument("--max", "-m", type=int, default=10,
                        help="Max leads per keyword (default: 10)")
    parser.add_argument("--pages", "-p", type=int, default=2,
                        help="Pages to scrape per keyword (default: 2)")
    parser.add_argument("--min-rating", type=float, default=MIN_RATING,
                        help=f"Minimum rating filter (default: {MIN_RATING})")
    parser.add_argument("--min-reviews", type=int, default=MIN_REVIEWS,
                        help=f"Minimum reviews filter (default: {MIN_REVIEWS})")
    parser.add_argument("--max-price", type=int, default=MAX_PRICE,
                        help=f"Maximum price filter in ₹ (default: {MAX_PRICE})")
    parser.add_argument("--no-csv", action="store_true",
                        help="Skip CSV output")
    parser.add_argument("--no-json", action="store_true",
                        help="Skip JSON output")

    args = parser.parse_args()

    # Apply CLI overrides to filters
    MIN_RATING  = args.min_rating
    MIN_REVIEWS = args.min_reviews
    MAX_PRICE   = args.max_price

    # Build keyword list
    keywords = []

    if args.keyword:
        keywords = [args.keyword.strip()]
    elif args.file:
        if not os.path.exists(args.file):
            print(c(f"[!] File not found: {args.file}", "red"))
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]
    else:
        # Default trending keywords (from Sourcing Engine Phase 1 output)
        keywords = [
            "oversized cargo pants",
            "cottagecore floral midi dress",
            "y2k crop jacket",
            "baggy linen coord set",
        ]
        print(c("  [i] No keyword given — using default trending keywords.", "yellow"))
        print(c("      Run with --keyword or --file for custom searches.\n", "dim"))

    if not keywords:
        print(c("[!] No keywords to search.", "red"))
        sys.exit(1)

    hunt(
        keywords=keywords,
        max_results=args.max,
        pages=args.pages,
        output_csv=not args.no_csv,
        output_json=not args.no_json,
    )

if __name__ == "__main__":
    main()
