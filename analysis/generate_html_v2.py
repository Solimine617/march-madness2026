#!/usr/bin/env python3
"""
Generate v2 HTML with confidence tiers, live odds, and Bracket Lab-style presentation.
"""

import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data():
    with open(DATA_DIR / "bracket_2026.json") as f:
        bracket = json.load(f)
    with open(DATA_DIR / "simulation_results_v2.json") as f:
        sim = json.load(f)
    with open(DATA_DIR / "brackets_v2.json") as f:
        brackets = json.load(f)
    with open(DATA_DIR / "betting_picks_v2.json") as f:
        picks = json.load(f)
    with open(DATA_DIR / "teams_database.json") as f:
        teams = json.load(f)
    return bracket, sim, brackets, picks, teams


def grade_color(grade):
    colors = {
        "A+": "#00e676", "A": "#4caf50", "B+": "#8bc34a",
        "B": "#cddc39", "C+": "#ffeb3b", "C": "#ffc107",
        "C-": "#ff9800", "D+": "#ff5722", "D": "#f44336",
    }
    return colors.get(grade, "#888")


def strategy_info(strategy):
    return {
        "chalk": {
            "name": "The Analyst",
            "emoji": "📊",
            "pool": "Small pools (5-15 people)",
            "desc": "Pure analytics. Picks the higher-rated team every game. Maximizes expected points.",
            "philosophy": "Consistency wins small pools. Be right the most often.",
        },
        "balanced": {
            "name": "The Strategist",
            "emoji": "⚖️",
            "pool": "Medium pools (15-100 people)",
            "desc": "Analytics core with strategic upsets where variance favors the underdog.",
            "philosophy": "Be mostly right but differentiate where the math supports it.",
        },
        "contrarian": {
            "name": "The Contrarian",
            "emoji": "🔄",
            "pool": "Large pools (100-1000 people)",
            "desc": "Targets underowned teams with real paths. Designed for ownership leverage.",
            "philosophy": "You can't win a big pool picking what everyone else picks.",
        },
        "chaos": {
            "name": "The Chaos Agent",
            "emoji": "🌪️",
            "pool": "Mega pools / longshot entry",
            "desc": "Maximum upsets for massive pools. Low probability, huge payoff if it hits.",
            "philosophy": "Go big or go home. This is your lottery ticket.",
        },
    }.get(strategy, {})


