#!/usr/bin/env python3
"""Scrape WHO UMD dictionary via its Search API endpoint - concurrent version."""

import csv
import json
import time
import urllib.request
import urllib.parse
import ssl
import sys
import string
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "https://umd.emro.who.int/WHODictionary/Home/Search"
OUTPUT_PATH = "/home/z/my-project/glossary-work/who_umd_terms.csv"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def search_prefix(prefix):
    """Search the UMD API for terms matching the given prefix. Returns list of (en, ar, category) tuples."""
    body = "targetLang%5B%5D=eng&targetLang%5B%5D=ara&sourceLanguage=eng&entry={}&SearchCheck=eng_Starts".format(
        urllib.parse.quote(prefix)
    )
    req = urllib.request.Request(API_URL, data=body.encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return prefix, []
    
    if not result or not result.get("TBSearchResultListALL"):
        return prefix, []
    
    items = result["TBSearchResultListALL"]
    pairs = []
    i = 0
    while i < len(items):
        if items[i].get("Language") == "eng":
            en = items[i].get("Entry", "").strip()
            cat = ""
            md = items[i].get("MetaData")
            if md and isinstance(md, dict):
                cat = md.get("Subfield", "")
            
            ar = ""
            if i + 1 < len(items) and items[i + 1].get("Language") == "ara":
                raw = items[i + 1].get("Entry", "").strip()
                ar = raw.split("|", 1)[1].strip() if "|" in raw else raw
                if not cat:
                    md2 = items[i + 1].get("MetaData")
                    if md2 and isinstance(md2, dict):
                        cat = md2.get("Subfield", "")
                i += 2
            else:
                i += 1
            
            if ar:
                pairs.append((en, ar, cat))
        else:
            i += 1
    
    return prefix, pairs

def main():
    prefixes = [a + b for a in string.ascii_lowercase for b in string.ascii_lowercase]
    print(f"Searching {len(prefixes)} two-letter prefixes with 10 concurrent workers...")
    print(f"Target: 5000+ unique EN-AR pairs")
    sys.stdout.flush()
    
    all_pairs = OrderedDict()
    t0 = time.time()
    done = 0
    
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(search_prefix, p): p for p in prefixes}
        for fut in as_completed(futures):
            prefix, pairs = fut.result()
            done += 1
            for en, ar, cat in pairs:
                key = (en, ar)
                if key not in all_pairs:
                    all_pairs[key] = {"en": en, "ar": ar, "category": cat}
            
            if done % 50 == 0:
                elapsed = time.time() - t0
                print(f"  [{done}/{len(prefixes)}] {len(all_pairs)} pairs | {elapsed:.0f}s elapsed")
                sys.stdout.flush()
    
    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"Total unique EN-AR pairs: {len(all_pairs)}")
    
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["en", "ar", "category"])
        w.writeheader()
        for p in all_pairs.values():
            w.writerow(p)
    
    print(f"Saved to: {OUTPUT_PATH}")
    
    cats = {}
    for p in all_pairs.values():
        c = p["category"] or "Unknown"
        cats[c] = cats.get(c, 0) + 1
    print(f"\nTop 15 categories:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1])[:15]:
        print(f"  {c}: {n}")

if __name__ == "__main__":
    main()