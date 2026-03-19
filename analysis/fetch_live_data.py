#!/usr/bin/env python3
"""
Fetch live data from ESPN's free API for March Madness 2026.
No API key required. Pulls scores, odds, injuries, and game details.

Usage:
    python3 fetch_live_data.py              # Today's games
    python3 fetch_live_data.py 20260319     # Specific date
    python3 fetch_live_data.py odds         # Just odds for today
    python3 fetch_live_data.py injuries     # Tournament injury report
"""

import json
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# Fix SSL on macOS Python installs
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.check_hostname = False
    SSL_CONTEXT.verify_mode = ssl.CERT_NONE

DATA_DIR = Path(__file__).parent.parent / "data"
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"


def fetch_json(url):
    """Fetch JSON from URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def fetch_scoreboard(date=None):
    """Fetch today's (or specified date's) scoreboard with scores and odds."""
    if date:
        url = f"{BASE_URL}/scoreboard?dates={date}&groups=50&limit=200"
    else:
        url = f"{BASE_URL}/scoreboard?groups=50&limit=200"

    data = fetch_json(url)
    if not data:
        return []

    games = []
    for event in data.get("events", []):
        game = {
            "id": event.get("id"),
            "name": event.get("name", ""),
            "date": event.get("date", ""),
            "status": event.get("status", {}).get("type", {}).get("description", ""),
            "venue": event.get("competitions", [{}])[0].get("venue", {}).get("fullName", ""),
            "broadcast": "",
            "teams": [],
            "odds": {},
        }

        comp = event.get("competitions", [{}])[0]

        # Broadcast info
        broadcasts = comp.get("broadcasts", [])
        if broadcasts:
            names = []
            for b in broadcasts:
                b_names = b.get("names", [])
                for n in b_names:
                    if isinstance(n, dict):
                        names.append(n.get("shortName", ""))
                    elif isinstance(n, str):
                        names.append(n)
            game["broadcast"] = ", ".join(names)

        # Teams and scores
        for team_data in comp.get("competitors", []):
            team_info = team_data.get("team", {})
            team = {
                "id": team_info.get("id"),
                "name": team_info.get("displayName", team_info.get("name", "")),
                "abbreviation": team_info.get("abbreviation", ""),
                "seed": team_data.get("curatedRank", {}).get("current", ""),
                "score": team_data.get("score", ""),
                "winner": team_data.get("winner", False),
                "home_away": team_data.get("homeAway", ""),
                "record": team_data.get("records", [{}])[0].get("summary", "") if team_data.get("records") else "",
            }
            game["teams"].append(team)

        # Odds
        odds_data = comp.get("odds", [])
        if odds_data:
            odds = odds_data[0]
            game["odds"] = {
                "provider": odds.get("provider", {}).get("name", ""),
                "spread": odds.get("details", ""),
                "overUnder": odds.get("overUnder", ""),
                "home_ml": "",
                "away_ml": "",
            }
            # Try to get moneylines
            if "homeTeamOdds" in odds:
                game["odds"]["home_ml"] = odds["homeTeamOdds"].get("moneyLine", "")
            if "awayTeamOdds" in odds:
                game["odds"]["away_ml"] = odds["awayTeamOdds"].get("moneyLine", "")

        games.append(game)

    return games


def fetch_game_summary(event_id):
    """Fetch detailed game summary including injuries."""
    url = f"{BASE_URL}/summary?event={event_id}"
    return fetch_json(url)


def fetch_tournament_injuries():
    """Fetch injuries for tournament teams by checking recent game summaries."""
    # Get today's scoreboard to find event IDs
    games = fetch_scoreboard()
    injuries = []

    for game in games:
        if game["id"]:
            summary = fetch_game_summary(game["id"])
            if summary and "injuries" in summary:
                for team_injuries in summary["injuries"]:
                    team_name = team_injuries.get("team", {}).get("displayName", "Unknown")
                    for item in team_injuries.get("injuries", []):
                        injuries.append({
                            "team": team_name,
                            "player": item.get("athlete", {}).get("displayName", "Unknown"),
                            "status": item.get("status", "Unknown"),
                            "type": item.get("type", {}).get("description", "Unknown"),
                            "detail": item.get("longComment", item.get("shortComment", "")),
                        })

    return injuries


def print_scoreboard(games):
    """Pretty print the scoreboard."""
    if not games:
        print("  No games found for this date.")
        return

    for game in games:
        print(f"\n  {'='*60}")
        print(f"  {game['name']}")
        print(f"  Status: {game['status']} | Venue: {game['venue']}")
        if game['broadcast']:
            print(f"  TV: {game['broadcast']}")

        for team in game['teams']:
            seed_str = f"({team['seed']}) " if team['seed'] else ""
            score_str = f" - {team['score']}" if team['score'] else ""
            winner_str = " W" if team['winner'] else ""
            print(f"    {seed_str}{team['name']} ({team['record']}){score_str}{winner_str}")

        if game['odds']:
            odds = game['odds']
            print(f"  Odds ({odds['provider']}): {odds['spread']} | O/U: {odds['overUnder']}")
            if odds['home_ml'] or odds['away_ml']:
                print(f"  ML: Home {odds['home_ml']} / Away {odds['away_ml']}")


def print_odds_only(games):
    """Print just the odds for betting analysis."""
    print(f"\n  {'Team Matchup':<45} {'Spread':<15} {'O/U':<10} {'ML Home':<10} {'ML Away'}")
    print(f"  {'-'*90}")
    for game in games:
        if not game['odds'] or not game['odds'].get('spread'):
            continue
        teams = " vs ".join([f"({t['seed']}){t['abbreviation']}" if t['seed'] else t['abbreviation'] for t in game['teams']])
        odds = game['odds']
        print(f"  {teams:<45} {odds['spread']:<15} {odds['overUnder']:<10} {str(odds['home_ml']):<10} {odds['away_ml']}")


def save_data(games, filename="live_scoreboard.json"):
    """Save fetched data to JSON."""
    output_path = DATA_DIR / filename
    with open(output_path, "w") as f:
        json.dump(games, f, indent=2)
    print(f"\n  Data saved to {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("MARCH MADNESS 2026 - LIVE DATA FETCHER")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
    print("=" * 60)

    mode = sys.argv[1] if len(sys.argv) > 1 else None

    if mode == "injuries":
        print("\nFetching tournament injury report...")
        injuries = fetch_tournament_injuries()
        if injuries:
            for inj in injuries:
                print(f"  {inj['team']} - {inj['player']}: {inj['status']} ({inj['type']})")
                if inj['detail']:
                    print(f"    {inj['detail']}")
        else:
            print("  No injury data available for today's games.")

    elif mode == "odds":
        print("\nFetching odds for today's games...")
        games = fetch_scoreboard()
        print_odds_only(games)
        save_data(games, "live_odds.json")

    elif mode and mode.isdigit():
        print(f"\nFetching scoreboard for {mode}...")
        games = fetch_scoreboard(date=mode)
        print_scoreboard(games)
        save_data(games, f"scoreboard_{mode}.json")

    else:
        print("\nFetching today's scoreboard...")
        games = fetch_scoreboard()
        print_scoreboard(games)
        save_data(games)

    print(f"\n{'='*60}")
    print("Usage: python3 fetch_live_data.py [date|odds|injuries]")
    print("  date format: YYYYMMDD (e.g., 20260319)")
