"""
mortgage_rate_report.py — Multi-lender mortgage rate comparison

Scrapes 9 lenders via patchright stealth browser + 2 national benchmarks.
Chase and Rocket Mortgage are handled separately via OpenClaw browser (anti-bot).

Lenders (automated):
  Bank of America, Wells Fargo, Citi, Navy Federal CU, SoFi,
  US Bank, Guaranteed Rate, Truist, Mr. Cooper

Benchmarks (no browser):
  Freddie Mac PMMS (CSV API), Mortgage News Daily (urllib)

Usage:
  python3 mortgage_rate_report.py            # run all automated lenders
  python3 mortgage_rate_report.py --zip 90210  # override ZIP code
"""

import argparse
import sys
import asyncio
import json
import os
import re
import ssl
import urllib.request
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
HISTORY_FILE = os.path.join(DATA_DIR, "mortgage_rates_history.json")

ZIP_CODE = None  # Set via config.json or --zip flag
WAIT_MS = 10000
MAX_RETRIES = 3
BATCH_SIZE = 4
WAIT_SCHEDULE = [8000, 12000, 15000]

BENCHMARKS = {"Freddie Mac (natl avg)", "MND Index"}

# Chase and Rocket Mortgage are handled by OpenClaw browser in the cron — not here
BROWSER_SOURCES = [
    ("Bank of America",  "https://promotions.bankofamerica.com/homeloans/homebuying-hub/home-loan-options?subCampCode=41490&dmcode=18099675931"),
    ("Wells Fargo",      "https://www.wellsfargo.com/mortgage/rates/"),
    ("Citi",             "https://www.citi.com/mortgage/purchase-rates"),
    ("Navy Federal CU",  "https://www.navyfederal.org/loans-cards/mortgage/mortgage-rates/"),
    ("SoFi",             "https://www.sofi.com/home-loans/mortgage-rates/"),
    ("US Bank",          "https://www.usbank.com/home-loans/mortgage/mortgage-rates.html"),
    ("Guaranteed Rate",  "https://www.rate.com/mortgage-rates"),
    ("Truist",           "https://www.truist.com/mortgage/current-mortgage-rates"),
    ("Mr. Cooper",       "https://www.mrcooper.com/get-started/rates?internal_ref=rates_home"),
]


# ─── CONFIG ──────────────────────────────────────────────────────────────────

def load_zip_code(cli_zip=None):
    """Resolve ZIP: --zip flag > config.json. No default — user must configure."""
    if cli_zip:
        return cli_zip
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        z = cfg.get("zip_code", "")
        if z and z != "YOUR_ZIP":
            return z
    print("ERROR: No ZIP code configured.")
    print("Set your ZIP in config.json: {\"zip_code\": \"YOUR_ZIP\"}")
    print("Or pass it directly: python3 mortgage_rate_report.py --zip 90210")
    sys.exit(1)


# ─── RATE EXTRACTION ─────────────────────────────────────────────────────────

def extract_rates(text, lender):
    """Extract rate/APR pairs from page text."""
    results = []
    for label, product in [
        (r'30[- ]?[Yy]ear(?:\s*[Ff]ixed)?', "30yr"),
        (r'15[- ]?[Yy]ear(?:\s*[Ff]ixed)?', "15yr"),
        (r'(?:7/6|7/1|5/1)\s*(?:ARM|Adj)', "ARM"),
    ]:
        # Pattern 1: "rate% APR apr%"
        m = re.search(label + r'.*?(\d\.\d{2,3})%.*?(?:APR|apr)[:\s]*(\d\.\d{2,3})%', text, re.DOTALL | re.IGNORECASE)
        if m:
            results.append({"lender": lender, "product": product, "rate": float(m.group(1)), "apr": float(m.group(2))})
            continue

        # Pattern 2: "rate%  apr%" (tab/space separated)
        m = re.search(label + r'[\t\s]+(\d\.\d{2,3})%[\t\s]+(\d\.\d{2,3})%', text, re.IGNORECASE)
        if m:
            results.append({"lender": lender, "product": product, "rate": float(m.group(1)), "apr": float(m.group(2))})
            continue

        # Pattern 3: "is X.XXX% (X.XXX% APR)"
        m = re.search(label + r'.*?is\s+(\d\.\d{2,3})%\s*\((\d\.\d{2,3})%\s*APR\)', text, re.DOTALL | re.IGNORECASE)
        if m:
            results.append({"lender": lender, "product": product, "rate": float(m.group(1)), "apr": float(m.group(2))})
            continue

        # Pattern 4: "Rate X.XXX% APR X.XXX%" (Mr. Cooper style)
        m = re.search(label + r'.*?Rate.*?(\d\.\d{2,3})%.*?APR.*?(\d\.\d{2,3})%', text, re.DOTALL | re.IGNORECASE)
        if m:
            results.append({"lender": lender, "product": product, "rate": float(m.group(1)), "apr": float(m.group(2))})
            continue

        # Pattern 5: rate only, no APR
        m = re.search(label + r'[^\d]*?(\d\.\d{2,3})%', text, re.DOTALL | re.IGNORECASE)
        if m and 3.0 <= float(m.group(1)) <= 12.0:
            results.append({"lender": lender, "product": product, "rate": float(m.group(1)), "apr": None})

    return results


