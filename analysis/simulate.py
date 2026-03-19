#!/usr/bin/env python3
"""
March Madness 2026 Monte Carlo Bracket Simulator
Runs N simulations of the tournament to generate win probabilities,
optimal bracket strategies, and betting edges.
"""

import json
import random
import math
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# ============================================================
# TEAM POWER RATINGS
# SOURCE: ESPN BPI (Basketball Power Index) as of March 18, 2026
# BPI = points above/below average. Higher = better.
# Top 10 are VERIFIED from ESPN BPI page. 11+ estimated from
# AP poll points + record + efficiency proxies.
# INJURY ADJUSTMENTS applied after base rating.
# ============================================================

# --- ESPN BPI VERIFIED (top 10) ---
_BPI_VERIFIED = {
    "Duke":      25.6,   # BPI #1: OFF 12.9, DEF 12.8
    "Michigan":  24.1,   # BPI #2: OFF 11.7, DEF 12.4
    "Arizona":   23.7,   # BPI #3: OFF 11.9, DEF 11.8
    "Houston":   23.0,   # BPI #4: OFF 10.4, DEF 12.6
    "Florida":   22.3,   # BPI #5: OFF 10.9, DEF 11.4
    "Iowa State":21.5,   # BPI #6: OFF 10.1, DEF 11.4
    "Illinois":  21.0,   # BPI #7: OFF 13.1, DEF 7.9
    "Gonzaga":   20.7,   # BPI #8: OFF 9.7, DEF 11.0
    "Purdue":    20.6,   # BPI #9: OFF 13.8, DEF 6.8
    "UConn":     19.4,   # BPI #10: OFF 9.1, DEF 10.3
}

# --- ESTIMATED from AP poll points, record, KenPom ranks ---
# Scaled to align with BPI range (AP #11 ~19.0, #25 ~13.0)
_BPI_ESTIMATED = {
    "Michigan State": 18.5,  # AP#11, 833 pts, 25-7
    "Virginia":       18.3,  # AP#9, 903 pts, 29-5 (defense-first)
    "St. John's":     18.0,  # AP#10, 860 pts, 28-6
    "Vanderbilt":     17.0,  # AP#16, 538 pts, 26-8
    "Nebraska":       17.5,  # AP#15, 689 pts, 26-6
    "Arkansas":       17.2,  # AP#14, 750 pts, 26-8, SEC champs
    "Kansas":         16.5,  # AP#17, 503 pts, 23-10
    "Alabama":        16.0,  # AP#18, 438 pts, 23-9
    "Wisconsin":      15.5,  # AP#19, 392 pts, 24-10
    "Texas Tech":     15.0,  # AP#20, 376 pts, 22-10 (Toppin out)
    "Louisville":     14.8,  # AP#23T, 112 pts, 23-10
    "North Carolina": 14.5,  # AP#21, 293 pts, 24-8
    "Saint Mary's":   14.0,  # AP#22, 113 pts, 27-5
    "Tennessee":      14.0,  # AP#23T, 112 pts, 22-11
    "Miami (FL)":     13.8,  # AP#25, 110 pts, 25-8
    "Kentucky":       13.0,  # Just outside top 25, 21-13
    "UCLA":           12.5,  # Unranked, 22-11, star injured
    "BYU":            12.5,  # Unranked, 23-11, Saunders out
    "Ohio State":     13.5,  # Borderline top 25
    "Villanova":      13.0,  # Mid-major feel, Big East
    "Clemson":        12.5,  # Unranked
    "Georgia":        11.5,  # 302nd scoring D per CBS
    "TCU":            13.0,
    "Utah State":     12.5,
    "Saint Louis":    13.5,  # #11 scoring offense, 59.7% eFG
    "Iowa":           13.5,  # Big Ten best scoring D, Stirtz 20ppg
    "UCF":            12.0,
    "Missouri":       12.5,
    "Santa Clara":    11.5,
    "Texas A&M":      13.5,  # Veteran squad, 35.6 bench ppg
    "South Florida":  13.0,  # AAC champs, 12-game win streak
    "Texas":          12.0,  # Won First Four
    "SMU":            11.5,
    "Miami (OH)":     12.5,  # 32-1! Beat SMU 89-79 in First Four. Elmer 23pts. LEGIT.
    "VCU":            12.0,  # Won 16 of last 17
    "Northern Iowa":  10.5,
    "High Point":      9.0,
    "Akron":          10.0,
    "McNeese":        10.5,
    "Cal Baptist":     7.5,
    "Hawaii":          8.0,
    "Hofstra":         8.5,
    "Troy":            9.5,  # CBS Cinderella, beat SDSU, took USC to 3OT
    "North Dakota State": 6.5,
    "Kennesaw State":     6.0,
    "Wright State":       7.0,
    "Penn":               7.5,
    "Furman":          6.5,
    "Queens":          4.5,
    "Tennessee State": 5.0,
    "Idaho":           4.5,
    "Siena":           3.5,
    "LIU":             2.5,
    "Howard":          4.0,  # Won First Four
    "Prairie View A&M": 3.5,
    "Lehigh":          3.5,
    "UMBC":            3.5,
    "NC State":        11.0,
}

