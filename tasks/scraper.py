"""
tasks/scraper.py — Sample task: simulate scraping product prices from a website.

Replace the simulated steps below with your real logic.
Any print() output is streamed live to the Kanban dashboard.
Exit with sys.exit(1) to mark the card as Error.
"""

import time
import random
import sys

PAGES = 4
PRODUCTS_PER_PAGE = 50

print("[INFO] Starting price scraper", flush=True)
print("[INFO] Target: shop.example.com", flush=True)
time.sleep(0.5)

results = []

for page in range(1, PAGES + 1):
    print(f"[INFO] Fetching page {page}/{PAGES}…", flush=True)
    time.sleep(0.8)  # simulate network request

    # Simulate occasional rate limiting
    if page == 3:
        print("[WARN] Rate limit detected — sleeping 2s", flush=True)
        time.sleep(2)

    # Simulate scraping items
    items_found = PRODUCTS_PER_PAGE + random.randint(-5, 5)
    results.append(items_found)
    print(f"[OK] Page {page}/{PAGES} scraped ({items_found} items)", flush=True)

total = sum(results)
print(f"[DEBUG] Raw counts: {results}", flush=True)
print(f"[OK] Total items collected: {total}", flush=True)

# Simulate saving to a file or database
print("[INFO] Saving results to prices.json…", flush=True)
time.sleep(0.4)
print("[OK] prices.json written successfully", flush=True)

print(f"[OK] Scraper finished — {total} products processed", flush=True)
