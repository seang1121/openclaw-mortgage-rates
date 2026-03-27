#!/usr/bin/env bash
# 🦞 OpenClaw Mortgage Rate Integration — One-command setup
# Usage: bash install.sh [ZIP_CODE]
#
# What this does:
#   1. Checks OpenClaw gateway + browser are set up
#   2. Clones the scraper into your OpenClaw workspace
#   3. Installs patchright + stealth Chromium
#   4. Sets your ZIP code
#   5. Registers a daily cron job in OpenClaw (with browser steps for Chase)
#
# After install, you get daily mortgage rates delivered to your Discord.

set -e

REPO_URL="https://github.com/seang1121/OpenClaw-Mortgage-Interest-Rates-Report.git"
INSTALL_DIR="$HOME/.openclaw/workspace/mortgage-rates"
CRON_FILE="$HOME/.openclaw/cron/jobs.json"
BROWSER_DIR="$HOME/.openclaw/browser/openclaw"
ZIP="${1:-}"

echo ""
echo "  🦞 Mortgage Rate Scanner — OpenClaw Integration"
echo "  ================================================"
echo ""

# Step 1: Check OpenClaw is installed
if ! command -v openclaw &>/dev/null; then
    echo "  ❌ ERROR: openclaw CLI not found."
    echo "  Install OpenClaw first: https://openclaw.ai"
    exit 1
fi

echo "  [1/6] Checking OpenClaw gateway..."
if curl -s --max-time 3 http://127.0.0.1:18789 >/dev/null 2>&1; then
    echo "         ✅ Gateway is running."
else
    echo "  ⚠️  WARNING: Gateway not responding on port 18789."
    echo "           Make sure OpenClaw is running: pm2 start openclaw"
    echo ""
fi

# Step 2: Check OpenClaw browser setup
echo "  [2/6] Checking OpenClaw browser..."
if [ -d "$BROWSER_DIR" ]; then
    echo "         ✅ OpenClaw browser profile found."
else
    echo ""
    echo "  ⚠️  OpenClaw browser profile not found at:"
    echo "     $BROWSER_DIR"
    echo ""
    echo "  The OpenClaw browser is REQUIRED for Chase and Rocket Mortgage."
    echo "  These lenders need a persistent browser session with cookies"
    echo "  and a real Chrome profile — patchright alone can't get through."
    echo ""
    echo "  To set up the OpenClaw browser:"
    echo ""
    echo "    1. Run: openclaw browser setup"
    echo "    2. This creates a Chrome profile at ~/.openclaw/browser/openclaw/"
    echo "    3. The cron job will use this profile to open Chase/Rocket pages"
    echo "       and extract rates that require a real browser session."
    echo ""
    read -p "  Do you want to set up the OpenClaw browser now? (y/n): " SETUP_BROWSER
    if [ "$SETUP_BROWSER" = "y" ] || [ "$SETUP_BROWSER" = "Y" ]; then
        echo "  Setting up OpenClaw browser..."
        openclaw browser setup 2>&1 || {
            echo ""
            echo "  ❌ Browser setup failed. You can retry later with:"
            echo "     openclaw browser setup"
            echo ""
            echo "  Continuing without browser — Chase and Rocket rates"
            echo "  will be missing from your report until browser is set up."
            echo ""
        }
    else
        echo ""
        echo "  ⚠️  Skipping browser setup."
        echo "  Chase and Rocket Mortgage rates will NOT be included"
        echo "  until you run: openclaw browser setup"
        echo ""
    fi
fi

# Step 3: Clone or update the scraper
echo "  [3/6] Installing scraper..."
if [ -d "$INSTALL_DIR" ]; then
    echo "         Updating existing install..."
    cd "$INSTALL_DIR" && git pull --quiet
else
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
fi

# Step 4: Install dependencies
echo "  [4/6] Installing dependencies..."
cd "$INSTALL_DIR"
python3 -m venv venv 2>/dev/null || python -m venv venv 2>/dev/null
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
pip install -q -r requirements.txt
python -m patchright install chromium 2>/dev/null
deactivate 2>/dev/null || true

# Step 5: Configure ZIP code
if [ -z "$ZIP" ]; then
    echo ""
    read -p "  Enter your ZIP code (e.g. 90210): " ZIP
fi

if [ -n "$ZIP" ]; then
    echo "{\"zip_code\": \"$ZIP\"}" > "$INSTALL_DIR/config.json"
    echo "  [5/6] ZIP code set to $ZIP"
else
    ZIP="32224"
    echo "  [5/6] No ZIP code set — using default ($ZIP)"
fi

# Step 6: Register OpenClaw cron job
echo "  [6/6] Registering cron job..."

JOB_ID="mortgage-rates-$(date +%s)"

if [ -f "$CRON_FILE" ]; then
    # Check if a mortgage rate job already exists
    if python3 -c "
import json
with open('$CRON_FILE') as f:
    jobs = json.load(f)
existing = [j for j in jobs['jobs'] if 'mortgage' in j['name'].lower()]
if existing:
    print('EXISTS')