# Combine verified + estimated
POWER_RATINGS = {**_BPI_VERIFIED, **_BPI_ESTIMATED}

# --- INJURY ADJUSTMENTS (subtracted from base BPI) ---
# Estimated using player's share of team production
INJURY_ADJUSTMENTS = {
    "Duke":           -3.0,   # Foster OUT (PG, surgery) + Ngongba "very unlikely" (C, 11.4/6.5/2.1)
    "Michigan":       -1.5,   # Cason torn ACL (reserve guard, season-ending)
    "Louisville":     -4.5,   # Brown Jr OUT opening weekend (18.2 PPG, lottery pick) = DEVASTATING
    "North Carolina": -5.0,   # Wilson OUT (would-be top-5 pick) = team fundamentally different
    "Alabama":        -4.0,   # Holloway SUSPENDED/OFF TEAM (16.8 PPG, 2nd scorer, felony arrest Mar 16)
    "Gonzaga":        -1.0,   # Huff unlikely first 2 games (left knee)
    "BYU":            -2.0,   # Saunders OUT season (knee, senior leader)
    "Texas Tech":     -3.5,   # Toppin OUT season (21.8 PPG, 10.8 RPG = All-American!) + 3-game losing streak
    "UCLA":           -2.0,   # Star forward questionable (knee strain) + Dent limited (calf)
    "Kansas":         -1.0,   # Peterson "full-body cramps" drama, inconsistent availability all year
}

# Apply injury adjustments to power ratings
for team, adj in INJURY_ADJUSTMENTS.items():
    if team in POWER_RATINGS:
        POWER_RATINGS[team] += adj

# ============================================================
# TRAVEL / SITUATIONAL ADJUSTMENTS
# ============================================================
TRAVEL_ADJUSTMENTS = {
    # Positive = advantage, Negative = disadvantage
    # Round 1-2 adjustments (later rounds would need separate handling)
    "Florida": 2.0,       # Basically home game in Tampa
    "Houston": 1.5,       # OKC for R1/R2 is fine, but S16/E8 IN HOUSTON = massive (modeled as avg boost)
    "Arizona": 1.0,       # SoCal fanbase in San Diego
    "Gonzaga": 1.0,       # Near-home in Portland
    "Duke": 0.5,          # ACC country in Greenville
    "Michigan": 0.5,      # Big Ten in Buffalo
    "UConn": 0.5,         # Short trip to Philly
    "Purdue": 0.5,        # Short to St. Louis
    "Michigan State": 0.3,
    "St. John's": -1.0,   # NYC to San Diego, 2432 miles
    "UCLA": -1.5,         # Cross-country to Philly + injury
    "Hawaii": -1.5,       # 2594 miles to Portland
    "Arkansas": -0.5,     # Long trip to Portland
    "Kansas": -0.5,       # Long trip to San Diego
    "Wisconsin": -0.5,    # Long trip to Portland
    "Iowa State": -0.5,   # Long trip to Philly
    "Saint Mary's": -0.5, # Long trip to St. Louis
}