# ─── BENCHMARKS (no browser) ─────────────────────────────────────────────────

def fetch_freddie_mac_csv():
    """Freddie Mac PMMS — national benchmark via free CSV endpoint."""
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            "https://www.freddiemac.com/pmms/docs/PMMS_history.csv",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            lines = r.read().decode().strip().split("\n")
        last = lines[-1].split(",")
        results = []
        if len(last) >= 2 and last[1]:
            results.append({"lender": "Freddie Mac (natl avg)", "product": "30yr", "rate": float(last[1]), "apr": None})
        if len(last) >= 4 and last[3]:
            results.append({"lender": "Freddie Mac (natl avg)", "product": "15yr", "rate": float(last[3]), "apr": None})
        return results
    except Exception:
        return []


def fetch_mnd_urllib():
    """Mortgage News Daily — daily index via plain HTML."""
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            "https://www.mortgagenewsdaily.com/mortgage-rates",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            html = r.read().decode("utf-8", errors="replace")
        text = re.sub(r'<[^>]+>', ' ', html)
        return extract_rates(text, "MND Index")
    except Exception:
        return []


# ─── STEALTH BROWSER SCRAPING ────────────────────────────────────────────────

async def scrape_lender(browser, name, url, wait_ms=None):
    """Scrape a single lender with patchright stealth browser."""
    wait = wait_ms or WAIT_MS
    ctx = None
    try:
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = await ctx.new_page()
        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(wait)

        # Try ZIP input if present
        for sel in ['input[name*="zip" i]', 'input[placeholder*="ZIP" i]', 'input[id*="zip" i]']:
            el = await page.query_selector(sel)
            if el:
                await el.fill(ZIP_CODE)
                await page.wait_for_timeout(500)
                for btn_sel in ['button[type="submit"]', 'button:has-text("Update")', 'button:has-text("Get")', 'button:has-text("View")']:
                    btn = await page.query_selector(btn_sel)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(5000)
                        break
                break

        text = await page.inner_text("body")
        await ctx.close()
        return name, extract_rates(text, name)
    except Exception:
        if ctx:
            try:
                await ctx.close()
            except Exception:
                pass
        return name, []


async def scrape_with_retries(browser, name, url):
    """Retry up to MAX_RETRIES with increasing wait times."""
    for attempt in range(MAX_RETRIES):
        wait = WAIT_SCHEDULE[min(attempt, len(WAIT_SCHEDULE) - 1)]
        result_name, rates = await scrape_lender(browser, name, url, wait_ms=wait)
        if rates:
            if attempt > 0:
                print(f"  {name}: succeeded on attempt {attempt + 1}")
            return result_name, rates
    return name, []


async def scrape_all_browser():
    """Scrape all lenders in batches of 4, retry failures sequentially."""
    from patchright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        final = []
        failed = []

        for batch_start in range(0, len(BROWSER_SOURCES), BATCH_SIZE):
            batch = BROWSER_SOURCES[batch_start:batch_start + BATCH_SIZE]
            print(f"  Batch {batch_start // BATCH_SIZE + 1}: {', '.join(n for n, _ in batch)}")
            tasks = [scrape_lender(browser, name, url) for name, url in batch]
            results = await asyncio.gather(*tasks)

            for (name, rates), (orig_name, orig_url) in zip(results, batch):
                if rates:
                    final.append((name, rates))
                else:
                    failed.append((orig_name, orig_url))

        if failed:
            print(f"  Retrying {len(failed)} failed: {', '.join(n for n, _ in failed)}")
            for name, url in failed:
                result_name, rates = await scrape_with_retries(browser, name, url)
                final.append((result_name, rates))

        await browser.close()
    return final


# ─── HISTORY ─────────────────────────────────────────────────────────────────

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def save_history(history):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ─── REPORT FORMATTING ───────────────────────────────────────────────────────