def generate_v2_html(bracket, sim, brackets, picks, teams):

    # --- CHAMPIONSHIP TABLE ---
    champ_rows = ""
    for team, pct in list(sim["champion"].items())[:20]:
        odds = teams["teams"].get(team, {}).get("championship_odds", "N/A")
        injuries = teams["teams"].get(team, {}).get("key_injuries", [])
        injury_text = ", ".join([f"<span style='color:#f44336'>{i['player']} ({i['status']})</span>" for i in injuries]) if injuries else "<span style='color:#4caf50'>Healthy</span>"
        hot_cold = teams["teams"].get(team, {}).get("hot_cold", "")
        hc_class = "hot" if "HOT" in str(hot_cold) else ("cold" if "COLD" in str(hot_cold) or "CRIPPLED" in str(hot_cold) or "COOLING" in str(hot_cold) else "steady")
        bar_width = min(pct * 3.5, 100)

        champ_rows += f"""
        <tr>
            <td><strong>{team}</strong></td>
            <td>
                <div style="display:flex;align-items:center;gap:8px;">
                    <div style="background:linear-gradient(90deg,#1565c0,#42a5f5);height:20px;width:{bar_width}%;border-radius:3px;min-width:2px;"></div>
                    <span>{pct}%</span>
                </div>
            </td>
            <td>{odds}</td>
            <td class="{hc_class}">{hot_cold[:60] if hot_cold else 'N/A'}</td>
            <td>{injury_text}</td>
        </tr>"""

    # --- BRACKET SECTIONS ---
    bracket_html = ""
    for key, b in brackets.items():
        cfg = b.get("pool_config", {})
        strat = cfg.get("strategy", key)
        info = strategy_info(strat)

        # Build region picks with confidence
        regions_html = ""
        for region_name in ["East", "West", "Midwest", "South"]:
            rd = b["regions"][region_name]
            picks_html = ""
            for pick in rd["all_picks"]:
                gc = grade_color(pick["confidence_grade"])
                picks_html += f"""
                <div class="pick-row">
                    <span class="pick-round">{pick['round']}</span>
                    <span class="pick-winner">{pick['winner']}</span>
                    <span class="pick-over">over {pick['loser']}</span>
                    <span class="pick-prob">{pick['probability']}%</span>
                    <span class="pick-grade" style="background:{gc};color:#000;">{pick['confidence_grade']}</span>
                </div>"""

            regions_html += f"""
            <div class="region-bracket">
                <h4>{region_name} Region → <strong>{rd['elite_8']}</strong></h4>
                {picks_html}
            </div>"""

        # Confidence summary
        conf = b.get("confidence_summary", {})
        conf_pills = " ".join([
            f"<span class='conf-pill' style='background:{grade_color(g)};color:#000;'>{g}: {c}</span>"
            for g, c in conf.items() if c > 0
        ])

        pool_name = cfg.get('name', info.get('name', strat))
        pool_desc = cfg.get('desc', info.get('desc', ''))
        pool_stakes = cfg.get('stakes', '')
        pool_size = cfg.get('pool_size', '')
        stakes_badge = f"<span style='background:var(--green);color:#000;padding:2px 8px;border-radius:10px;font-size:0.7em;margin-left:8px;'>MONEY</span>" if pool_stakes == "Money" else "<span style='background:var(--muted);color:#000;padding:2px 8px;border-radius:10px;font-size:0.7em;margin-left:8px;'>FREE</span>"

        bracket_html += f"""
        <div class="bracket-card" id="bracket-{key}">
            <div class="bracket-header">
                <h3>{pool_name} {stakes_badge}</h3>
                <p class="pool-size">{pool_size} people | {pool_stakes}</p>
                <p class="strat-desc">{pool_desc}</p>
            </div>
            <div class="ff-banner">
                <div class="ff-game"><span class="ff-name">{b['final_four'][0]}</span> vs <span class="ff-name">{b['final_four'][1]}</span></div>
                <div class="ff-game"><span class="ff-name">{b['final_four'][2]}</span> vs <span class="ff-name">{b['final_four'][3]}</span></div>
                <div class="champ-banner">CHAMPION: <strong>{b['champion']}</strong></div>
            </div>
            <div class="conf-summary">{conf_pills}</div>
            <div class="regions-grid">{regions_html}</div>
        </div>"""

    # --- BETTING PICKS ---
    sorted_picks = sorted(picks, key=lambda x: max(abs(x["edge_fav"]), abs(x["edge_dog"])), reverse=True)
    betting_rows = ""
    for p in sorted_picks:
        edge = max(abs(p["edge_fav"]), abs(p["edge_dog"]))
        if p["best_bet"] == "NO EDGE":
            row_class = "no-edge"
        elif p["confidence"] == "HIGH":
            row_class = "edge-high"
        elif p["confidence"] == "MEDIUM":
            row_class = "edge-med"
        else:
            row_class = "edge-low"

        spread_text = f"{p['spread']}" if p.get('spread') else "—"
        betting_rows += f"""
        <tr class="{row_class}">
            <td>{p['region']}</td>
            <td><strong>{p['matchup']}</strong></td>
            <td>{p['model_prob_fav']}%</td>
            <td>{p['model_prob_dog']}%</td>
            <td>{p['implied_prob_fav']}%</td>
            <td>{p['implied_prob_dog']}%</td>
            <td style="color:{('#4caf50' if p['confidence']=='HIGH' else '#ffc107') if p['best_bet']!='NO EDGE' else '#666'};font-weight:bold;">{p['best_bet']}</td>
            <td>{p['confidence']}</td>
            <td>{spread_text}</td>
        </tr>"""

    # --- INJURY CARDS ---
    injury_html = ""
    for team_name, team_data in teams["teams"].items():
        for inj in team_data.get("key_injuries", []):
            severity = "devastating" if "DEVASTATING" in inj["impact"] else ("high" if "HIGH" in inj["impact"] else "medium")
            injury_html += f"""
            <div class="inj-card inj-{severity}">
                <div class="inj-team">{team_name} ({team_data.get('seed', '?')} seed, {team_data.get('region', '?')})</div>
                <div class="inj-player">{inj['player']} ({inj['position']})</div>
                <div class="inj-detail">{inj['injury']}</div>
                <div class="inj-status">{inj['status']}</div>
                <div class="inj-impact">{inj['impact']}</div>
            </div>"""

    # --- REGION PROBABILITIES ---
    region_html = ""
    for region_name, probs in sim.get("region_winners", {}).items():
        bars = ""
        for team, pct in list(probs.items())[:8]:
            w = min(pct * 2, 100)
            bars += f"""<div class="rp-row"><span class="rp-name">{team}</span><div class="rp-bar-bg"><div class="rp-bar" style="width:{w}%">{pct}%</div></div></div>"""
        region_html += f"""<div class="rp-card"><h4>{region_name}</h4>{bars}</div>"""

    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>March Madness 2026 v2 — AI Bracket Lab</title>