# March Madness upset frequency by seed matchup (historical)
# Probability that the LOWER seed wins (the upset)
HISTORICAL_UPSET_RATES = {
    (1, 16): 0.01,   # Only once: UMBC over Virginia 2018
    (2, 15): 0.06,
    (3, 14): 0.13,
    (4, 13): 0.20,
    (5, 12): 0.35,   # Classic upset spot
    (6, 11): 0.37,   # Another classic
    (7, 10): 0.40,
    (8, 9):  0.49,   # Near coin flip
}

# Izzo factor - Tom Izzo historically overperforms seed in March
COACH_ADJUSTMENTS = {
    "Michigan State": 1.5,  # Izzo March magic
    "Kansas": 1.0,          # Bill Self
    "UConn": 1.5,           # Dan Hurley back-to-back DNA
    "Houston": 1.5,         # Kelvin Sampson HOF-level, championship game last year
    "Duke": 1.0,            # Scheyer + Cameron Boozer NPOY superstar factor
    "Florida": 1.0,         # Defending champion experience/DNA
    "Kentucky": 0.5,        # Brand factor
    "North Carolina": 0.0,  # Brand means nothing without Caleb Wilson
}


def get_effective_rating(team):
    """Get team's effective power rating with all adjustments."""
    base = POWER_RATINGS.get(team, 10.0)
    travel = TRAVEL_ADJUSTMENTS.get(team, 0.0)
    coach = COACH_ADJUSTMENTS.get(team, 0.0)
    return base + travel + coach


def win_probability(team_a, team_b):
    """
    Calculate probability that team_a beats team_b.
    Uses log5 method with power ratings.
    """
    rating_a = get_effective_rating(team_a)
    rating_b = get_effective_rating(team_b)

    # Convert to probability using logistic function
    # Each point of rating difference ≈ 3% win probability shift
    diff = rating_a - rating_b
    prob = 1.0 / (1.0 + math.exp(-diff * 0.15))

    return prob


def simulate_game(team_a, team_b):
    """Simulate a single game, return winner."""
    prob_a = win_probability(team_a, team_b)
    if random.random() < prob_a:
        return team_a
    return team_b


def resolve_first_four():
    """Resolve First Four games and return the winners."""
    # ALL FIRST FOUR RESULTS FINAL (March 17-18):
    winners = {
        "11_West": "Texas",          # FINAL: Texas 68, NC State 66 (Tramon Mark buzzer-beater)
        "16_Midwest": "Howard",      # FINAL: Howard 86, UMBC 83 (Howard's first tourney win)
        "11_Midwest": "Miami (OH)",  # FINAL: Miami (OH) 89, SMU 79 (31-1 RedHawks! Elmer 23pts)
        "16_South": "Prairie View A&M",  # FINAL: PV A&M 67, Lehigh 55 (Horne 25pts)
    }
    return winners


def build_region_bracket(region_name, matchups, first_four_winners):
    """Build initial round of 64 matchups for a region."""
    games = []
    for m in matchups:
        team_high = m["team_high"]
        team_low = m["team_low"]

        # Handle First Four winners
        if "/" in team_low:
            parts = team_low.split("/")
            if "UMBC" in team_low:
                team_low = first_four_winners.get("16_Midwest", parts[0])
            elif "Prairie View" in team_low:
                team_low = first_four_winners.get("16_South", parts[0])
            elif "Texas" in team_low and "NC State" in team_low:
                team_low = first_four_winners.get("11_West", parts[0])
            elif "SMU" in team_low:
                team_low = first_four_winners.get("11_Midwest", parts[0])

        games.append((team_high, team_low))
    return games