def format_report(unique, history):
    """Build Discord-ready rate comparison report."""
    last_rates = history[-1].get("rates", {}) if history else {}
    today = datetime.now().strftime("%b %d, %Y")
    reporting = len(set(r["lender"] for r in unique if r["lender"] not in BENCHMARKS))

    lines = [f"📊 **MORTGAGE RATES — {today}**  |  {reporting}/{len(BROWSER_SOURCES)} lenders reporting", ""]

    for product, label in [("30yr", "30-YEAR FIXED"), ("15yr", "15-YEAR FIXED"), ("ARM", "ARM")]:
        product_rates = sorted(
            [r for r in unique if r["product"] == product],
            key=lambda r: r["rate"]
        )
        if not product_rates:
            continue

        lines.append(f"📊 {label}")

        # Find best non-benchmark rate(s)
        non_bench = [r for r in product_rates if r["lender"] not in BENCHMARKS]
        best_rate = non_bench[0]["rate"] if non_bench else None

        for r in product_rates:
            rate_str = f"{r['rate']:.3f}%"
            apr_str = f" ({r['apr']:.3f}% APR)" if r.get("apr") else ""
            is_benchmark = r["lender"] in BENCHMARKS

            if is_benchmark:
                lines.append(f"▸ {r['lender']} — {rate_str}{apr_str}  *(benchmark)*")
            elif r["rate"] == best_rate:
                lines.append(f"🏆 {r['lender']} — **{rate_str}**{apr_str}")
            else:
                lines.append(f"▸ {r['lender']} — {rate_str}{apr_str}")

        # Day-over-day avg
        prev = last_rates.get(product, [])
        if prev and non_bench:
            curr_avg = sum(r["rate"] for r in non_bench) / len(non_bench)
            prev_avg = sum(r["rate"] for r in prev if r["lender"] not in BENCHMARKS) / max(len([r for r in prev if r["lender"] not in BENCHMARKS]), 1)
            diff = curr_avg - prev_avg
            if abs(diff) >= 0.005:
                arrow = "▲" if diff > 0 else "▼"
                lines.append(f"📈 Avg: {curr_avg:.3f}%  |  vs yesterday: {arrow} {abs(diff):.3f}%")
            else:
                lines.append(f"📈 Avg: {curr_avg:.3f}%  |  vs yesterday: unchanged")

        lines.append("")

    return "\n".join(lines)


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-lender mortgage rate comparison")
    parser.add_argument("--zip", type=str, default=None, help="ZIP code override (default: 32224)")
    args = parser.parse_args()

    global ZIP_CODE
    ZIP_CODE = load_zip_code(args.zip)

    print(f"Scraping {len(BROWSER_SOURCES)} lenders + 2 benchmarks (ZIP: {ZIP_CODE})...\n")

    all_rates = []
    successes = []
    failures = []

    # Benchmarks (no browser)
    fm_rates = fetch_freddie_mac_csv()
    if fm_rates:
        all_rates.extend(fm_rates)
        successes.append("Freddie Mac")
    else:
        failures.append("Freddie Mac")

    mnd_rates = fetch_mnd_urllib()
    if mnd_rates:
        all_rates.extend(mnd_rates)
        successes.append("MND")
    else:
        failures.append("MND")

    # Stealth browser scraping
    browser_results = asyncio.run(scrape_all_browser())
    for name, rates in browser_results:
        if rates:
            all_rates.extend(rates)
            successes.append(name)
        else:
            failures.append(name)

    if not all_rates:
        print("No rates fetched from any source.")
        return

    # Deduplicate
    seen = set()
    unique = []
    for r in all_rates:
        key = (r["lender"], r["product"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Load history, format, print
    history = load_history()
    report = format_report(unique, history)
    print(report)

    if failures:
        failed_lenders = [f for f in failures if f not in ("Freddie Mac", "MND")]
        if failed_lenders:
            print(f"⚠️ Failed: {', '.join(failed_lenders)}")

    # Save latest report to file for external analysis
    os.makedirs(DATA_DIR, exist_ok=True)
    report_file = os.path.join(DATA_DIR, "latest_report.txt")
    with open(report_file, "w") as f:
        f.write(report + "\n")
        if failures:
            failed_lenders = [ff for ff in failures if ff not in ("Freddie Mac", "MND")]
            if failed_lenders:
                f.write(f"\n⚠️ Failed: {', '.join(failed_lenders)}\n")

    # Save history
    today_key = datetime.now().strftime("%Y-%m-%d")
    rates_by_product = {}
    for product in ["30yr", "15yr", "ARM"]:
        pr = [r for r in unique if r["product"] == product]
        if pr:
            rates_by_product[product] = [{"lender": r["lender"], "rate": r["rate"], "apr": r.get("apr")} for r in pr]

    if history and history[-1].get("date") == today_key:
        history[-1]["rates"] = rates_by_product
    else:
        history.append({"date": today_key, "rates": rates_by_product})

    history = history[-90:]
    save_history(history)


if __name__ == "__main__":
    main()