" 2>/dev/null | grep -q "EXISTS"; then
        echo "         Mortgage rate job already registered — skipping."
        echo ""
        echo "  ✅ Done! Your existing mortgage rate job will use the updated scraper."
        echo "  To run manually: openclaw run mortgage-rates"
        echo ""
        exit 0
    fi

    # Add the new job with OpenClaw browser steps for Chase + Rocket
    python3 << 'PYSCRIPT'
import json, time

cron_file = "$CRON_FILE"
install_dir = "$INSTALL_DIR"
job_id = "$JOB_ID"
zip_code = "$ZIP"

with open(cron_file) as f:
    data = json.load(f)

now_ms = int(time.time() * 1000)

# The cron job payload includes:
# 1. Run the patchright scraper for 8 automated lenders + 2 benchmarks
# 2. Use OpenClaw browser for Chase (needs real Chrome profile)
# 3. Use OpenClaw browser for Rocket Mortgage (needs real Chrome profile)
# 4. Combine all results into a formatted Discord report

payload_msg = f"""MORTGAGE RATES: Do NOT use the message tool.

STEP 1 — Run the script:
cd {install_dir} && source venv/bin/activate && python3 mortgage_rate_report.py 2>&1
Capture all rates from the output.

STEP 2 — Chase via OpenClaw browser (MANDATORY):
1. Open https://www.chase.com/personal/mortgage/mortgage-rates in the openclaw browser profile
2. ZIP {zip_code} should be pre-filled — click 'See rates'
3. Wait 4 seconds, evaluate document.body.innerText
4. Extract: 30yr Fixed, 15yr Fixed, 30yr FHA, 30yr Jumbo rates+APR

STEP 3 — Rocket Mortgage via OpenClaw browser:
1. Open https://www.rocketmortgage.com/mortgage-rates in the openclaw browser profile
2. Wait 5 seconds, evaluate document.body.innerText
3. Extract: 30yr, 15yr, FHA, VA rates+APR

STEP 4 — Combine and format using EXACTLY this Discord format:
📊 MORTGAGE RATES — [date] | X/X lenders reporting

📊 30-YEAR FIXED
🏆 [best lender] — X.XXX% (X.XXX% APR)
▸ [next lender] — X.XXX% (X.XXX% APR)
... all lenders sorted low to high
▸ Freddie Mac natl avg — X.XXX% (benchmark)
▸ MND Index — X.XXX% (benchmark)
📈 Avg: X.XXX% | vs yesterday: ▲/▼ X.XXX%

📊 15-YEAR FIXED
(same format)

📊 CHASE FULL MENU (ZIP {zip_code})
▸ 30yr Fixed — X.XXX% (X.XXX% APR)
▸ 15yr Fixed — X.XXX% (X.XXX% APR)
▸ 30yr FHA Fixed — X.XXX% (X.XXX% APR)
▸ 30yr Jumbo Fixed — X.XXX% (X.XXX% APR)

📊 ROCKET MORTGAGE
▸ 30yr Fixed — X.XXX% (X.XXX% APR)
▸ 15yr Fixed — X.XXX% (X.XXX% APR)
▸ 30yr FHA — X.XXX% (X.XXX% APR)
▸ 30yr VA — X.XXX% (X.XXX% APR)

No markdown tables. No code blocks. Plain Discord text only."""

job = {
    "id": job_id,
    "name": "daily-mortgage-rates",
    "enabled": True,
    "createdAtMs": now_ms,
    "updatedAtMs": now_ms,
    "schedule": {
        "kind": "cron",
        "expr": "0 8 * * *",
        "tz": "America/New_York"
    },
    "sessionTarget": "isolated",
    "wakeMode": "now",
    "payload": {
        "kind": "agentTurn",
        "message": payload_msg,
        "timeoutSeconds": 300
    },
    "delivery": {
        "mode": "announce",
        "channel": "discord"
    },
    "state": {
        "consecutiveErrors": 0
    }
}

data["jobs"].append(job)
with open(cron_file, "w") as f:
    json.dump(data, f, indent=2)
print("REGISTERED")
PYSCRIPT

    echo "         ✅ Cron job registered: daily at 8:00 AM EST"
else
    echo "  ⚠️  WARNING: $CRON_FILE not found."
    echo "           You can register the job manually with:"
    echo "           openclaw cron create --name daily-mortgage-rates --expr '0 8 * * *'"
fi

echo ""
echo "  ================================================"
echo "  🦞 Setup complete!"
echo ""
echo "  What happens every morning at 8 AM:"
echo "    1. Patchright scrapes 8 lenders + 2 benchmarks (headless)"
echo "    2. OpenClaw browser opens Chase + Rocket (real Chrome session)"
echo "    3. All rates combined, ranked, and delivered to Discord"
echo ""
echo "  To test now:"
echo "    cd $INSTALL_DIR"
echo "    source venv/bin/activate"
echo "    python3 mortgage_rate_report.py"
echo ""
echo "  To change your ZIP:  edit $INSTALL_DIR/config.json"
echo "  To change schedule:  edit $CRON_FILE (find 'daily-mortgage-rates')"
echo ""
echo "  ⚠️  If you skipped OpenClaw browser setup, run it before your"
echo "  first scheduled report: openclaw browser setup"
echo ""