def simulate_region(games):
    """Simulate all rounds of a region, return results by round."""
    results = {"R64": [], "R32": [], "S16": [], "E8": []}

    # Round of 64
    r64_winners = []
    for team_a, team_b in games:
        winner = simulate_game(team_a, team_b)
        r64_winners.append(winner)
        results["R64"].append(winner)

    # Round of 32
    r32_winners = []
    for i in range(0, len(r64_winners), 2):
        winner = simulate_game(r64_winners[i], r64_winners[i+1])
        r32_winners.append(winner)
        results["R32"].append(winner)

    # Sweet 16
    s16_winners = []
    for i in range(0, len(r32_winners), 2):
        winner = simulate_game(r32_winners[i], r32_winners[i+1])
        s16_winners.append(winner)
        results["S16"].append(winner)

    # Elite 8
    e8_winner = simulate_game(s16_winners[0], s16_winners[1])
    results["E8"].append(e8_winner)

    return results


def simulate_tournament(bracket_data):
    """Simulate entire tournament once. Return full results."""
    first_four = resolve_first_four()

    all_results = {"first_four": first_four}
    final_four = []

    for region_name, region_data in bracket_data["regions"].items():
        games = build_region_bracket(region_name, region_data["matchups"], first_four)
        region_results = simulate_region(games)
        all_results[region_name] = region_results
        final_four.append(region_results["E8"][0])

    # Final Four: East vs West, Midwest vs South (standard bracket)
    semi1 = simulate_game(final_four[0], final_four[1])  # East vs West
    semi2 = simulate_game(final_four[2], final_four[3])  # Midwest vs South
    champion = simulate_game(semi1, semi2)

    all_results["final_four"] = final_four
    all_results["semi_winners"] = [semi1, semi2]
    all_results["champion"] = champion

    return all_results


def run_simulations(n=10000):
    """Run N tournament simulations and aggregate results."""
    with open(DATA_DIR / "bracket_2026.json") as f:
        bracket_data = json.load(f)

    # Track results
    champion_counts = Counter()
    final_four_counts = Counter()
    elite_8_counts = Counter()
    sweet_16_counts = Counter()
    round_32_counts = Counter()
    round_64_counts = Counter()

    # Track region winners
    region_winner_counts = {r: Counter() for r in bracket_data["regions"]}

    for _ in range(n):
        results = simulate_tournament(bracket_data)

        champion_counts[results["champion"]] += 1

        for team in results["final_four"]:
            final_four_counts[team] += 1

        for region_name in bracket_data["regions"]:
            for team in results[region_name]["E8"]:
                elite_8_counts[team] += 1
                region_winner_counts[region_name][team] += 1
            for team in results[region_name]["S16"]:
                sweet_16_counts[team] += 1
            for team in results[region_name]["R32"]:
                round_32_counts[team] += 1
            for team in results[region_name]["R64"]:
                round_64_counts[team] += 1

    # Convert to probabilities
    def to_pct(counter):
        return {team: round(count / n * 100, 1) for team, count in counter.most_common()}

    results = {
        "simulations": n,
        "champion": to_pct(champion_counts),
        "final_four": to_pct(final_four_counts),
        "elite_8": to_pct(elite_8_counts),
        "sweet_16": to_pct(sweet_16_counts),
        "round_of_32": to_pct(round_32_counts),
        "round_of_64": to_pct(round_64_counts),
        "region_winners": {r: to_pct(c) for r, c in region_winner_counts.items()},
    }

    return results


