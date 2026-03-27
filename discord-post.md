# Discord Post — Copy everything below the line into your channel

---

🦞 **Mortgage Rate Scanner — OpenClaw Integration**

Wake up to the best mortgage rates in the country, every morning, in your Discord. No tabs. No bank websites. No BS.

Your OpenClaw scrapes **11 lenders** + **2 national benchmarks** using a two-tier approach:
- **8 lenders** via stealth headless Chromium (patchright) — bypasses Cloudflare and anti-bot
- **Chase + Rocket Mortgage** via the **OpenClaw Browser** — real Chrome session that gets through their aggressive bot detection

Rates ranked lowest to highest. Day-over-day tracking. Chase full product menu (30yr, 15yr, FHA, Jumbo).

**Here's what lands in your Discord every morning:**

📊 **MORTGAGE RATES — Mar 26, 2026** | 11/11 lenders reporting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📊 30-YEAR FIXED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 **Navy Federal CU — 5.375%** (6.875% APR) ← **BEST**
🟢 Wells Fargo — 5.875% (6.082% APR)
🟢 Citi — 6.125% (6.259% APR)
> ─── *Freddie Mac natl avg — 6.380%* (benchmark) ───
🟡 Mr. Cooper — 6.250% (6.550% APR)
🟡 Guaranteed Rate — 6.325% (6.639% APR)
🟡 SoFi — 6.351% (5.625% APR)
🟡 US Bank — 6.375% (6.529% APR)
🟡 Truist — 6.375% (6.565% APR)
> ─── *MND Index — 6.620%* (benchmark) ───
🔴 Bank of America — 6.625% (6.846% APR)
🔴 Chase — 6.490% (6.578% APR)
🔴 **Rocket Mortgage — 6.750%** (6.890% APR) ← **WORST**
📈 Avg: 6.186% | vs yesterday: ▲ 0.086%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📊 15-YEAR FIXED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 **Navy Federal CU — 5.375%** (6.875% APR) ← **BEST**
🟢 US Bank — 5.490% (5.774% APR)
🟢 Truist — 5.600% (5.892% APR)
🟡 *...middle of pack...*
🔴 **Rocket Mortgage — 6.125%** (6.340% APR) ← **WORST**
📈 Avg: 5.632% | vs yesterday: ▲ 0.084%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📊 CHASE FULL MENU (ZIP YOUR_ZIP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▸ 30yr Fixed — 6.490% (6.578% APR)
▸ 15yr Fixed — 5.500% (5.667% APR)
▸ 30yr FHA Fixed — 6.000% (6.780% APR)
▸ 30yr Jumbo Fixed — 5.990% (6.082% APR)
▸ 7/6 Jumbo ARM — 5.375% (5.980% APR)

🟢 = below avg | 🟡 = near avg | 🔴 = above avg — **instantly see who's ripping you off**

**Lenders:** BofA • Wells Fargo • **Chase** • Citi • Navy Federal • SoFi • US Bank • Guaranteed Rate • Truist • Mr. Cooper • **Rocket Mortgage**
**Benchmarks:** Freddie Mac PMMS + Mortgage News Daily

🦞 **One-command install:**
```bash
bash <(curl -s https://raw.githubusercontent.com/seang1121/OpenClaw-Mortgage-Interest-Rates-Report/main/install.sh) YOUR_ZIP
```
Replace `YOUR_ZIP` with your ZIP code. That's it. Takes 2 minutes.

**What happens:**
✅ Checks your OpenClaw browser is set up (walks you through it if not)
✅ Installs the scraper + stealth Chromium into your workspace
✅ Registers a daily 8 AM cron job
✅ Report lands in your Discord every morning

**Customize everything:** ZIP code, schedule (weekdays, twice daily, whatever), delivery channel.

**Requirements:** OpenClaw + OpenClaw Browser (`openclaw browser setup`) + Python 3.10+

> **Why the OpenClaw browser?** Chase and Rocket use aggressive anti-bot that blocks even stealth headless browsers. The OpenClaw browser is a real Chrome profile your agent controls — it gets through where headless can't.

📎 Full docs + source: <https://github.com/seang1121/OpenClaw-Mortgage-Interest-Rates-Report>

---