<style>
:root {{
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #c9d1d9; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --gold: #d29922; --purple: #bc8cff;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background:var(--bg); color:var(--text); line-height:1.5; }}
.container {{ max-width:1400px; margin:0 auto; padding:16px; }}
header {{ background:linear-gradient(135deg, #0d1117, #161b22); padding:48px 24px; text-align:center; border-bottom:2px solid var(--accent); }}
header h1 {{ font-size:2.8em; background:linear-gradient(90deg, var(--accent), var(--purple)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
header .sub {{ color:var(--gold); font-size:1.2em; margin-top:8px; }}
header .meta {{ color:var(--muted); font-size:0.85em; margin-top:12px; }}
nav {{ background:var(--card); padding:12px 16px; position:sticky; top:0; z-index:100; border-bottom:1px solid var(--border); display:flex; flex-wrap:wrap; gap:6px; }}
nav a {{ color:var(--text); text-decoration:none; padding:6px 14px; border-radius:6px; font-size:0.85em; border:1px solid var(--border); transition:all 0.15s; }}
nav a:hover {{ background:var(--accent); color:#000; border-color:var(--accent); }}
nav a.hot {{ background:var(--red); color:#fff; border-color:var(--red); animation:pulse 2s infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.7}} }}
section {{ margin:48px 0; }}
h2 {{ font-size:1.6em; color:var(--accent); border-bottom:1px solid var(--border); padding-bottom:8px; margin-bottom:20px; }}
table {{ width:100%; border-collapse:collapse; font-size:0.9em; }}
th {{ background:var(--card); color:var(--accent); padding:10px; text-align:left; border-bottom:2px solid var(--border); position:sticky; top:50px; z-index:10; }}
td {{ padding:8px 10px; border-bottom:1px solid var(--border); }}
tr:hover {{ background:rgba(88,166,255,0.05); }}
.hot {{ color:var(--red); }} .cold {{ color:var(--accent); }} .steady {{ color:var(--muted); }}

.bracket-card {{ background:var(--card); border-radius:12px; padding:24px; margin:24px 0; border:1px solid var(--border); }}
.bracket-header {{ margin-bottom:16px; }}
.strat-badge {{ background:var(--accent); color:#000; padding:2px 10px; border-radius:20px; font-size:0.7em; font-weight:700; }}
.pool-size {{ color:var(--gold); font-weight:600; margin:4px 0; }}
.strat-desc {{ color:var(--muted); font-size:0.9em; }}
.strat-phil {{ color:var(--purple); font-size:0.9em; }}

.ff-banner {{ background:linear-gradient(135deg, #0d1117, #1a1f2e); border:2px solid var(--gold); border-radius:10px; padding:20px; text-align:center; margin:16px 0; }}
.ff-game {{ display:inline-block; margin:8px 20px; }}
.ff-name {{ background:var(--card); padding:6px 14px; border-radius:6px; font-weight:700; border:1px solid var(--border); }}
.champ-banner {{ font-size:1.4em; color:var(--gold); margin-top:12px; padding-top:12px; border-top:1px solid var(--border); }}

.conf-summary {{ margin:12px 0; display:flex; flex-wrap:wrap; gap:6px; }}
.conf-pill {{ padding:3px 10px; border-radius:12px; font-size:0.8em; font-weight:700; }}

.regions-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.region-bracket {{ background:rgba(255,255,255,0.02); border-radius:8px; padding:14px; border:1px solid var(--border); }}
.region-bracket h4 {{ color:var(--gold); margin-bottom:10px; font-size:0.95em; }}

.pick-row {{ display:flex; align-items:center; gap:6px; padding:3px 0; font-size:0.82em; border-bottom:1px solid rgba(255,255,255,0.03); }}
.pick-round {{ color:var(--muted); min-width:30px; font-size:0.75em; }}
.pick-winner {{ font-weight:600; min-width:120px; }}
.pick-over {{ color:var(--muted); font-size:0.8em; min-width:100px; }}
.pick-prob {{ color:var(--accent); min-width:45px; text-align:right; }}
.pick-grade {{ padding:1px 8px; border-radius:10px; font-size:0.75em; font-weight:700; min-width:28px; text-align:center; }}

.edge-high {{ background:rgba(63,185,80,0.08); }}
.edge-med {{ background:rgba(210,153,34,0.06); }}
.no-edge {{ opacity:0.5; }}

.inj-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:12px; }}
.inj-card {{ background:var(--card); border-radius:8px; padding:14px; }}
.inj-devastating {{ border-left:4px solid #8b0000; background:rgba(139,0,0,0.08); }}
.inj-high {{ border-left:4px solid var(--red); }}
.inj-medium {{ border-left:4px solid var(--gold); }}
.inj-team {{ color:var(--accent); font-weight:700; }}
.inj-player {{ font-size:1.1em; font-weight:600; margin:4px 0; }}
.inj-status {{ color:var(--red); font-weight:600; }}
.inj-impact {{ color:var(--muted); font-style:italic; font-size:0.9em; }}

.rp-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.rp-card {{ background:var(--card); border-radius:8px; padding:16px; }}
.rp-card h4 {{ color:var(--gold); margin-bottom:12px; }}
.rp-row {{ display:flex; align-items:center; margin:5px 0; }}
.rp-name {{ min-width:120px; font-size:0.85em; }}
.rp-bar-bg {{ flex:1; background:#1a1f2e; border-radius:4px; height:20px; }}
.rp-bar {{ background:linear-gradient(90deg, #0d47a1, var(--accent)); height:100%; border-radius:4px; display:flex; align-items:center; justify-content:flex-end; padding-right:6px; font-size:0.7em; font-weight:700; min-width:35px; }}

.insight-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(340px, 1fr)); gap:14px; }}
.insight-card {{ background:var(--card); border-radius:8px; padding:18px; border-top:3px solid var(--accent); }}
.insight-card h4 {{ color:var(--gold); margin-bottom:8px; }}
.insight-card.hot-take {{ border-top-color:var(--red); }}
.insight-card.value {{ border-top-color:var(--green); }}

.live-banner {{ background:linear-gradient(90deg, rgba(248,81,73,0.1), rgba(248,81,73,0.02)); border:1px solid var(--red); border-radius:8px; padding:16px; margin:16px 0; }}
.live-dot {{ display:inline-block; width:8px; height:8px; background:var(--red); border-radius:50%; margin-right:6px; animation:pulse 1.5s infinite; }}

footer {{ text-align:center; padding:24px; color:var(--muted); border-top:1px solid var(--border); margin-top:40px; font-size:0.85em; }}

@media (max-width:768px) {{ .regions-grid, .rp-grid {{ grid-template-columns:1fr; }} header h1 {{ font-size:1.8em; }} }}
</style>
</head>
<body>
<header>
    <h1>MARCH MADNESS 2026</h1>
    <div class="sub">v2 — BPI-Powered | Variance-Adjusted | Confidence-Tiered | 50,000 Simulations</div>
    <div class="meta">
        Generated: {now} | ESPN BPI (verified) + AP Poll + Injury-Adjusted + Travel + Coach + Variance<br>
        Inspired by <a href="#" style="color:var(--accent);">Bracket Lab</a>'s 10-step pipeline architecture
    </div>
</header>

<nav>
    <a href="#live">LIVE</a>
    <a href="#champ">Championship %</a>
    <a href="#injuries">Injuries</a>
    <a href="#brackets">4 Brackets</a>
    <a href="#regions">Regions</a>
    <a class="hot" href="#betting">BETTING EDGE</a>
    <a href="#compare" style="background:var(--purple);color:#fff;border-color:var(--purple);">Model vs BPI vs Torvik</a>
    <a href="#insights">Insights</a>
    <a href="#method">Methodology</a>
</nav>

<div class="container">

<!-- LIVE -->
<section id="live">
    <h2>LIVE Updates — March 18, 8:40 PM ET</h2>
    <div class="live-banner">
        <p><span class="live-dot"></span><strong>First Four IN PROGRESS</strong></p>
        <p><strong>Prairie View A&M 51, Lehigh 44</strong> — 2nd Half, 7:24 left. PV A&M pulling the upset (Lehigh was -3.5). Dontae Horne: 19 pts.</p>
        <p><strong>SMU (-7.5) vs Miami OH (31-1)</strong> — Tips at 9:15 PM. The most interesting First Four game in years.</p>
    </div>
    <div class="live-banner" style="border-color:var(--red);background:rgba(248,81,73,0.15);">
        <p><strong>NCAA CHARTER AIRCRAFT SHORTAGE:</strong> Government shutdown + ICE commandeering private charters = systemic travel disruption. Small programs with long travel most affected (Hawaii, High Point, Troy). Teams may arrive late, fatigued, off routine.</p>
    </div>
    <div class="live-banner" style="border-color:var(--gold);">
        <p><strong>BREAKING NEWS (confirmed tonight):</strong></p>
        <p style="color:var(--red);font-size:1.1em;"><strong>ALABAMA: Aden Holloway ARRESTED</strong> — felony marijuana (2.1 lbs). SUSPENDED, OFF TEAM. 16.8 PPG, 2nd leading scorer. Team in chaos.</p>
        <p style="color:var(--red);">Louisville: Mikel Brown Jr. OUT opening weekend (back) — 18.2 PPG, lottery pick</p>
        <p style="color:var(--red);">Duke: Patrick Ngongba II "very unlikely" per Scheyer — starting center, 11.4/6.5/2.1</p>
        <p style="color:var(--red);">Michigan: L.J. Cason torn ACL (season-ending) — confirmed worse than initially reported</p>
        <p style="color:var(--red);">Texas Tech: Toppin was 21.8 PPG / 10.8 RPG (All-American). On 3-game losing streak. Akron has won 19 of 20.</p>
        <p style="color:var(--red);">Kansas: Darryn Peterson "full-body cramps" drama — inconsistent availability all year</p>
    </div>
    <div class="live-banner" style="border-color:var(--green);">
        <p><strong>First Four Results (March 17):</strong></p>
        <p style="color:var(--green);">Howard 86, UMBC 83 — Howard's first-ever March Madness win. Plays (1) Michigan.</p>
        <p style="color:var(--green);">Texas 68, NC State 66 — Tramon Mark buzzer-beater. Plays (6) BYU.</p>
    </div>
</section>

<!-- CHAMPIONSHIP -->
<section id="champ">
    <h2>Championship Probabilities — 50,000 Simulations</h2>
    <table>
        <thead><tr><th>Team</th><th>Win Probability</th><th>Vegas</th><th>Status</th><th>Injuries</th></tr></thead>
        <tbody>{champ_rows}</tbody>
    </table>
</section>

<!-- INJURIES -->
<section id="injuries">
    <h2>Key Injuries — Impact-Ranked</h2>
    <div class="inj-grid">{injury_html}</div>
</section>

<!-- BRACKETS -->
<section id="brackets">
    <h2>5 Brackets for Your 4 Pools — Every Pick Graded</h2>
    <p style="color:var(--muted);margin-bottom:16px;">Each pick has a confidence grade (A+ to D) based on win probability. A+ = near-lock. D = longshot. The two 34-person entries have DIFFERENT champions to maximize coverage.</p>
    {bracket_html}
</section>

<!-- REGIONS -->
<section id="regions">
    <h2>Region Winner Probabilities</h2>
    <div class="rp-grid">{region_html}</div>
</section>

<!-- BETTING -->
<section id="betting">
    <h2>Betting Edge — Model vs Market</h2>
    <div class="live-banner" style="border-color:var(--green);">
        <h3 style="color:var(--green);">TOP 5 BETS (Highest Edge)</h3>
        <p><strong>1. South Florida +4.5 / ML +170 vs Louisville</strong> — Model: 70.3% USF. Market: 35.5%. Edge: +34.7%. Louisville CRIPPLED without Brown Jr (18.2 PPG).</p>
        <p><strong>2. Hofstra +23.5 vs Alabama</strong> — Model: 40.3% Hofstra. Market: 7.9%. Edge: +32.5%. Alabama lost Holloway (16.8 PPG) to FELONY ARREST. Team in chaos. The spread is STALE.</p>
        <p><strong>3. VCU ML vs North Carolina</strong> — Model: 69.0% VCU. Market: 37.5%. Edge: +31.5%. UNC without Caleb Wilson is a shell.</p>
        <p><strong>4. UCF over UCLA</strong> — Model: 63.4% UCF. UCLA star hurt + Dent limited + 2,700-mile travel. Edge: +23.9%.</p>
        <p><strong>5. Akron +7.5 vs Texas Tech</strong> — Model: 48.1% Akron (near coin flip!). Market: 25.9%. Edge: +22.2%. Tech lost All-American Toppin (21.8/10.8), on 3-game skid. Akron won 19 of 20.</p>
    </div>
    <table>
        <thead><tr><th>Region</th><th>Matchup</th><th>Model Fav%</th><th>Model Dog%</th><th>Market Fav%</th><th>Market Dog%</th><th>Best Bet</th><th>Conf</th><th>Spread</th></tr></thead>
        <tbody>{betting_rows}</tbody>
    </table>
</section>

<!-- MULTI-SOURCE COMPARISON -->
<section id="compare">
    <h2>Multi-Source Model Comparison — Where Our Edge Lives</h2>
    <p style="color:var(--muted);margin-bottom:16px;">ESPN BPI and BartTorvik use <strong>season-long data</strong>. They DON'T dynamically adjust for breaking injuries/suspensions. Our model does. That's the structural edge.</p>
    <table>
        <thead><tr><th>Game</th><th>Our Model</th><th>ESPN BPI</th><th>Market</th><th>Why We Disagree</th></tr></thead>
        <tbody>
            <tr class="edge-high">
                <td>(6) Louisville vs (11) USF</td>
                <td style="color:var(--green);font-weight:700;">70.3% USF</td>
                <td>81.0% Louisville</td>
                <td>LOU -4.5</td>
                <td>BPI doesn't reflect Brown Jr OUT (18.2 PPG). USF is 10-0, +19.6 margin L10.</td>
            </tr>
            <tr class="edge-high">
                <td>(4) Alabama vs (13) Hofstra</td>
                <td style="color:var(--green);font-weight:700;">40.3% Hofstra</td>
                <td>90.1% Alabama</td>
                <td>ALA -11.5</td>
                <td>Holloway ARRESTED (16.8 PPG, off team). BPI/market haven't fully adjusted. Spread moved 12 pts but still too high.</td>
            </tr>
            <tr class="edge-high">
                <td>(6) UNC vs (11) VCU</td>
                <td style="color:var(--green);font-weight:700;">69.0% VCU</td>
                <td>61.6% UNC</td>
                <td>UNC -2.5</td>
                <td>Torvik confirms UNC drops from 16.6 to 7.6 differential without Wilson. VCU 9-1 L10.</td>
            </tr>
            <tr class="edge-high">
                <td>(5) Texas Tech vs (12) Akron</td>
                <td style="color:var(--green);font-weight:700;">48.1% Akron</td>
                <td>81.9% Tech</td>
                <td>TT -7.5</td>
                <td>Toppin was ALL-AMERICAN (21.8/10.8). Tech on 3-game skid. Akron 19 of 20. BPI way off.</td>
            </tr>
            <tr class="edge-high">
                <td>(7) UCLA vs (10) UCF</td>
                <td style="color:var(--green);font-weight:700;">63.4% UCF</td>
                <td>72.2% UCLA</td>
                <td>UCLA -5.5</td>
                <td>UCLA star hurt + Dent limited (calf) + 2,700-mile travel to Philly.</td>
            </tr>
            <tr class="edge-med">
                <td>(7) Saint Mary's vs (10) A&M</td>
                <td>51.9% A&M</td>
                <td>53.2% SMC</td>
                <td>SMC -3.5</td>
                <td>All models say close. A&M veterans (7/8 seniors) + CBS model agrees.</td>
            </tr>
            <tr class="edge-med">
                <td>(8) Georgia vs (9) Saint Louis</td>
                <td>59.3% StL</td>
                <td>50.9% Georgia</td>
                <td>UGA -1.5</td>
                <td>BPI says coin flip. Our model gives StL edge: 86.4 ppg + 59.7% eFG vs Georgia's 302nd D.</td>
            </tr>
        </tbody>
    </table>

    <div class="live-banner" style="border-color:var(--purple);margin-top:20px;">
        <h3 style="color:var(--purple);">Championship: Our Model vs Torvik vs Market</h3>
        <table style="margin:10px 0;">
            <thead><tr><th>Team</th><th>Our Model</th><th>BartTorvik</th><th>Vegas Odds</th><th>Take</th></tr></thead>
            <tbody>
                <tr><td>Houston</td><td style="color:var(--green);font-weight:700;">17.6%</td><td>7.0%</td><td>+900 (10%)</td><td>We're highest. Home court S16/E8 + low variance = value bet.</td></tr>
                <tr><td>Florida</td><td style="color:var(--green);font-weight:700;">17.6%</td><td>9.1%</td><td>+750 (12%)</td><td>We're highest. Tampa + defending champ. Torvik undervalues.</td></tr>
                <tr><td>Arizona</td><td>16.8%</td><td>14.8%</td><td>+380 (22%)</td><td>Close to Torvik. Market overvalues (brand premium).</td></tr>
                <tr><td>Duke</td><td style="color:var(--red);">16.0%</td><td>20.2%</td><td>+325 (25%)</td><td>We're LOWEST. 2 starters out. Torvik/market = fade opportunity.</td></tr>
                <tr><td>Michigan</td><td style="color:var(--red);">8.1%</td><td>17.9%</td><td>+370 (21%)</td><td>We're MUCH lower. Cason ACL + lost B10 final. Others haven't adjusted.</td></tr>
            </tbody>
        </table>
    </div>
</section>

<!-- INSIGHTS -->
<section id="insights">
    <h2>Edge Insights</h2>
    <div class="insight-grid">
        <div class="insight-card value">
            <h4>Houston = Our #1 Pick (26.4%)</h4>
            <p>ESPN BPI #4 (23.0). DEF rating 12.6 (2nd best). Low variance (0.7) = consistent.</p>
            <p>Kelvin Sampson is HOF-level. Kingston Flemings + Chris Cenac = NBA 1st rounders.</p>
            <p><strong>HOME COURT for Sweet 16/Elite 8</strong> — South Region games are IN HOUSTON.</p>
            <p>At +900 futures (implied ~10%), our model gives them 26.4%. Massive value.</p>
        </div>
        <div class="insight-card hot-take">
            <h4>Louisville is a Trap</h4>
            <p>The -4.5 line is STALE. It was set before Brown Jr was ruled OUT.</p>
            <p>Without their 18.2 PPG lottery pick, Louisville drops from a legit 6-seed to maybe a 10-seed talent level.</p>
            <p>South Florida has won 12 straight and is the AAC champion.</p>
            <p>Our model: USF wins 67.3% of the time. This is the biggest first-round edge.</p>
        </div>
        <div class="insight-card hot-take">
            <h4>Why Variance Matters</h4>
            <p>This model uses <strong>variance modifiers</strong> (0.5-2.0 scale).</p>
            <p><strong>Low variance (consistent):</strong> Houston (0.7), Virginia (0.6), Michigan (0.7) — these teams rarely get upset early.</p>
            <p><strong>High variance (boom/bust):</strong> Alabama (1.6), Purdue (1.4), Illinois (1.4) — they CAN beat anyone but also CAN lose to anyone.</p>
            <p>In March, consistency compounds. Houston's low variance is why they're #1 in 50K sims.</p>
        </div>
        <div class="insight-card">
            <h4>Defense Survives, Offense Wins Titles</h4>
            <p><strong>Historical finding:</strong> Champions average #21 offense and #42 defense (KenPom). Offense is ~50% more important for WINNING titles. But defense prevents early-round upsets.</p>
            <p><strong>Survive (defense):</strong> Houston (#4 D), Michigan (#1 D), Iowa State (#6 D) — these grind through R64/R32.</p>
            <p><strong>Win titles (offense):</strong> Duke (OFF 12.9), Purdue (OFF 13.8), Illinois (OFF 13.1) — if they survive early, they can outscore anyone.</p>
            <p><strong>Both sides:</strong> Arizona (OFF 11.9, DEF 11.8) = the most balanced. That's why they're elite.</p>
        </div>
        <div class="insight-card value">
            <h4>Four Factors Analysis (ESPN Data)</h4>
            <p>The 4 Factors that predict basketball success:</p>
            <p><strong>eFG%:</strong> Saint Louis (.575, best!), Gonzaga (.563), Michigan (.556). South Florida (.493, worst) — but they compensate with...</p>
            <p><strong>ORB%:</strong> South Florida (.362, best!), Florida (.355), Houston (.350). Second-chance points are huge vs Louisville without Brown.</p>
            <p><strong>TO%:</strong> Arkansas (.108, best!), Houston (.111). Michigan (.150, WORST!) — hidden vulnerability for a 1-seed.</p>
            <p><strong>FT Rate:</strong> VCU (.437, best!), Arizona (.429). Getting to the line in tight games is critical in March.</p>
            <p style="color:var(--gold);"><strong>Michigan's .150 TO% is alarming.</strong> They turn it over the most of any contender. Against a pressing team, this could end them.</p>
        </div>
        <div class="insight-card">
            <h4>BPI Decomposition Insight</h4>
            <p>ESPN BPI breaks into OFF + DEF ratings. The most balanced team wins most often:</p>
            <p><strong>Duke</strong>: OFF 12.9 + DEF 12.8 = most balanced... when healthy</p>
            <p><strong>Houston</strong>: OFF 10.4 + DEF 12.6 = defense-anchored</p>
            <p><strong>Purdue</strong>: OFF 13.8 + DEF 6.8 = extreme offense, leaky D</p>
            <p>Balanced teams (gap < 3 between OFF/DEF) win titles. Extreme teams flame out.</p>
        </div>
        <div class="insight-card">
            <h4>The 5-12 Upset Spots</h4>
            <p>Historically 35% upset rate. This year's best candidates:</p>
            <p><strong>Akron over Texas Tech</strong> — Tech lost Toppin + 10 losses + our model: 44.4% Akron</p>
            <p><strong>McNeese over Vanderbilt</strong> — Vandy's #29 defense is exploitable</p>
            <p><strong>Troy over Nebraska</strong> — CBS Cinderella pick, beat SDSU on road</p>
        </div>
    </div>
</section>

<!-- METHODOLOGY -->
<section id="method">
    <h2>Methodology — 10-Step Pipeline</h2>
    <div class="insight-grid">
        <div class="insight-card">
            <h4>Step 1: Base Rating</h4>
            <p>ESPN BPI (Basketball Power Index) — verified for top 10 teams from espn.com/bpi. Remaining teams estimated from AP poll points + record.</p>
        </div>
        <div class="insight-card">
            <h4>Step 2: Injury Adjustment</h4>
            <p>Player production share × minutes percentage. Brown Jr (Louisville) = -4.5 because he's 35% of their offense.</p>
        </div>
        <div class="insight-card">
            <h4>Step 3: Momentum</h4>
            <p>Conference tournament results + late-season form. Winners get +0.5 to +1.5. Losers get -0.5 to -2.0.</p>
        </div>
        <div class="insight-card">
            <h4>Step 4: Travel/Venue</h4>
            <p>Distance to venue + crowd composition. Florida in Tampa (+2.5) vs Hawaii in Portland (-2.0).</p>
        </div>
        <div class="insight-card">
            <h4>Step 5: Coach Pedigree</h4>
            <p>Historical March overperformance. Izzo (+1.5), Sampson (+1.5), Hurley (+1.5).</p>
        </div>
        <div class="insight-card">
            <h4>Step 6-7: Variance + Win Prob</h4>
            <p>Variance modifier (0.5-2.0) affects logistic slope. High-variance teams have flatter probability curves = more upsets. 50,000 Monte Carlo sims.</p>
        </div>
        <div class="insight-card">
            <h4>Step 8-9: Betting Edge</h4>
            <p>Model probability vs live moneyline-implied probability (vig-removed). Edges > 3% are flagged. Compared against historical seed upset rates as baseline.</p>
        </div>
        <div class="insight-card">
            <h4>Step 10: Confidence Tiers</h4>
            <p>Every pick graded A+ (>90% confidence) through D (<30%). This lets you see exactly how confident the model is about each pick in your bracket.</p>
        </div>
    </div>
</section>

</div>

<footer>
    <p>March Madness 2026 v2 | 50,000 Monte Carlo Simulations | ESPN BPI-Powered</p>
    <p>Data: ESPN BPI, AP Poll, CBS Sports, RotoWire, Vegas Insider, DraftKings | Updated: {now}</p>
    <p style="color:var(--red);margin-top:8px;">Gambling involves risk. Never bet more than you can afford to lose. 18+</p>
</footer>
</body>
</html>"""

    output_path = OUTPUT_DIR / "march_madness_2026.html"
    with open(output_path, "w") as f:
        f.write(html)
    print(f"v2 HTML saved to {output_path}")
    return output_path


if __name__ == "__main__":
    data = load_data()
    path = generate_v2_html(*data)
    print(f"\nOpen: file://{path}")