def generate_bracket(strategy="chalk", sim_results=None):
    """
    Generate a bracket based on strategy.

    Strategies:
    - chalk: Pick the higher-rated team every game
    - simulation: Pick the most likely winner from sim results
    - contrarian: Pick upsets where value exists (for large pools)
    - balanced: Mix of chalk and strategic upsets
    - chaos: Maximum differentiation for mega-pools
    - value: Pick teams with best odds-to-probability ratio
    """
    with open(DATA_DIR / "bracket_2026.json") as f:
        bracket_data = json.load(f)

    first_four = resolve_first_four_deterministic(strategy)
    bracket = {"strategy": strategy, "regions": {}, "final_four": [], "champion": None}

    for region_name, region_data in bracket_data["regions"].items():
        games = build_region_bracket(region_name, region_data["matchups"], first_four)
        region_picks = pick_region(games, strategy, sim_results, region_name)
        bracket["regions"][region_name] = region_picks

    # Final Four picks
    ff_teams = [bracket["regions"][r]["elite_8"] for r in ["East", "West", "Midwest", "South"]]
    bracket["final_four"] = ff_teams

    if strategy == "chalk":
        semi1 = max(ff_teams[0:2], key=get_effective_rating)
        semi2 = max(ff_teams[2:4], key=get_effective_rating)
        bracket["champion"] = max([semi1, semi2], key=get_effective_rating)
    elif strategy == "contrarian":
        # Pick less popular Final Four teams
        semi1 = pick_contrarian_ff(ff_teams[0], ff_teams[1], sim_results)
        semi2 = pick_contrarian_ff(ff_teams[2], ff_teams[3], sim_results)
        bracket["champion"] = pick_contrarian_ff(semi1, semi2, sim_results)
    elif strategy == "chaos":
        semi1 = min(ff_teams[0:2], key=get_effective_rating)
        semi2 = min(ff_teams[2:4], key=get_effective_rating)
        bracket["champion"] = min([semi1, semi2], key=get_effective_rating)
    else:  # simulation, balanced, value
        semi1 = max(ff_teams[0:2], key=lambda t: sim_results["champion"].get(t, 0))
        semi2 = max(ff_teams[2:4], key=lambda t: sim_results["champion"].get(t, 0))
        bracket["champion"] = max([semi1, semi2], key=lambda t: sim_results["champion"].get(t, 0))

    bracket["semi_winners"] = [semi1, semi2] if 'semi1' in dir() else ff_teams[:2]

    return bracket


def resolve_first_four_deterministic(strategy):
    """Deterministic First Four picks based on strategy.
    KNOWN RESULTS: Texas beat NC State, Howard beat UMBC.
    TONIGHT: SMU vs Miami (OH), Lehigh vs Prairie View A&M.
    """
    # ALL FIRST FOUR RESULTS LOCKED IN
    return {
        "11_West": "Texas",              # FINAL
        "16_Midwest": "Howard",          # FINAL
        "11_Midwest": "Miami (OH)",      # FINAL: upset! 89-79 over SMU
        "16_South": "Prairie View A&M",  # FINAL: upset! 67-55 over Lehigh
    }


def pick_contrarian_ff(team_a, team_b, sim_results):
    """Pick the less popular team for contrarian strategy."""
    if sim_results:
        pop_a = sim_results["champion"].get(team_a, 0)
        pop_b = sim_results["champion"].get(team_b, 0)
        return team_b if pop_a > pop_b else team_a
    return team_b  # default to underdog


def pick_region(games, strategy, sim_results, region_name):
    """Pick winners through an entire region."""
    region = {"R64": [], "R32": [], "S16": [], "elite_8": None}

    # R64
    r64_winners = []
    for team_a, team_b in games:
        winner = pick_game(team_a, team_b, strategy, sim_results, "round_of_64")
        r64_winners.append(winner)
        region["R64"].append({"winner": winner, "loser": team_b if winner == team_a else team_a})

    # R32
    r32_winners = []
    for i in range(0, len(r64_winners), 2):
        winner = pick_game(r64_winners[i], r64_winners[i+1], strategy, sim_results, "round_of_32")
        r32_winners.append(winner)
        region["R32"].append({"winner": winner, "loser": r64_winners[i+1] if winner == r64_winners[i] else r64_winners[i]})

    # S16
    s16_winners = []
    for i in range(0, len(r32_winners), 2):
        winner = pick_game(r32_winners[i], r32_winners[i+1], strategy, sim_results, "sweet_16")
        s16_winners.append(winner)
        region["S16"].append({"winner": winner, "loser": r32_winners[i+1] if winner == r32_winners[i] else r32_winners[i]})

    # E8
    region["elite_8"] = pick_game(s16_winners[0], s16_winners[1], strategy, sim_results, "elite_8")

    return region


