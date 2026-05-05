#!/bin/bash
# ──────────────────────────────────────────────────────────────
# Google Cloud Shell — Setup & Run Script
# Run this ONCE after cloning the repo to set up the environment,
# then use it again any time to re-run the pipeline.
# ──────────────────────────────────────────────────────────────

set -e

REPO_DIR="$HOME/web-scraper"

# ── Clone or pull latest ──────────────────────────────────────
if [ -d "$REPO_DIR" ]; then
    echo "[Setup] Repo already exists, pulling latest..."
    cd "$REPO_DIR"
    git pull
else
    echo "[Setup] Cloning repository..."
    # REPLACE with your actual GitHub repo URL:
    git clone https://github.com/Sachar04/web-scraper.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# ── Install dependencies ─────────────────────────────────────
echo "[Setup] Installing Python dependencies..."
pip install --user -r requirements.txt

# ── Run the pipeline ──────────────────────────────────────────
echo ""
echo "============================================"
echo "  Running Mastodon Scrape Pipeline"
echo "============================================"
echo ""

python pipeline.py --instance https://mastodon.social --action trends_statuses --limit 1 --format json

echo ""
echo "============================================"
echo "  Pipeline complete! Check output/ folder"
echo "============================================"
ls -la output/
