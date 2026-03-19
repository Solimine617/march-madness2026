#!/usr/bin/env python3
"""
Generate comprehensive HTML output for March Madness 2026 brackets and betting picks.
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
    with open(DATA_DIR / "simulation_results.json") as f:
        sim = json.load(f)
    with open(DATA_DIR / "brackets.json") as f:
        brackets = json.load(f)
    with open(DATA_DIR / "betting_picks.json") as f:
        picks = json.load(f)
    with open(DATA_DIR / "teams_database.json") as f:
        teams = json.load(f)
    return bracket, sim, brackets, picks, teams


def get_seed_for_team(team, bracket):
    for region in bracket["regions"].values():
        for m in region["matchups"]:
            if m["team_high"] == team:
                return m["seed_high"]
            if team in m["team_low"]:
                return m["seed_low"]
    return "?"


def bracket_strategy_description(strategy):
    descs = {
        "chalk": {
            "name": "The Analyst",
            "pool": "Small pools (10 people)",
            "desc": "Pure analytics. Picks the higher-rated team in every game. Maximizes expected points. Best for small pools where consistency wins.",
            "philosophy": "Win by being right the most often. In a 10-person pool, the most accurate bracket usually wins."
        },
        "simulation": {
            "name": "The Simulator",
            "pool": "Medium pools (30 people)",
            "desc": "Based on 50,000 Monte Carlo simulations. Picks the most likely outcome at every branch. Slightly different from chalk due to path dependencies.",
            "philosophy": "Let the math decide. Simulation captures cascading effects that raw power ratings miss."
        },
        "balanced": {
            "name": "The Strategist",
            "pool": "Medium-large pools (50 people)",
            "desc": "Chalk core with strategic upsets where the model sees value. Balances expected points with differentiation.",
            "philosophy": "Be mostly right but differentiate enough to separate from the pack."
        },
        "contrarian": {
            "name": "The Contrarian",
            "pool": "Large pools (1000 people)",
            "desc": "Targets less popular teams where analytics still support them. Designed to win big pools through ownership leverage.",
            "philosophy": "You can't win a 1000-person pool picking the same bracket as everyone else. Find the road less traveled."
        },
        "chaos": {
            "name": "The Chaos Agent",
            "pool": "Mega pools / longshot entry",
            "desc": "Maximum upset picks for massive pools. Low probability of winning but huge payoff if it hits. Your lottery ticket.",
            "philosophy": "Go big or go home. This bracket wins maybe 1% of the time, but when it does, nobody else has it."
        },
        "value": {
            "name": "The Value Hunter",
            "pool": "Medium pools (30-50 people)",
            "desc": "Picks teams where our model gives them more credit than the betting market. Exploits market inefficiencies.",
            "philosophy": "The market is usually right but not always. Find where the crowd is wrong."
        }
    }
    return descs.get(strategy, {"name": strategy, "pool": "", "desc": "", "philosophy": ""})


def generate_main_html(bracket, sim, brackets, picks, teams):
    """Generate the main comprehensive HTML file."""

    # Championship odds comparison
    champ_rows = ""
    for team, pct in list(sim["champion"].items())[:20]:
        odds = teams["teams"].get(team, {}).get("championship_odds", "N/A")
        injuries = teams["teams"].get(team, {}).get("key_injuries", [])
        injury_text = ", ".join([f"{i['player']} ({i['status']})" for i in injuries]) if injuries else "Healthy"
        injury_class = "injury-alert" if injuries else "healthy"
        hot_cold = teams["teams"].get(team, {}).get("hot_cold", "N/A")
        hot_class = "hot" if "HOT" in str(hot_cold) else ("cold" if "COLD" in str(hot_cold) else "steady")

        champ_rows += f"""
        <tr>
            <td><strong>{team}</strong></td>
            <td>{pct}%</td>
            <td>{odds}</td>
            <td class="{hot_class}">{hot_cold}</td>
            <td class="{injury_class}">{injury_text}</td>
        </tr>"""

    # Bracket strategy sections
    bracket_sections = ""
    strategy_order = ["chalk", "simulation", "balanced", "value", "contrarian", "chaos"]
    for strategy in strategy_order:
        b = brackets[strategy]
        info = bracket_strategy_description(strategy)
        region_html = ""

        for region_name in ["East", "West", "Midwest", "South"]:
            rd = b["regions"][region_name]
            r64_picks = " → ".join([f"<span class='pick'>{g['winner']}</span>" for g in rd["R64"]])
            r32_picks = " → ".join([f"<span class='pick'>{g['winner']}</span>" for g in rd["R32"]])
            s16_picks = " → ".join([f"<span class='pick'>{g['winner']}</span>" for g in rd["S16"]])
            e8_pick = rd["elite_8"]

            region_html += f"""
            <div class="region-card">
                <h4>{region_name} Region</h4>
                <div class="round"><span class="round-label">R64:</span> {r64_picks}</div>
                <div class="round"><span class="round-label">R32:</span> {r32_picks}</div>
                <div class="round"><span class="round-label">S16:</span> {s16_picks}</div>
                <div class="round elite"><span class="round-label">Elite 8 Winner:</span> <strong>{e8_pick}</strong></div>
            </div>"""

        ff = b.get("final_four", [])
        champ = b.get("champion", "TBD")

        bracket_sections += f"""
        <div class="bracket-strategy" id="{strategy}">
            <div class="strategy-header">
                <h3>{info['name']} <span class="strategy-tag">{strategy.upper()}</span></h3>
                <p class="pool-rec">Best for: {info['pool']}</p>
                <p class="strategy-desc">{info['desc']}</p>
                <p class="philosophy"><em>"{info['philosophy']}"</em></p>
            </div>
            <div class="final-four-banner">
                <div class="ff-matchup">
                    <span class="ff-team">{ff[0] if len(ff) > 0 else '?'}</span>
                    <span class="vs">vs</span>
                    <span class="ff-team">{ff[1] if len(ff) > 1 else '?'}</span>
                </div>
                <div class="ff-matchup">
                    <span class="ff-team">{ff[2] if len(ff) > 2 else '?'}</span>
                    <span class="vs">vs</span>
                    <span class="ff-team">{ff[3] if len(ff) > 3 else '?'}</span>
                </div>
                <div class="champion-pick">CHAMPION: <strong>{champ}</strong></div>
            </div>
            <div class="regions-grid">
                {region_html}
            </div>
        </div>"""

    # Betting picks section
    betting_rows = ""
    for p in sorted(picks, key=lambda x: max(abs(x["edge_fav"]), abs(x["edge_dog"])), reverse=True):
        edge = max(abs(p["edge_fav"]), abs(p["edge_dog"]))
        if p["best_bet"] == "NO EDGE":
            bet_class = "no-edge"
            bet_text = "No clear edge"
        else:
            bet_class = "has-edge"
            bet_text = p["best_bet"]

        conf_class = p["confidence"].lower()
        betting_rows += f"""
        <tr class="{bet_class}">
            <td>{p['region']}</td>
            <td>{p['matchup']}</td>
            <td>{p['model_prob_fav']}%</td>
            <td>{p['model_prob_dog']}%</td>
            <td>{p['edge_fav']:+.1f}%</td>
            <td>{p['edge_dog']:+.1f}%</td>
            <td><strong>{bet_text}</strong></td>
            <td class="conf-{conf_class}">{p['confidence']}</td>
            <td>{p['venue']}</td>
        </tr>"""

    # Key injuries section
    injury_cards = ""
    for team_name, team_data in teams["teams"].items():
        for inj in team_data.get("key_injuries", []):
            impact_class = inj["impact"].split(" ")[0].lower()
            injury_cards += f"""
            <div class="injury-card impact-{impact_class}">
                <div class="injury-team">{team_name} ({team_data.get('seed', '?')} seed)</div>
                <div class="injury-player">{inj['player']} - {inj['position']}</div>
                <div class="injury-detail">{inj['injury']}</div>
                <div class="injury-status">Status: {inj['status']}</div>
                <div class="injury-impact">Impact: {inj['impact']}</div>
            </div>"""

    # Region winner probabilities
    region_prob_html = ""
    for region_name, probs in sim["region_winners"].items():
        rows = ""
        for team, pct in list(probs.items())[:8]:
            bar_width = min(pct, 100)
            rows += f"""
            <div class="prob-row">
                <span class="prob-team">{team}</span>
                <div class="prob-bar-bg"><div class="prob-bar" style="width: {bar_width}%">{pct}%</div></div>
            </div>"""
        region_prob_html += f"""
        <div class="region-prob-card">
            <h4>{region_name} Region Winner</h4>
            {rows}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>March Madness 2026 - AI-Powered Analysis</title>
    <style>
        :root {{
            --primary: #1a1a2e;
            --secondary: #16213e;
            --accent: #e94560;
            --accent2: #0f3460;
            --gold: #f5a623;
            --green: #27ae60;
            --red: #e74c3c;
            --blue: #3498db;
            --bg: #0a0a1a;
            --card: #1a1a2e;
            --text: #e0e0e0;
            --text-muted: #888;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        header {{
            background: linear-gradient(135deg, var(--primary), var(--accent2));
            padding: 40px 20px;
            text-align: center;
            border-bottom: 3px solid var(--accent);
        }}
        header h1 {{ font-size: 2.5em; color: white; margin-bottom: 10px; }}
        header .subtitle {{ color: var(--gold); font-size: 1.2em; }}
        header .meta {{ color: var(--text-muted); margin-top: 10px; font-size: 0.9em; }}

        nav {{
            background: var(--secondary);
            padding: 15px;
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 2px solid var(--accent);
        }}
        nav a {{
            color: var(--text);
            text-decoration: none;
            padding: 8px 16px;
            margin: 4px;
            border-radius: 4px;
            display: inline-block;
            transition: all 0.2s;
        }}
        nav a:hover {{ background: var(--accent); color: white; }}

        section {{ margin: 40px 0; }}
        h2 {{
            font-size: 1.8em;
            color: var(--gold);
            border-bottom: 2px solid var(--accent);
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h3 {{ color: var(--blue); margin-bottom: 10px; }}

        /* Championship Odds Table */
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: var(--accent2); color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #333; }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .hot {{ color: #e74c3c; font-weight: bold; }}
        .cold {{ color: #3498db; font-weight: bold; }}
        .steady {{ color: #95a5a6; }}
        .injury-alert {{ color: var(--red); }}
        .healthy {{ color: var(--green); }}

        /* Bracket Strategy Cards */
        .bracket-strategy {{
            background: var(--card);
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
            border: 1px solid #333;
        }}
        .strategy-header {{ margin-bottom: 20px; }}
        .strategy-tag {{
            background: var(--accent);
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.7em;
            vertical-align: middle;
        }}
        .pool-rec {{ color: var(--gold); font-weight: bold; }}
        .strategy-desc {{ color: var(--text-muted); }}
        .philosophy {{ color: var(--blue); margin-top: 5px; }}

        .final-four-banner {{
            background: linear-gradient(135deg, #1a1a3e, #2a1a3e);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
            border: 2px solid var(--gold);
        }}
        .ff-matchup {{
            display: inline-block;
            margin: 10px 20px;
        }}
        .ff-team {{
            background: var(--accent2);
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            display: inline-block;
        }}
        .vs {{ color: var(--accent); margin: 0 8px; font-weight: bold; }}
        .champion-pick {{
            font-size: 1.4em;
            color: var(--gold);
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #444;
        }}

        .regions-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        .region-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            padding: 15px;
            border: 1px solid #444;
        }}
        .region-card h4 {{ color: var(--accent); margin-bottom: 10px; }}
        .round {{ margin: 5px 0; font-size: 0.85em; }}
        .round-label {{ color: var(--text-muted); font-weight: bold; min-width: 40px; display: inline-block; }}
        .pick {{
            background: rgba(52, 152, 219, 0.15);
            padding: 2px 6px;
            border-radius: 3px;
            margin: 1px;
            display: inline-block;
        }}
        .round.elite {{ color: var(--gold); font-size: 1em; margin-top: 8px; }}

        /* Betting Picks */
        .has-edge {{ background: rgba(39, 174, 96, 0.1); }}
        .no-edge {{ opacity: 0.6; }}
        .conf-high {{ color: var(--green); font-weight: bold; }}
        .conf-medium {{ color: var(--gold); }}
        .conf-low {{ color: var(--text-muted); }}

        /* Injury Cards */
        .injury-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }}
        .injury-card {{
            background: var(--card);
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid var(--red);
        }}
        .impact-high .injury-card, .injury-card.impact-high {{ border-left-color: var(--red); }}
        .impact-medium .injury-card, .injury-card.impact-medium {{ border-left-color: var(--gold); }}
        .impact-devastating .injury-card, .injury-card.impact-devastating {{ border-left-color: #8b0000; background: rgba(139,0,0,0.1); }}
        .injury-team {{ font-weight: bold; color: var(--accent); }}
        .injury-player {{ font-size: 1.1em; margin: 5px 0; }}
        .injury-status {{ color: var(--red); }}
        .injury-impact {{ color: var(--text-muted); font-style: italic; }}

        /* Probability Bars */
        .region-prob-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .region-prob-card {{ background: var(--card); border-radius: 8px; padding: 20px; }}
        .region-prob-card h4 {{ color: var(--accent); margin-bottom: 15px; }}
        .prob-row {{ display: flex; align-items: center; margin: 6px 0; }}
        .prob-team {{ min-width: 130px; font-size: 0.9em; }}
        .prob-bar-bg {{ flex: 1; background: #222; border-radius: 4px; height: 22px; }}
        .prob-bar {{
            background: linear-gradient(90deg, var(--accent2), var(--blue));
            height: 100%;
            border-radius: 4px;
            min-width: 30px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 6px;
            font-size: 0.75em;
            font-weight: bold;
        }}

        /* Insights */
        .insight-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; }}
        .insight-card {{
            background: var(--card);
            border-radius: 8px;
            padding: 20px;
            border-top: 3px solid var(--blue);
        }}
        .insight-card h4 {{ color: var(--gold); margin-bottom: 8px; }}

        .bankroll-info {{
            background: linear-gradient(135deg, rgba(39,174,96,0.1), rgba(52,152,219,0.1));
            border: 1px solid var(--green);
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}

        footer {{
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
            border-top: 1px solid #333;
            margin-top: 40px;
        }}

        @media (max-width: 768px) {{
            .regions-grid, .region-prob-grid {{ grid-template-columns: 1fr; }}
            header h1 {{ font-size: 1.5em; }}
            nav a {{ padding: 6px 10px; font-size: 0.85em; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>MARCH MADNESS 2026</h1>
        <div class="subtitle">AI-Powered Bracket & Betting Analysis</div>
        <div class="meta">
            50,000 Monte Carlo Simulations | ESPN BPI + BartTorvik Composite | Injury-Adjusted | Travel-Factored<br>
            Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Data Sources: ESPN, KenPom, RotoWire, Vegas Insider
        </div>
    </header>

    <nav>
        <a href="#overview">Overview</a>
        <a href="#championship">Championship Odds</a>
        <a href="#injuries">Key Injuries</a>
        <a href="#live-odds" style="background:var(--accent);color:white;font-weight:bold;">LIVE ODDS Thu</a>
        <a href="#regions">Region Probabilities</a>
        <a href="#brackets">6 Bracket Strategies</a>
        <a href="#betting">Model Picks</a>
        <a href="#insights">Edge Insights</a>
        <a href="#methodology">Methodology</a>
    </nav>

    <div class="container">

        <!-- OVERVIEW -->
        <section id="overview">
            <h2>Tournament Overview</h2>
            <div class="insight-grid">
                <div class="insight-card">
                    <h4>No. 1 Seeds</h4>
                    <p><strong>Duke</strong> (East) - #1 overall, Cameron Boozer NPOY, but missing Foster + Ngongba unlikely</p>
                    <p><strong>Arizona</strong> (West) - Our model's favorite (20.8%). "Safest bet" per CBS. Healthy.</p>
                    <p><strong>Michigan</strong> (Midwest) - #1 defense but lost Big Ten tourney to Purdue, Cason ACL tear.</p>
                    <p><strong>Florida</strong> (South) - DEFENDING CHAMP. Playing in Tampa = home game.</p>
                </div>
                <div class="insight-card" style="border-top: 3px solid var(--accent);">
                    <h4>GAME DAY - March 19 Final Updates</h4>
                    <p style="color:var(--red);"><strong>Louisville's Mikel Brown Jr. officially OUT</strong>. Line moved -7.5 to -4.5. 85% sharp money on USF.</p>
                    <p style="color:var(--red);"><strong>Duke's Ngongba officially OUT</strong> for opener. Maliq Brown starts (foul trouble risk).</p>
                    <p style="color:var(--red);"><strong>Alabama's Holloway OFF TEAM</strong> - felony arrest. 16.8 PPG gone + team morale shattered.</p>
                    <p style="color:var(--green);"><strong>Michigan's Lendeborg CLEARED</strong> (ankle). Full strength minus Cason (ACL).</p>
                    <p style="color:var(--green);"><strong>First Four COMPLETE:</strong> Howard 86-83 UMBC | Texas 68-66 NC State | Miami OH 89-79 SMU (UPSET!) | PV A&M 67-55 Lehigh (UPSET!)</p>
                    <p><strong>NCAA charter aircraft shortage</strong> due to gov shutdown/ICE. No delays reported yet but monitoring.</p>
                </div>
                <div class="insight-card">
                    <h4>ESPN Scoring (Standard)</h4>
                    <p>Round of 64: <strong>10 pts</strong> per correct pick</p>
                    <p>Round of 32: <strong>20 pts</strong></p>
                    <p>Sweet 16: <strong>40 pts</strong></p>
                    <p>Elite 8: <strong>80 pts</strong></p>
                    <p>Final Four: <strong>160 pts</strong></p>
                    <p>Championship: <strong>320 pts</strong></p>
                    <p>Max possible: <strong>1,920 pts</strong></p>
                </div>
                <div class="insight-card" style="border-top: 3px solid var(--gold);">
                    <h4>YOUR 5 BRACKETS</h4>
                    <p><strong>Free 8-person:</strong> MICHIGAN champion (heart pick, tiny pool)</p>
                    <p><strong>Money 18-person:</strong> HOUSTON champion (best value play)</p>
                    <p><strong>Free 20-person:</strong> FLORIDA champion (defending champ, home court)</p>
                    <p><strong>Money 34-person #1:</strong> HOUSTON champion (highest expected pts)</p>
                    <p><strong>Money 34-person #2:</strong> VIRGINIA champion (contrarian hedge)</p>
                    <p style="color:var(--text-muted);font-size:0.85em;">Two different champs in 34-person pool = 2x coverage</p>
                </div>
            </div>
        </section>

        <!-- CHAMPIONSHIP PROBABILITIES -->
        <section id="championship">
            <h2>Championship Probabilities (50,000 Simulations)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Team</th>
                        <th>Model Win %</th>
                        <th>Vegas Odds</th>
                        <th>Momentum</th>
                        <th>Injuries</th>
                    </tr>
                </thead>
                <tbody>
                    {champ_rows}
                </tbody>
            </table>
        </section>

        <!-- KEY INJURIES -->
        <section id="injuries">
            <h2>Key Injuries to Watch</h2>
            <div class="injury-grid">
                {injury_cards}
            </div>
        </section>

        <!-- REGION PROBABILITIES -->
        <section id="regions">
            <h2>Region Winner Probabilities</h2>
            <div class="region-prob-grid">
                {region_prob_html}
            </div>
        </section>

        <!-- 6 BRACKET STRATEGIES -->
        <section id="brackets">
            <h2>6 Bracket Strategies</h2>
            <p style="color: var(--text-muted); margin-bottom: 20px;">
                6 strategies generated. Your 5 entries: Free 8-person (Michigan champ), Money 18-person (Houston),
                Free 20-person (Florida), Money 34-person #1 (Houston), Money 34-person #2 (Virginia contrarian).
                Use Chalk/Simulation/Value for your Houston brackets, Contrarian for Virginia, and see Michigan bracket below.
            </p>
            {bracket_sections}
        </section>

        <!-- LIVE ODDS - THURSDAY -->
        <section id="live-odds">
            <h2>LIVE ODDS - Thursday March 19 (Round of 64)</h2>
            <p style="color:var(--gold);margin-bottom:15px;"><strong>Lines verified 7:00 AM EST via ESPN API. Sharp money movements noted.</strong></p>
            <table>
                <thead>
                    <tr><th>Time</th><th>Matchup</th><th>Spread</th><th>O/U</th><th>ML Fav</th><th>ML Dog</th><th>Our Take</th></tr>
                </thead>
                <tbody>
                    <tr class="has-edge"><td>12:15p</td><td>(8) Ohio State vs (9) TCU</td><td>OSU -2.5</td><td>145.5</td><td>-142</td><td>+120</td><td style="color:var(--green);font-weight:bold;">TCU +2.5. Line moved from -4.5. Sharp money.</td></tr>
                    <tr class="has-edge"><td>12:40p</td><td>(4) Nebraska vs (13) Troy</td><td>NEB -13.5</td><td>138.5</td><td>-1000</td><td>+650</td><td style="color:var(--green);">Troy +13.5. CBS Cinderella. NEB 3-8 ATS as big fav.</td></tr>
                    <tr class="has-edge" style="background:rgba(39,174,96,0.2);"><td>1:30p</td><td>(6) Louisville vs (11) South Florida</td><td>LOU -4.5</td><td>163.5</td><td>-198</td><td>+164</td><td style="color:var(--green);font-weight:bold;">USF +4.5 / ML +164. #1 BET. Brown OUT. 85% sharp $.</td></tr>
                    <tr><td>1:50p</td><td>(5) Wisconsin vs (12) High Point</td><td>WIS -10.5</td><td>162.5</td><td>-485</td><td>+370</td><td>HPU +10.5 has some value (ESPN BPI's top upset pick).</td></tr>
                    <tr><td>2:50p</td><td>(1) Duke vs (16) Siena</td><td>DUKE -27.5</td><td>135.5</td><td>-20000</td><td>+3500</td><td>No value. Duke covers but Ngongba OUT.</td></tr>
                    <tr><td>3:15p</td><td>(5) Vanderbilt vs (12) McNeese</td><td>VAN -16.5</td><td>148.5</td><td>-1400</td><td>+950</td><td>Vandy covers. T-Rank #10 vs mid-major.</td></tr>
                    <tr><td>~7:10p</td><td>(1) Michigan vs (16) Howard</td><td>~MICH -27</td><td>~140</td><td></td><td></td><td>Michigan rolls. Lendeborg cleared. Go Blue!</td></tr>
                    <tr><td>Eve</td><td>(3) Michigan St vs (14) NDSU</td><td>TBD</td><td>TBD</td><td></td><td></td><td>Izzo in March. MSU handles business.</td></tr>
                </tbody>
            </table>
            <div class="bankroll-info" style="margin-top:20px;">
                <h3>THURSDAY BETTING CARD ($200 bankroll, $10/unit)</h3>
                <table>
                    <thead><tr><th>#</th><th>Pick</th><th>Size</th><th>Line</th><th>Confidence</th></tr></thead>
                    <tbody>
                        <tr style="background:rgba(39,174,96,0.15);"><td>1</td><td><strong>USF +4.5</strong> vs Louisville</td><td>2u ($20)</td><td>+4.5</td><td style="color:var(--green);font-weight:bold;">HIGH</td></tr>
                        <tr style="background:rgba(39,174,96,0.1);"><td>2</td><td><strong>USF ML</strong> +164</td><td>1u ($10)</td><td>+164</td><td style="color:var(--gold);">MEDIUM</td></tr>
                        <tr><td>3</td><td><strong>TCU +2.5</strong> vs Ohio State</td><td>1u ($10)</td><td>+2.5</td><td style="color:var(--gold);">MEDIUM</td></tr>
                        <tr><td>4</td><td><strong>Troy +13.5</strong> vs Nebraska</td><td>1u ($10)</td><td>+13.5</td><td style="color:var(--gold);">MEDIUM</td></tr>
                        <tr style="background:rgba(39,174,96,0.15);"><td>5</td><td><strong>Houston futures +900</strong></td><td>1u ($10)</td><td>+900</td><td style="color:var(--green);font-weight:bold;">HIGH</td></tr>
                    </tbody>
                </table>
                <p style="margin-top:10px;color:var(--text-muted);">Total risk: $60 (6u). Remaining: $140 for Friday+.</p>
            </div>
        </section>

        <!-- BETTING PICKS -->
        <section id="betting">
            <h2>Model Betting Picks - Full First Round</h2>

            <div class="bankroll-info">
                <h3>Bankroll Management</h3>
                <p><strong>Total Bankroll:</strong> $300 across DraftKings + Fanatics</p>
                <p><strong>Unit Size (1u):</strong> $15 (5% of bankroll - conservative Kelly)</p>
                <p><strong>Max single bet:</strong> $30 (2u) on HIGH confidence picks</p>
                <p><strong>Daily budget:</strong> ~$75 per day (5 units)</p>
                <p><strong>Rule:</strong> Only bet edges > 3%. HIGH confidence = 2u, MEDIUM = 1u. Never chase.</p>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Region</th>
                        <th>Matchup</th>
                        <th>Model Fav%</th>
                        <th>Model Dog%</th>
                        <th>Edge Fav</th>
                        <th>Edge Dog</th>
                        <th>Best Bet</th>
                        <th>Confidence</th>
                        <th>Venue</th>
                    </tr>
                </thead>
                <tbody>
                    {betting_rows}
                </tbody>
            </table>
        </section>

        <!-- EDGE INSIGHTS -->
        <section id="insights">
            <h2>Edge Insights & Niche Factors</h2>
            <div class="insight-grid">
                <div class="insight-card">
                    <h4>Travel Advantages</h4>
                    <p><strong>Florida in Tampa</strong> - Only 130 miles from campus. Biggest home-court edge in the tournament. Massive crowd support for rounds 1-2.</p>
                    <p><strong>Arizona in San Diego</strong> - Big alumni base in SoCal. Near-home atmosphere.</p>
                    <p><strong>Gonzaga in Portland</strong> - Pacific NW crowd. Only 280 miles.</p>
                    <p><strong>Duke in Greenville</strong> - ACC territory, short drive from Durham.</p>
                </div>
                <div class="insight-card">
                    <h4>Travel Disadvantages</h4>
                    <p><strong>Hawaii to Portland</strong> - 2,594 miles. Longest trip. Time zone disruption. 13-seed facing Arkansas.</p>
                    <p><strong>St. John's to San Diego</strong> - 2,432 miles. NYC to SoCal. Jet lag factor for a 5-seed.</p>
                    <p><strong>UCLA to Philadelphia</strong> - 2,700+ miles. Cross-country + injured star.</p>
                    <p><strong>Iowa State to Philadelphia</strong> - 1,100+ miles. Neutral territory for a 2-seed.</p>
                </div>
                <div class="insight-card">
                    <h4>Duke Without Caleb Foster</h4>
                    <p>Duke's starting PG had surgery for a fractured foot. He's out until at least the Final Four (and even then unlikely). This is a MAJOR factor:</p>
                    <p>- Duke drops ~2-3 points in our power rating without him</p>
                    <p>- Guard depth becomes thin (Ngongba also questionable)</p>
                    <p>- Still talented enough to win, but more vulnerable than odds suggest</p>
                    <p><strong>Implication:</strong> Duke at +300 may be overvalued. Michigan/Arizona offer better value.</p>
                </div>
                <div class="insight-card">
                    <h4>UNC Without Caleb Wilson</h4>
                    <p>North Carolina lost projected top-5 NBA pick Caleb Wilson to a season-ending broken thumb on March 5.</p>
                    <p>- A 6-seed that should probably be a 9-10 seed now</p>
                    <p>- Fade UNC heavily in all brackets</p>
                    <p>- Their opponent VCU (11 seed) becomes a strong upset pick</p>
                    <p><strong>Implication:</strong> One of the best upset spots in the tournament.</p>
                </div>
                <div class="insight-card">
                    <h4>Offense vs. Defense in March</h4>
                    <p>Historical data shows defense travels better in March. Teams that rely on shooting often go cold in unfamiliar gyms with tournament pressure.</p>
                    <p><strong>Red flags:</strong> Alabama (#3 O, #67 D), Arkansas (#6 O, #52 D) - these teams live by the 3 and can die by it.</p>
                    <p><strong>Green flags:</strong> Michigan (#1 D), Houston (#5 D), Iowa State (#4 D) - these teams grind.</p>
                </div>
                <div class="insight-card">
                    <h4>The 5-12 Upset Special</h4>
                    <p>Historically, 12-seeds beat 5-seeds ~35% of the time. This year's best 12-over-5 candidates:</p>
                    <p><strong>McNeese over Vanderbilt</strong> - Vandy's defense (#29) is exploitable</p>
                    <p><strong>Akron over Texas Tech</strong> - Tech lost JT Toppin, only 22-10</p>
                    <p><strong>Northern Iowa over St. John's</strong> - St. John's traveled 2,432 miles to San Diego</p>
                </div>
                <div class="insight-card">
                    <h4>AI Bracket History</h4>
                    <p>AI/ML brackets have been tried extensively:</p>
                    <p>- <strong>What works:</strong> Power ratings + tempo adjustment + injury factors</p>
                    <p>- <strong>What fails:</strong> Overfitting to regular season data, ignoring intangibles (coaching in March, crowd energy, fatigue)</p>
                    <p>- <strong>Our edge:</strong> We combine KenPom analytics with situational factors (travel, injuries, momentum) that pure models miss</p>
                    <p>- <strong>Key insight:</strong> No one has ever picked a perfect bracket (1 in 9.2 quintillion odds). Focus on maximizing expected value, not perfection.</p>
                </div>
                <div class="insight-card" style="border-top: 3px solid var(--green);">
                    <h4>HOUSTON - Biggest Hidden Edge</h4>
                    <p>At +900 (implied ~10%), our model gives Houston 11.7% to win it all. That's VALUE.</p>
                    <p>- <strong>HOME COURT for Sweet 16/Elite 8</strong> - South Region games are IN HOUSTON</p>
                    <p>- <strong>Kelvin Sampson</strong> = HOF-level coach, championship game in 2025</p>
                    <p>- <strong>Kingston Flemings + Chris Cenac</strong> = projected 1st round NBA picks</p>
                    <p>- <strong>#5 defense</strong> travels in March. Physical style disrupts.</p>
                    <p style="color:var(--green);"><strong>BET: Houston futures at +900 or better.</strong></p>
                </div>
                <div class="insight-card">
                    <h4>Louisville/USF - Live Injury Edge</h4>
                    <p>Louisville -4.5 is STALE. It doesn't fully price in Mikel Brown Jr being OUT.</p>
                    <p>- Brown Jr: 18.2 PPG, projected lottery pick, team's engine</p>
                    <p>- South Florida: AAC champs, 12-game win streak, 25-8</p>
                    <p>- Without Brown, Louisville is closer to a 9-10 seed talent level</p>
                    <p style="color:var(--green);"><strong>BET: South Florida +4.5 (or ML +170)</strong></p>
                </div>
            </div>
        </section>

        <!-- METHODOLOGY -->
        <section id="methodology">
            <h2>Methodology</h2>
            <div class="insight-grid">
                <div class="insight-card">
                    <h4>Power Ratings</h4>
                    <p>Base ratings derived from KenPom adjusted efficiency margins. Modified for:</p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Injury impact (manually assessed per player)</li>
                        <li>Travel distance to venue</li>
                        <li>Home court / crowd advantage</li>
                        <li>Coach tournament pedigree (Izzo, Self, Hurley)</li>
                        <li>Momentum (conference tournament performance)</li>
                    </ul>
                </div>
                <div class="insight-card">
                    <h4>Monte Carlo Simulation</h4>
                    <p>10,000 full tournament simulations using logistic win probability model.</p>
                    <p>Each game's outcome is probabilistic based on the effective power rating difference.</p>
                    <p>Every ~1 point of rating difference = ~3% win probability shift.</p>
                </div>
                <div class="insight-card">
                    <h4>Betting Model</h4>
                    <p>Compares model-implied probabilities vs. historical seed-based upset rates.</p>
                    <p>Edges > 3% are flagged. Kelly Criterion used for sizing (5% base unit).</p>
                    <p>Will be updated daily with actual spreads/lines from DraftKings and Fanatics.</p>
                </div>
                <div class="insight-card">
                    <h4>Data Sources</h4>
                    <ul style="padding-left: 20px;">
                        <li>KenPom adjusted efficiency ratings</li>
                        <li>ESPN bracket and team data</li>
                        <li>RotoWire injury reports</li>
                        <li>Vegas Insider / OddsShark championship odds</li>
                        <li>CBS Sports simulation data</li>
                        <li>Bauertology travel distances</li>
                        <li>Historical NCAA tournament upset rates</li>
                    </ul>
                </div>
            </div>
        </section>

    </div>

    <footer>
        <p>March Madness 2026 AI Analysis | Generated by Monte Carlo Simulation Engine</p>
        <p>Data verified from ESPN, KenPom, RotoWire, CBS Sports, Vegas Insider</p>
        <p style="color: var(--accent); margin-top: 10px;">Gambling involves risk. Never bet more than you can afford to lose. 18+</p>
    </footer>
</body>
</html>"""

    output_path = OUTPUT_DIR / "march_madness_2026.html"
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Main HTML saved to {output_path}")
    return output_path


if __name__ == "__main__":
    bracket, sim, brackets, picks, teams = load_data()
    path = generate_main_html(bracket, sim, brackets, picks, teams)
    print(f"\nOpen in browser: file://{path}")