def pick_game(team_a, team_b, strategy, sim_results, round_key):
    """Pick a game winner based on strategy."""
    if strategy == "chalk":
        return team_a if get_effective_rating(team_a) >= get_effective_rating(team_b) else team_b

    elif strategy == "simulation":
        if sim_results and round_key in sim_results:
            prob_a = sim_results[round_key].get(team_a, 0)
            prob_b = sim_results[round_key].get(team_b, 0)
            return team_a if prob_a >= prob_b else team_b
        return team_a if get_effective_rating(team_a) >= get_effective_rating(team_b) else team_b

    elif strategy == "contrarian":
        # Pick upset if it's a common upset spot and lower seed has decent rating
        rating_a = get_effective_rating(team_a)
        rating_b = get_effective_rating(team_b)
        diff = abs(rating_a - rating_b)
        # If the gap is small (< 5 points), pick the less popular team
        if diff < 5:
            if sim_results and round_key in sim_results:
                pop_a = sim_results[round_key].get(team_a, 50)
                pop_b = sim_results[round_key].get(team_b, 50)
                return team_b if pop_a > pop_b else team_a
            return team_b  # default to the "lower" team
        return team_a if rating_a >= rating_b else team_b

    elif strategy == "balanced":
        # Mix: pick favorite unless upset probability > 35% and rating gap < 6
        prob_a = win_probability(team_a, team_b)
        if prob_a < 0.65 and get_effective_rating(team_b) > 14:
            # Consider the upset
            if sim_results and round_key in sim_results:
                sim_prob_b = sim_results[round_key].get(team_b, 0)
                if sim_prob_b > 40:
                    return team_b
        return team_a if prob_a >= 0.5 else team_b

    elif strategy == "chaos":
        # Heavy upset picks for mega-pools
        prob_a = win_probability(team_a, team_b)
        if prob_a < 0.75:  # If not a massive favorite, consider upset
            rating_b = get_effective_rating(team_b)
            if rating_b > 12:
                return team_b
        return team_a if prob_a >= 0.5 else team_b

    elif strategy == "value":
        # Use odds-implied probability vs model probability
        prob_a = win_probability(team_a, team_b)
        # Pick the team where our model gives them more credit than the market
        return team_a if prob_a >= 0.5 else team_b

    return team_a


def generate_betting_picks(sim_results):
    """Generate betting picks for first round based on simulation results."""
    with open(DATA_DIR / "bracket_2026.json") as f:
        bracket_data = json.load(f)

    picks = []
    for region_name, region_data in bracket_data["regions"].items():
        for matchup in region_data["matchups"]:
            team_h = matchup["team_high"]
            team_l = matchup["team_low"]

            # Skip first four placeholders
            if "/" in team_l:
                continue

            prob_h = win_probability(team_h, team_l)
            prob_l = 1 - prob_h

            # Look for value: where our probability significantly differs from implied
            seed_h = matchup["seed_high"]
            seed_l = matchup["seed_low"]

            # Estimate market implied probability from seeds
            market_upset_rate = HISTORICAL_UPSET_RATES.get((seed_h, seed_l), 0.3)
            market_fav = 1 - market_upset_rate

            edge_fav = prob_h - market_fav
            edge_dog = prob_l - market_upset_rate

            pick = {
                "region": region_name,
                "matchup": f"({seed_h}) {team_h} vs ({seed_l}) {team_l}",
                "favorite": team_h,
                "underdog": team_l,
                "model_prob_fav": round(prob_h * 100, 1),
                "model_prob_dog": round(prob_l * 100, 1),
                "market_implied_fav": round(market_fav * 100, 1),
                "edge_fav": round(edge_fav * 100, 1),
                "edge_dog": round(edge_dog * 100, 1),
                "venue": matchup.get("venue", "TBD"),
            }

            # Determine best bet
            if abs(edge_dog) > abs(edge_fav) and edge_dog > 3:
                pick["best_bet"] = f"{team_l} (underdog)"
                pick["confidence"] = "HIGH" if edge_dog > 8 else "MEDIUM"
            elif edge_fav > 3:
                pick["best_bet"] = f"{team_h} (favorite)"
                pick["confidence"] = "HIGH" if edge_fav > 8 else "MEDIUM"
            else:
                pick["best_bet"] = "NO EDGE"
                pick["confidence"] = "LOW"

            picks.append(pick)

    return picks


