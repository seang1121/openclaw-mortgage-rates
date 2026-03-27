# 🦞 OpenClaw Mortgage Rate Scanner

> Daily mortgage rate comparisons from **10 lenders** and **2 national benchmarks**, delivered to your Discord automatically via [OpenClaw](https://openclaw.ai). Set it up once, never check a bank website again.

![Lenders](https://img.shields.io/badge/lenders-10-brightgreen)
![Benchmarks](https://img.shields.io/badge/benchmarks-2-blue)
![Schedule](https://img.shields.io/badge/runs-daily-orange)
![OpenClaw](https://img.shields.io/badge/OpenClaw-integration-purple)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What You Get

Every morning, your OpenClaw agent scrapes 10 lender websites using a two-tier approach:

- **Tier 1 — Patchright (headless):** 8 lenders scraped in parallel via stealth Chromium
- **Tier 2 — OpenClaw Browser (real Chrome):** Chase and Rocket Mortgage require a persistent browser session with cookies — the OpenClaw browser profile handles these automatically

All rates are combined, ranked lowest to highest against Freddie Mac and Mortgage News Daily national averages, and posted to your Discord.

```
MORTGAGE RATES — Mar 26, 2026  |  9/9 lenders reporting

30-YEAR FIXED
  Navy Federal CU — 5.375% (6.875% APR)
  Wells Fargo — 5.875% (6.082% APR)
  Citi — 6.125% (6.259% APR)
  Mr. Cooper — 6.250% (6.550% APR)
  Guaranteed Rate — 6.325% (6.639% APR)
  SoFi — 6.351% (5.625% APR)
  US Bank — 6.375% (6.529% APR)
  Truist — 6.375% (6.565% APR)
  Freddie Mac natl avg — 6.380%  (benchmark)
  MND Index — 6.620%  (benchmark)
  Bank of America — 6.625% (6.846% APR)
  Avg: 6.186% | vs yesterday: up 0.086%

15-YEAR FIXED
  Navy Federal CU — 5.375% (6.875% APR)
  US Bank — 5.490% (5.774% APR)
  Truist — 5.600% (5.892% APR)
  Guaranteed Rate — 5.625% (6.096% APR)
  Freddie Mac natl avg — 5.750%  (benchmark)
  Bank of America — 5.750% (6.134% APR)
  Wells Fargo — 5.750% (6.000% APR)
  SoFi — 5.831% (5.990% APR)
  MND Index — 6.620%  (benchmark)
  Avg: 5.632% | vs yesterday: up 0.084%
```

---

## Lenders Tracked

| # | Lender | Type | How |
|---|--------|------|-----|
| 1 | Bank of America | Big 4 Bank | Patchright |
| 2 | Wells Fargo | Big 4 Bank | Patchright |
| 3 | **Chase** | Big 4 Bank | **OpenClaw Browser** |
| 4 | Citi | Big 4 Bank | Patchright |
| 5 | Navy Federal CU | Credit Union | Patchright |
| 6 | SoFi | Online Lender | Patchright |
| 7 | US Bank | National Bank | Patchright |
| 8 | Guaranteed Rate | Online Lender | Patchright |
| 9 | Truist | National Bank | Patchright |
| 10 | Mr. Cooper | Largest Servicer | Patchright |
| 11 | **Rocket Mortgage** | Online Lender | **OpenClaw Browser** |

**Benchmarks:** Freddie Mac PMMS (weekly national average) + Mortgage News Daily (daily index)

---

## 🦞 One-Command Install

```bash
bash <(curl -s https://raw.githubusercontent.com/seang1121/OpenClaw-Mortgage-Interest-Rates-Report/main/install.sh) YOUR_ZIP
```

Replace `YOUR_ZIP` with your ZIP code (e.g. `90210`). That's it. Two minutes and you're done.

### What the installer does:

1. Checks that OpenClaw gateway is running
2. **Checks for OpenClaw browser** — if not set up, walks you through `openclaw browser setup` (required for Chase + Rocket Mortgage)
3. Clones this repo into `~/.openclaw/workspace/mortgage-rates/`
4. Creates a Python venv and installs patchright + stealth Chromium
5. Sets your ZIP code
6. Registers a daily 8:00 AM EST cron job in OpenClaw
7. Report gets delivered to your Discord channel

---

## Manual Setup

```bash
# Clone into your OpenClaw workspace
git clone https://github.com/seang1121/OpenClaw-Mortgage-Interest-Rates-Report.git ~/.openclaw/workspace/mortgage-rates
cd ~/.openclaw/workspace/mortgage-rates

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m patchright install chromium

# Set your ZIP code
echo '{"zip_code": "YOUR_ZIP"}' > config.json

# Test it
python3 mortgage_rate_report.py
```

Then register the cron job in `~/.openclaw/cron/jobs.json` (see [Cron Setup](#cron-job-setup) below).

---

## Customize

### Change your ZIP code

```bash
echo '{"zip_code": "10001"}' > ~/.openclaw/workspace/mortgage-rates/config.json
```

### Change the schedule

Find `daily-mortgage-rates` in `~/.openclaw/cron/jobs.json` and edit the `expr` field:

| Schedule | Cron Expression |
|----------|----------------|
| Daily at 8 AM | `0 8 * * *` |
| Weekdays only at 8 AM | `0 8 * * 1-5` |
| Twice daily (8 AM + 5 PM) | `0 8,17 * * *` |
| Every 6 hours | `0 */6 * * *` |

### Change the delivery channel

In `jobs.json`, update the `delivery.to` field with your Discord channel ID.

---

## Cron Job Setup

Add this to your `~/.openclaw/cron/jobs.json` in the `jobs` array:

```json
{
  "id": "mortgage-rates-001",
  "name": "daily-mortgage-rates",
  "enabled": true,
  "schedule": {
    "kind": "cron",
    "expr": "0 8 * * *",
    "tz": "America/New_York"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "MORTGAGE RATE REPORT: Run this command:\ncd ~/.openclaw/workspace/mortgage-rates && source venv/bin/activate && python3 mortgage_rate_report.py 2>&1\n\nRead the full output and reply with it formatted for Discord.",
    "timeoutSeconds": 300
  },
  "delivery": {
    "mode": "announce",
    "channel": "discord",
    "to": "YOUR_CHANNEL_ID"
  }
}
```

---

## How It Works

```
         OpenClaw Cron (8:00 AM EST)
                    |
         +---------+---------+
         |                   |
   TIER 1: Script      TIER 2: OpenClaw Browser
   mortgage_rate_report.py   (real Chrome profile)
         |                   |
   asyncio.gather()    Chase — ZIP gate, click
   batches of 4        "See rates", extract
         |             full product menu
   +-----+-----+            |
   |     |     |       Rocket Mortgage —
patchright  patchright urllib   wait for JS render,
(stealth) (stealth) (API)   extract all products
   |     |     |            |
 BofA   SoFi  Freddie      |
 WF     USB   Mac          |
 Citi   Guar  MND          |
 Navy   Truist              |
 Fed    Cooper              |
   |     |     |            |
   +-----+-----+-----+-----+
                |
     Combine all rates
     Rank lowest to highest
     Calculate day-over-day
                |
     Deliver to Discord
```

**Tier 1 — Patchright (8 lenders + 2 benchmarks):** Stealth-patched headless Chromium that bypasses bot detection, Cloudflare, and JS-rendered SPAs. Runs in parallel batches of 4. Freddie Mac and MND are fetched via direct API (no browser).

**Tier 2 — OpenClaw Browser (Chase + Rocket):** These lenders require a persistent Chrome session with cookies and a real browser profile. The OpenClaw browser (`~/.openclaw/browser/openclaw/`) handles this — it opens the page, fills the ZIP code, clicks through, and extracts the full product menu (30yr, 15yr, FHA, Jumbo, VA, ARM).

90 days of rate history stored locally at `data/mortgage_rates_history.json` for trend tracking.

---

## Requirements

- [OpenClaw](https://openclaw.ai) running with gateway active
- **OpenClaw Browser** set up (`openclaw browser setup`) — required for Chase + Rocket Mortgage
- Python 3.10+
- ~200MB disk space (Chromium browser)
- Internet access

> **Why do I need the OpenClaw browser?** Chase and Rocket Mortgage use aggressive anti-bot protection that blocks even stealth headless browsers. They need a real Chrome profile with persistent cookies and session state. The OpenClaw browser provides this — it's a managed Chrome instance that your agent can control like a real user.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 0 lenders reporting | Run `python3 mortgage_rate_report.py --headed` to see what the browser loads. Some VPNs/corporate networks block stealth browsers. |
| Cron job not firing | Check `~/.openclaw/cron/jobs.json` — is the job `enabled: true`? Is the gateway running (`pm2 status`)? |
| Rates look wrong | Bank websites change layouts. Open an issue or PR. |
| patchright install fails | Make sure you ran `python -m patchright install chromium`. On corporate networks, set `HTTPS_PROXY`. |

---

## Contributing

- Found a working URL for a new lender? **Open an issue.**
- Built a custom schedule or integration? **Share it.**
- Lender broke? **Submit a PR** with the updated regex or URL.

---

## License

MIT
