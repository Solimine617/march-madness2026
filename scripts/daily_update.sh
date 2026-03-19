#!/bin/bash
# March Madness 2026 - Daily Update Script
# Run each morning before games to refresh data and regenerate picks
#
# Usage: ./scripts/daily_update.sh

set -e
cd "$(dirname "$0")/.."

echo "============================================"
echo "MARCH MADNESS DAILY UPDATE - $(date)"
echo "============================================"

echo ""
echo "Step 1: Re-running 50K simulations..."
python3 analysis/simulate_v2.py

echo ""
echo "Step 2: Regenerating HTML..."
python3 analysis/generate_html_v2.py

echo ""
echo "Step 3: Opening in browser..."
open output/march_madness_2026.html

echo ""
echo "============================================"
echo "DONE. HTML updated at output/march_madness_2026.html"
echo "============================================"
echo ""
echo "REMEMBER: Before running, update these in simulate_v2.py:"
echo "  1. INJURY_ADJUSTMENTS (check for new injuries)"
echo "  2. MOMENTUM_ADJUSTMENTS (update with latest results)"
echo "  3. LIVE_ODDS_THURSDAY (update with today's lines)"
echo "  4. resolve_first_four() (lock in any new results)"