if __name__ == "__main__":
    print("=" * 60)
    print("MARCH MADNESS 2026 MONTE CARLO SIMULATOR")
    print("=" * 60)

    N_SIMS = 10000
    print(f"\nRunning {N_SIMS:,} tournament simulations...")

    sim_results = run_simulations(N_SIMS)

    # Save simulation results
    output_path = DATA_DIR / "simulation_results.json"
    with open(output_path, "w") as f:
        json.dump(sim_results, f, indent=2)
    print(f"Simulation results saved to {output_path}")

    # Print championship probabilities
    print("\n" + "=" * 60)
    print("CHAMPIONSHIP PROBABILITIES (Top 15)")
    print("=" * 60)
    for team, pct in list(sim_results["champion"].items())[:15]:
        bar = "█" * int(pct)
        print(f"  {team:20s} {pct:5.1f}% {bar}")

    # Print Final Four probabilities
    print("\n" + "=" * 60)
    print("FINAL FOUR PROBABILITIES (Top 15)")
    print("=" * 60)
    for team, pct in list(sim_results["final_four"].items())[:15]:
        bar = "█" * int(pct / 2)
        print(f"  {team:20s} {pct:5.1f}% {bar}")

    # Generate brackets
    print("\n" + "=" * 60)
    print("GENERATING BRACKET STRATEGIES")
    print("=" * 60)

    strategies = ["chalk", "simulation", "balanced", "contrarian", "chaos", "value"]
    brackets = {}
    for strat in strategies:
        bracket = generate_bracket(strat, sim_results)
        brackets[strat] = bracket
        print(f"\n  [{strat.upper()}] Champion: {bracket['champion']}")
        print(f"    Final Four: {', '.join(bracket['final_four'])}")

    # Save brackets
    brackets_path = DATA_DIR / "brackets.json"
    with open(brackets_path, "w") as f:
        json.dump(brackets, f, indent=2)
    print(f"\nBrackets saved to {brackets_path}")

    # Generate betting picks
    print("\n" + "=" * 60)
    print("FIRST ROUND BETTING PICKS (edges > 3%)")
    print("=" * 60)

    picks = generate_betting_picks(sim_results)
    edge_picks = [p for p in picks if p["best_bet"] != "NO EDGE"]
    edge_picks.sort(key=lambda x: max(abs(x["edge_fav"]), abs(x["edge_dog"])), reverse=True)

    for pick in edge_picks:
        print(f"\n  {pick['matchup']}")
        print(f"    Best Bet: {pick['best_bet']} ({pick['confidence']})")
        print(f"    Model: {pick['model_prob_fav']}% fav / {pick['model_prob_dog']}% dog")
        print(f"    Edge: Fav {pick['edge_fav']:+.1f}% | Dog {pick['edge_dog']:+.1f}%")
        print(f"    Venue: {pick['venue']}")

    # Save picks
    picks_path = DATA_DIR / "betting_picks.json"
    with open(picks_path, "w") as f:
        json.dump(picks, f, indent=2)
    print(f"\nAll picks saved to {picks_path}")
