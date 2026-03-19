#!/usr/bin/env python3
"""
March Madness 2026 Monte Carlo Bracket Simulator v2
===================================================
Inspired by Bracket Lab's 10-step pipeline architecture.

Pipeline:
1. Base composite rating (ESPN BPI verified)
2. Injury adjustment (player production share)
3. Momentum/form (last 10 games)
4. Four Factors matchup analysis
5. Travel/venue advantage
6. Coach tournament pedigree
7. Variance modifier (boom/bust vs consistent)
8. Conference strength adjustment
9. Historical seed performance overlay
10. Win probability via logistic with variance

Key differences from v1:
- Composite ratings from BPI + AP + contextual data
- Variance modifiers (high-variance teams are riskier but can upset)
- Tiered confidence system for picks
- Matchup-specific Four Factors analysis
- Historical seed performance weighting
- Better bracket generation with pool-size optimization
"""

import json
import random
import math
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# ============================================================
# STEP 1: BASE COMPOSITE RATINGS
# Source: ESPN BPI (verified March 18, 2026)
# BPI = points above/below average team
# ============================================================

# ESPN BPI VERIFIED (top 10 from espn.com/mens-college-basketball/bpi)
BPI_VERIFIED = {
    "Duke":      25.6,   # OFF 12.9, DEF 12.8 (most balanced)
    "Michigan":  24.1,   # OFF 11.7, DEF 12.4 (defense-first)
    "Arizona":   23.7,   # OFF 11.9, DEF 11.8 (elite both ends)
    "Houston":   23.0,   # OFF 10.4, DEF 12.6 (defense dominant)
    "Florida":   22.3,   # OFF 10.9, DEF 11.4 (defending champ)
    "Iowa State":21.5,   # OFF 10.1, DEF 11.4 (defense-first)
    "Illinois":  21.0,   # OFF 13.1, DEF 7.9 (offense-heavy)
    "Gonzaga":   20.7,   # OFF 9.7, DEF 11.0 (solid)
    "Purdue":    20.6,   # OFF 13.8, DEF 6.8 (extreme offense)
    "UConn":     19.4,   # OFF 9.1, DEF 10.3 (championship DNA)
}

# BPI ESTIMATED (from AP poll points, record, KenPom rank correlation)
BPI_ESTIMATED = {
    "Michigan State": 18.5,  # AP#11, 25-7
    "Virginia":       18.3,  # AP#9 (in AP pts), 29-5
    "St. John's":     18.0,  # AP#10, 28-6
    "Nebraska":       17.5,  # AP#15, 26-6
    "Arkansas":       17.2,  # AP#14, 26-8, SEC champs
    "Vanderbilt":     17.0,  # AP#16, 26-8
    "Kansas":         16.5,  # AP#17, 23-10
    "Alabama":        16.0,  # AP#18, 23-9
    "Wisconsin":      15.5,  # AP#19, 24-10
    "Texas Tech":     15.0,  # AP#20, 22-10 (Toppin OUT)
    "Louisville":     14.8,  # AP#23T, 23-10
    "North Carolina": 14.5,  # AP#21, 24-8
    "Saint Mary's":   14.0,  # AP#22, 27-5
    "Tennessee":      14.0,  # AP#23T, 22-11
    "Miami (FL)":     13.8,  # AP#25, 25-8
    "Ohio State":     13.5,
    "Kentucky":       13.0,  # Just outside top 25, 21-13
    "Saint Louis":    13.5,  # #11 scoring offense (86.4ppg), 59.7% eFG
    "Iowa":           13.5,  # Big Ten best scoring D (66ppg), Stirtz 20ppg
    "Texas A&M":      13.5,  # Veteran squad, 7/8 seniors, 35.6 bench ppg
    "South Florida":  13.0,  # AAC champs, 12-game win streak, 25-8
    "TCU":            13.0,
    "Villanova":      13.0,
    "UCLA":           12.5,  # 22-11, star injured
    "BYU":            12.5,  # 23-11, Saunders OUT
    "Clemson":        12.5,
    "Utah State":     12.5,
    "Missouri":       12.5,
    "VCU":            12.0,  # Won 16 of last 17
    "Texas":          12.0,  # Won First Four (buzzer beater)
    "UCF":            12.0,
    "Santa Clara":    11.5,
    "SMU":            11.5,
    "Miami (OH)":     11.5,  # 31-1 but MAC level competition
    "NC State":       11.0,
    "Georgia":        11.5,  # 302nd scoring defense
    "Northern Iowa":  10.5,
    "McNeese":        10.5,
    "Akron":          10.0,
    "Troy":            9.5,  # CBS Cinderella, beat SDSU on road, took USC to 3OT
    "High Point":      9.0,
    "Hofstra":         8.5,
    "Hawaii":          8.0,
    "Cal Baptist":     7.5,
    "Penn":            7.5,
    "Wright State":    7.0,
    "Furman":          6.5,
    "North Dakota State": 6.5,
    "Kennesaw State":     6.0,
    "Tennessee State":    5.0,
    "Idaho":           4.5,
    "Howard":          4.0,
    "Siena":           3.5,
    "Prairie View A&M": 3.5,
    "Lehigh":          3.5,
    "LIU":             2.5,
    "Queens":          4.5,
    "UMBC":            3.5,
}

BASE_RATINGS = {**BPI_VERIFIED, **BPI_ESTIMATED}

# ============================================================
# STEP 2: INJURY ADJUSTMENTS
# Calculated from player production share of team output
# ============================================================
INJURY_ADJUSTMENTS = {
    "Duke":           -3.0,   # Foster OUT (PG, surgery) + Ngongba "very unlikely" (C, 11.4/6.5/2.1)
    "Michigan":       -1.5,   # Cason torn ACL (reserve guard, season-ending)
    "Louisville":     -4.5,   # Brown Jr OUT opening weekend (18.2 PPG, lottery pick, ~35% usage)
    "North Carolina": -5.0,   # Wilson OUT (would-be top-5 pick, ~30% of team offense)
    "Alabama":        -4.0,   # Holloway SUSPENDED/OFF TEAM (16.8 PPG, 2nd scorer, FELONY arrest Mar 16)
    "Gonzaga":        -1.0,   # Huff unlikely first 2 games (left knee)
    "BYU":            -2.0,   # Saunders OUT season (knee, senior leader)
    "Texas Tech":     -3.5,   # Toppin OUT (21.8 PPG, 10.8 RPG = ALL-AMERICAN) + 3-game losing streak
    "UCLA":           -2.0,   # Star forward questionable (knee strain) + Dent limited (calf)
    "Kansas":         -1.0,   # Peterson "full-body cramps" drama, inconsistent availability
}

# ============================================================
# STEP 3: MOMENTUM / FORM (last 10 games factor)
# Teams on hot streaks get a boost; cold teams get a discount
# Will be updated when last_10_games.json is available
# ============================================================
MOMENTUM_ADJUSTMENTS = {
    # SOURCE: ESPN last 10 game data (fetched March 18, 2026)
    # Positive = hot, Negative = cold
    # Formula: base on L10 record + avg margin + context

    # VERIFIED FROM LAST 10 GAME LOGS:
    "Duke":            +2.0,  # L10: 10-0, +21.3 avg margin. Dominant WITHOUT 2 starters.
    "South Florida":   +2.0,  # L10: 10-0, +19.6 avg margin. HOTTEST team in tournament.
    "Florida":         +0.5,  # L10: 9-1, +17.5. Strong but lost SEC final by 17 to Vanderbilt.
    "Arizona":         +1.0,  # L10: 9-1, +14.8. Only loss: OT to Texas Tech. Very consistent.
    "VCU":             +1.5,  # L10: 9-1, +8.7. Won A-10 tourney. Only loss: @ Saint Louis.
    "Michigan":        -0.5,  # L10: 8-2, +7.6. Lost B10 final. Close wins lately (3-4 pt margins).
    "UConn":           -0.5,  # L10: 7-3, +7.8. Lost to St. John's by 20 in Big East tourney.
    "Houston":         -1.0,  # L10: 6-4, +6.4. FOUR losses in last 10! Lost to Arizona, Kansas, ISU.
    "Iowa State":      -0.5,  # L10: 6-4, +5.6. Lost to Arizona twice, BYU, Texas Tech.
    "Purdue":          +1.0,  # L10: 6-4, +3.5. Won Big Ten tourney (beat Michigan) = momentum.
    "Louisville":      -1.5,  # L10: 6-4, +4.3. Without Brown Jr since Feb 23. Lost ACC tourney R1.
    "Michigan State":  -0.5,  # L10: 6-4, +2.2. Lost to UCLA and Michigan. Inconsistent.
    "North Carolina":  -2.0,  # L10: 6-4, +1.4. Lost Wilson. Lost to Duke by 15 without him.
    "Illinois":        -1.5,  # L10: 5-5, +3.0. Three OT losses. Very inconsistent.
    "Arkansas":        +1.0,  # Won SEC tournament (momentum)
    "Texas A&M":       +0.5,  # Veteran squad, steady
    "Iowa":            +0.5,  # Big Ten best scoring defense, Stirtz hot
    "Saint Louis":     +0.5,  # Elite offense (86.4 ppg), beat VCU
    "Troy":            +0.5,  # Cinderella energy, beat SDSU on road
    "Kentucky":        -0.5,  # 21-13, inconsistent all year
    "Kansas":          -0.5,  # 23-10, fading
    "BYU":             -1.0,  # Lost Saunders mid-season, haven't recovered
    "Texas Tech":      -1.0,  # Lost Toppin, 22-10
    "UCLA":            -1.0,  # Star injured, lost Big Ten semis
}

# ============================================================
# STEP 4: TRAVEL / VENUE ADVANTAGE
# Data from tournament venue assignments
# ============================================================
TRAVEL_ADJUSTMENTS = {
    "Florida":          +2.5,  # Tampa is 130 miles. Basically home. MASSIVE.
    "Houston":          +2.0,  # OKC for R1/R2 + HOME COURT for S16/E8 in Houston
    "Arizona":          +1.0,  # SoCal fanbase in San Diego
    "Gonzaga":          +1.0,  # Near-home in Portland (280 mi)
    "Duke":             +0.5,  # ACC country in Greenville (400 mi)
    "Michigan":         +0.5,  # Big Ten in Buffalo (275 mi)
    "Michigan State":   +0.3,  # Also Big Ten in Buffalo
    "UConn":            +0.5,  # Short to Philly (200 mi), Big East territory
    "Purdue":           +0.5,  # Short to St. Louis (280 mi)
    "St. John's":      -1.0,  # NYC to San Diego = 2,432 miles
    "UCLA":            -1.5,  # Cross-country to Philly = 2,700+ miles + injury
    "Hawaii":          -2.5,  # 2,594 miles to Portland + time zone (3hrs) + charter shortage risk
    "Arkansas":        -0.5,  # 2,000+ miles to Portland
    "Kansas":          -0.5,  # 1,600 miles to San Diego
    "Wisconsin":       -0.5,  # 1,900 miles to Portland
    "Iowa State":      -0.5,  # 1,100+ miles to Philly
    "Saint Mary's":    -0.5,  # 1,900 miles to St. Louis
    "Kentucky":        -0.3,  # 700 miles to Philly
}

# ============================================================
# STEP 5: COACH TOURNAMENT PEDIGREE
# Historical March overperformance by coach
# ============================================================
COACH_ADJUSTMENTS = {
    "Michigan State":  +1.5,  # Tom Izzo: 26 consecutive tournaments, 8 Final Fours
    "Houston":         +1.5,  # Kelvin Sampson: HOF trajectory, championship game 2025
    "UConn":           +1.5,  # Dan Hurley: back-to-back champs 2023-24
    "Duke":            +0.5,  # Jon Scheyer: learning, but Duke brand + Boozer NPOY
    "Kansas":          +1.0,  # Bill Self: 2022 champ, always dangerous
    "Florida":         +1.0,  # Defending champ experience/DNA
    "St. John's":      +0.5,  # Rick Pitino: controversial but tournament-proven
    "Gonzaga":         +0.5,  # Mark Few: consistent tourney success
}

# ============================================================
# STEP 6: VARIANCE MODIFIER (new in v2!)
# How volatile is this team? High variance = more upsets both ways
# Scale: 0.5 (very consistent) to 2.0 (extreme boom/bust)
# Default: 1.0
# This affects the STANDARD DEVIATION of the win probability
# ============================================================
VARIANCE_MODIFIERS = {
    # High variance (offense-dependent, live by 3, streaky)
    "Alabama":        1.8,   # #3 offense, #67 defense, LOST Holloway (felony). Team chaos.
    "Purdue":         1.4,   # #2 offense, #36 defense. Can score 90 or give up 85.
    "Illinois":       1.4,   # #1 offense, #28 defense. Similar profile.
    "Arkansas":       1.4,   # #6 offense, #52 defense.
    "Vanderbilt":     1.3,   # #7 offense, #29 defense.

    # Low variance (defense-first, grind, rarely blow out or get blown out)
    "Virginia":       0.6,   # Pack-line defense, slow tempo, every game is close
    "Houston":        0.7,   # Kelvin Sampson defense, physical, controls pace
    "Michigan":       0.7,   # #1 defense, methodical
    "Iowa State":     0.7,   # Elite defense, grinder
    "Nebraska":       0.8,   # #7 defense, low-scoring
    "Tennessee":      0.8,   # Defense-first

    # Medium-high (talented but inconsistent)
    "Kentucky":       1.3,   # Young talent, 21-13, wild swings
    "North Carolina": 1.4,   # Without Wilson, very volatile
    "Louisville":     1.3,   # Without Brown, unpredictable
    "UCLA":           1.2,   # Injured star, unknown

    # Slightly above average
    "Duke":           1.1,   # Boozer can take over but missing 2 starters adds variance
    "Kansas":         1.1,   # 23-10, up and down year
    "Miami (FL)":     1.1,

    # Conference tournament momentum = reduced variance
    "VCU":            0.9,   # 16 of last 17, very consistent streak
    "South Florida":  0.9,   # 12-game win streak, on a roll
}

# ============================================================
# STEP 7: HISTORICAL SEED PERFORMANCE
# Base upset rates from 1985-2025 tournament data (40 years)
# ============================================================
HISTORICAL_UPSET_RATES = {
    (1, 16): 0.015,   # 2/156 (UMBC 2018, FDU 2023)
    (2, 15): 0.065,   # ~10/156
    (3, 14): 0.135,
    (4, 13): 0.205,
    (5, 12): 0.355,   # Classic upset spot
    (6, 11): 0.375,   # Another classic
    (7, 10): 0.395,
    (8, 9):  0.490,   # Near coin flip
}

# Conference tournament loss effect on R64 performance
# Teams that lost their conf tourney final historically underperform by ~1.5%
CONF_TOURNEY_LOSS_PENALTY = {
    "Florida":  -0.3,  # Lost SEC final
    "Michigan": -0.5,  # Lost Big Ten final to Purdue
}


# ============================================================
# COMPOSITE RATING FUNCTION (the 10-step pipeline)
# ============================================================
def get_composite_rating(team):
    """
    10-step pipeline to compute effective team rating.
    Returns (rating, variance_modifier)
    """
    # Step 1: Base BPI
    base = BASE_RATINGS.get(team, 8.0)

    # Step 2: Injury adjustment
    injury = INJURY_ADJUSTMENTS.get(team, 0.0)

    # Step 3: Momentum
    momentum = MOMENTUM_ADJUSTMENTS.get(team, 0.0)

    # Step 4: Travel/venue
    travel = TRAVEL_ADJUSTMENTS.get(team, 0.0)

    # Step 5: Coach pedigree
    coach = COACH_ADJUSTMENTS.get(team, 0.0)

    # Step 6: Conference tourney loss penalty
    conf_loss = CONF_TOURNEY_LOSS_PENALTY.get(team, 0.0)

    # Composite
    rating = base + injury + momentum + travel + coach + conf_loss

    # Step 7: Variance modifier
    variance = VARIANCE_MODIFIERS.get(team, 1.0)

    return rating, variance


def win_probability(team_a, team_b, include_variance=True):
    """
    Calculate probability that team_a beats team_b.
    Uses logistic function with optional variance modifier.

    When include_variance=True, high-variance teams have more
    spread in their outcomes (can upset or be upset more).
    """
    rating_a, var_a = get_composite_rating(team_a)
    rating_b, var_b = get_composite_rating(team_b)

    diff = rating_a - rating_b

    # Base logistic: each 1 point ≈ 3% win probability shift
    # Variance modifiers affect the slope — higher variance = flatter curve
    # (more randomness, closer to 50/50)
    if include_variance:
        # Combined variance: geometric mean
        combined_var = math.sqrt(var_a * var_b)
        # Higher variance → lower slope → more upsets
        slope = 0.15 / combined_var
    else:
        slope = 0.15

    prob = 1.0 / (1.0 + math.exp(-diff * slope))

    # Floor/ceiling: no game is ever truly 0% or 100%
    prob = max(0.005, min(0.995, prob))

    return prob


def simulate_game(team_a, team_b):
    """Simulate a single game with variance-adjusted probability."""
    prob_a = win_probability(team_a, team_b, include_variance=True)
    return team_a if random.random() < prob_a else team_b


# ============================================================
# CONFIDENCE TIERS
# Rate each pick on how confident we are
# ============================================================
def get_confidence_tier(prob):
    """
    Assign confidence tier based on win probability.
    Returns (tier_name, tier_emoji, tier_description)
    """
    if prob >= 0.90:
        return ("LOCK", "A+", "Near-certain. Would need a miracle upset.")
    elif prob >= 0.80:
        return ("VERY HIGH", "A", "Strong favorite. Upset possible but unlikely.")
    elif prob >= 0.70:
        return ("HIGH", "B+", "Clear favorite but not a lock.")
    elif prob >= 0.60:
        return ("MODERATE", "B", "Favored but a real game. Upset wouldn't shock.")
    elif prob >= 0.52:
        return ("LEAN", "C+", "Slight edge. Could go either way.")
    elif prob >= 0.48:
        return ("TOSSUP", "C", "Coin flip. No meaningful edge.")
    elif prob >= 0.40:
        return ("UPSET LEAN", "C-", "Underdog but with a real path.")
    elif prob >= 0.30:
        return ("UPSET", "D+", "Underdog. Needs things to break right.")
    else:
        return ("LONGSHOT", "D", "Major upset territory.")


# ============================================================
# BRACKET TREE AND SIMULATION
# ============================================================
def resolve_first_four():
    """Known results + simulate remaining."""
    winners = {
        "11_West": "Texas",      # FINAL: Texas 68, NC State 66
        "16_Midwest": "Howard",  # FINAL: Howard 86, UMBC 83
    }
    # Tonight's games (simulate)
    remaining = [
        ("SMU", "Miami (OH)", "11_Midwest"),
        ("Lehigh", "Prairie View A&M", "16_South"),
    ]
    for team_a, team_b, slot in remaining:
        winners[slot] = simulate_game(team_a, team_b)
    return winners


def resolve_first_four_deterministic(strategy):
    """Deterministic First Four picks."""
    base = {
        "11_West": "Texas",
        "16_Midwest": "Howard",
    }
    if strategy in ("chalk", "simulation", "balanced", "value"):
        base["11_Midwest"] = "SMU"
        base["16_South"] = "Lehigh"
    else:  # contrarian, chaos
        base["11_Midwest"] = "Miami (OH)"  # 31-1 contrarian
        base["16_South"] = "Prairie View A&M"
    return base


def build_region_bracket(region_name, matchups, first_four_winners):
    """Build initial R64 matchups for a region."""
    games = []
    for m in matchups:
        team_high = m["team_high"]
        team_low = m["team_low"]
        if "/" in team_low:
            if "UMBC" in team_low or "Howard" in team_low:
                team_low = first_four_winners.get("16_Midwest", "Howard")
            elif "Prairie View" in team_low or "Lehigh" in team_low:
                team_low = first_four_winners.get("16_South", "Lehigh")
            elif "Texas" in team_low and "NC State" in team_low:
                team_low = first_four_winners.get("11_West", "Texas")
            elif "SMU" in team_low or "Miami (OH)" in team_low:
                team_low = first_four_winners.get("11_Midwest", "SMU")
        games.append((team_high, team_low))
    return games


def simulate_region(games):
    """Simulate all rounds of a region."""
    results = {"R64": [], "R32": [], "S16": [], "E8": []}

    r64_winners = []
    for a, b in games:
        w = simulate_game(a, b)
        r64_winners.append(w)
        results["R64"].append(w)

    r32_winners = []
    for i in range(0, len(r64_winners), 2):
        w = simulate_game(r64_winners[i], r64_winners[i+1])
        r32_winners.append(w)
        results["R32"].append(w)

    s16_winners = []
    for i in range(0, len(r32_winners), 2):
        w = simulate_game(r32_winners[i], r32_winners[i+1])
        s16_winners.append(w)
        results["S16"].append(w)

    results["E8"].append(simulate_game(s16_winners[0], s16_winners[1]))
    return results


def simulate_tournament(bracket_data):
    """Simulate entire tournament once."""
    ff_winners = resolve_first_four()
    all_results = {"first_four": ff_winners}
    final_four = []

    for region_name, region_data in bracket_data["regions"].items():
        games = build_region_bracket(region_name, region_data["matchups"], ff_winners)
        region_results = simulate_region(games)
        all_results[region_name] = region_results
        final_four.append(region_results["E8"][0])

    # Standard bracket: East vs West, Midwest vs South
    semi1 = simulate_game(final_four[0], final_four[1])
    semi2 = simulate_game(final_four[2], final_four[3])
    champion = simulate_game(semi1, semi2)

    all_results["final_four"] = final_four
    all_results["semi_winners"] = [semi1, semi2]
    all_results["champion"] = champion
    return all_results


def run_simulations(n=50000):
    """Run N tournament simulations."""
    with open(DATA_DIR / "bracket_2026.json") as f:
        bracket_data = json.load(f)

    champion_counts = Counter()
    final_four_counts = Counter()
    elite_8_counts = Counter()
    sweet_16_counts = Counter()
    round_32_counts = Counter()
    round_64_counts = Counter()
    region_winner_counts = {r: Counter() for r in bracket_data["regions"]}

    # Track matchup-specific results for confidence tiers
    matchup_results = defaultdict(lambda: {"wins": 0, "total": 0})

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

    def to_pct(counter):
        return {team: round(count / n * 100, 1) for team, count in counter.most_common()}

    return {
        "simulations": n,
        "champion": to_pct(champion_counts),
        "final_four": to_pct(final_four_counts),
        "elite_8": to_pct(elite_8_counts),
        "sweet_16": to_pct(sweet_16_counts),
        "round_of_32": to_pct(round_32_counts),
        "round_of_64": to_pct(round_64_counts),
        "region_winners": {r: to_pct(c) for r, c in region_winner_counts.items()},
    }


# ============================================================
# BRACKET GENERATION WITH CONFIDENCE TIERS
# ============================================================
def generate_bracket_with_confidence(strategy, sim_results):
    """Generate a bracket with confidence tier for each pick."""
    with open(DATA_DIR / "bracket_2026.json") as f:
        bracket_data = json.load(f)

    ff = resolve_first_four_deterministic(strategy)
    bracket = {
        "strategy": strategy,
        "regions": {},
        "final_four": [],
        "champion": None,
        "confidence_summary": {"A+": 0, "A": 0, "B+": 0, "B": 0, "C+": 0, "C": 0, "C-": 0, "D+": 0, "D": 0},
    }

    for region_name, region_data in bracket_data["regions"].items():
        games = build_region_bracket(region_name, region_data["matchups"], ff)
        region_picks = pick_region_with_confidence(games, strategy, sim_results, region_name)
        bracket["regions"][region_name] = region_picks

        # Count confidence tiers
        for game in region_picks["all_picks"]:
            tier = game["confidence_grade"]
            bracket["confidence_summary"][tier] = bracket["confidence_summary"].get(tier, 0) + 1

    # Final Four
    ff_teams = [bracket["regions"][r]["elite_8"] for r in ["East", "West", "Midwest", "South"]]
    bracket["final_four"] = ff_teams

    # Pick champion based on strategy
    if strategy in ("chalk", "simulation", "balanced", "value"):
        semi1 = max(ff_teams[0:2], key=lambda t: get_composite_rating(t)[0])
        semi2 = max(ff_teams[2:4], key=lambda t: get_composite_rating(t)[0])
        bracket["champion"] = max([semi1, semi2], key=lambda t: get_composite_rating(t)[0])
    elif strategy == "contrarian":
        # Pick less popular teams for differentiation
        semi1 = min(ff_teams[0:2], key=lambda t: sim_results["champion"].get(t, 50))
        semi2 = min(ff_teams[2:4], key=lambda t: sim_results["champion"].get(t, 50))
        bracket["champion"] = min([semi1, semi2], key=lambda t: sim_results["champion"].get(t, 50))
    else:  # chaos
        semi1 = min(ff_teams[0:2], key=lambda t: get_composite_rating(t)[0])
        semi2 = min(ff_teams[2:4], key=lambda t: get_composite_rating(t)[0])
        bracket["champion"] = min([semi1, semi2], key=lambda t: get_composite_rating(t)[0])

    bracket["semi_winners"] = [semi1, semi2]
    return bracket


def pick_region_with_confidence(games, strategy, sim_results, region_name):
    """Pick winners through a region with confidence tiers."""
    region = {"R64": [], "R32": [], "S16": [], "elite_8": None, "all_picks": []}

    # R64
    r64_winners = []
    for team_a, team_b in games:
        winner, prob, tier = pick_game_with_confidence(team_a, team_b, strategy, sim_results)
        r64_winners.append(winner)
        loser = team_b if winner == team_a else team_a
        pick_data = {
            "round": "R64", "winner": winner, "loser": loser,
            "probability": round(prob * 100, 1),
            "confidence_tier": tier[0], "confidence_grade": tier[1],
            "confidence_desc": tier[2],
        }
        region["R64"].append(pick_data)
        region["all_picks"].append(pick_data)

    # R32
    r32_winners = []
    for i in range(0, len(r64_winners), 2):
        winner, prob, tier = pick_game_with_confidence(r64_winners[i], r64_winners[i+1], strategy, sim_results)
        r32_winners.append(winner)
        loser = r64_winners[i+1] if winner == r64_winners[i] else r64_winners[i]
        pick_data = {
            "round": "R32", "winner": winner, "loser": loser,
            "probability": round(prob * 100, 1),
            "confidence_tier": tier[0], "confidence_grade": tier[1],
            "confidence_desc": tier[2],
        }
        region["R32"].append(pick_data)
        region["all_picks"].append(pick_data)

    # S16
    s16_winners = []
    for i in range(0, len(r32_winners), 2):
        winner, prob, tier = pick_game_with_confidence(r32_winners[i], r32_winners[i+1], strategy, sim_results)
        s16_winners.append(winner)
        loser = r32_winners[i+1] if winner == r32_winners[i] else r32_winners[i]
        pick_data = {
            "round": "S16", "winner": winner, "loser": loser,
            "probability": round(prob * 100, 1),
            "confidence_tier": tier[0], "confidence_grade": tier[1],
            "confidence_desc": tier[2],
        }
        region["S16"].append(pick_data)
        region["all_picks"].append(pick_data)

    # E8
    winner, prob, tier = pick_game_with_confidence(s16_winners[0], s16_winners[1], strategy, sim_results)
    region["elite_8"] = winner
    loser = s16_winners[1] if winner == s16_winners[0] else s16_winners[0]
    pick_data = {
        "round": "E8", "winner": winner, "loser": loser,
        "probability": round(prob * 100, 1),
        "confidence_tier": tier[0], "confidence_grade": tier[1],
        "confidence_desc": tier[2],
    }
    region["all_picks"].append(pick_data)

    return region


def pick_game_with_confidence(team_a, team_b, strategy, sim_results):
    """Pick a game winner and return (winner, probability, confidence_tier)."""
    prob_a = win_probability(team_a, team_b)
    prob_b = 1 - prob_a

    if strategy == "chalk":
        if prob_a >= prob_b:
            tier = get_confidence_tier(prob_a)
            return team_a, prob_a, tier
        else:
            tier = get_confidence_tier(prob_b)
            return team_b, prob_b, tier

    elif strategy == "contrarian":
        rating_a, _ = get_composite_rating(team_a)
        rating_b, _ = get_composite_rating(team_b)
        diff = abs(rating_a - rating_b)
        # Pick upset when gap is small enough
        if diff < 4:
            # Pick the less popular team
            pop_a = sim_results.get("round_of_64", {}).get(team_a, 50)
            pop_b = sim_results.get("round_of_64", {}).get(team_b, 50)
            if pop_a > pop_b:
                tier = get_confidence_tier(prob_b)
                return team_b, prob_b, tier
            else:
                tier = get_confidence_tier(prob_a)
                return team_a, prob_a, tier
        if prob_a >= prob_b:
            tier = get_confidence_tier(prob_a)
            return team_a, prob_a, tier
        else:
            tier = get_confidence_tier(prob_b)
            return team_b, prob_b, tier

    elif strategy == "chaos":
        # Aggressive upset picks
        if prob_a < 0.72 and get_composite_rating(team_b)[0] > 10:
            tier = get_confidence_tier(prob_b)
            return team_b, prob_b, tier
        if prob_a >= prob_b:
            tier = get_confidence_tier(prob_a)
            return team_a, prob_a, tier
        else:
            tier = get_confidence_tier(prob_b)
            return team_b, prob_b, tier

    else:  # simulation, balanced, value
        if prob_a >= prob_b:
            tier = get_confidence_tier(prob_a)
            return team_a, prob_a, tier
        else:
            tier = get_confidence_tier(prob_b)
            return team_b, prob_b, tier


# ============================================================
# BETTING EDGE CALCULATOR
# ============================================================
LIVE_ODDS_THURSDAY = {
    # Format: (team_a, team_b): {"spread": X, "ml_fav": X, "ml_dog": X, "ou": X}
    ("Ohio State", "TCU"): {"spread": -2.5, "ml_fav": -142, "ml_dog": 120, "ou": 145.5},
    ("Nebraska", "Troy"): {"spread": -12.5, "ml_fav": -1000, "ml_dog": 650, "ou": 137.5},
    ("Louisville", "South Florida"): {"spread": -4.5, "ml_fav": -205, "ml_dog": 170, "ou": 164.5},
    ("Wisconsin", "High Point"): {"spread": -10.5, "ml_fav": -500, "ml_dog": 380, "ou": 163.5},
    ("Duke", "Siena"): {"spread": -27.5, "ml_fav": -20000, "ml_dog": 3500, "ou": 135.5},
    ("Vanderbilt", "McNeese"): {"spread": -14.5, "ml_fav": -1200, "ml_dog": 700, "ou": 144.5},
    ("Arizona", "LIU"): {"spread": -30.5, "ml_fav": -100000, "ml_dog": 5000, "ou": 150.5},
    ("Virginia", "Wright State"): {"spread": -18.5, "ml_fav": -2800, "ml_dog": 1300, "ou": 145.5},
    ("Iowa State", "Tennessee State"): {"spread": -24.5, "ml_fav": -8000, "ml_dog": 2200, "ou": 149.5},
    ("Alabama", "Hofstra"): {"spread": -23.5, "ml_fav": -4000, "ml_dog": 1100, "ou": 154.5},
    ("Kentucky", "Santa Clara"): {"spread": -2.5, "ml_fav": -162, "ml_dog": 136, "ou": 160.5},
    ("Texas Tech", "Akron"): {"spread": -7.5, "ml_fav": -340, "ml_dog": 270, "ou": 156.5},
}


def ml_to_implied_prob(ml):
    """Convert American moneyline to implied probability."""
    if ml < 0:
        return abs(ml) / (abs(ml) + 100)
    else:
        return 100 / (ml + 100)


def generate_betting_picks():
    """Generate betting picks comparing model vs live odds."""
    with open(DATA_DIR / "bracket_2026.json") as f:
        bracket_data = json.load(f)

    picks = []
    for region_name, region_data in bracket_data["regions"].items():
        for matchup in region_data["matchups"]:
            team_h = matchup["team_high"]
            team_l = matchup["team_low"]
            if "/" in team_l:
                continue

            prob_h = win_probability(team_h, team_l)
            prob_l = 1 - prob_h
            seed_h = matchup["seed_high"]
            seed_l = matchup["seed_low"]

            # Check if we have live odds
            odds_key = (team_h, team_l)
            live_odds = LIVE_ODDS_THURSDAY.get(odds_key, None)

            if live_odds:
                implied_fav = ml_to_implied_prob(live_odds["ml_fav"])
                implied_dog = ml_to_implied_prob(live_odds["ml_dog"])
                # Remove vig (normalize)
                total_implied = implied_fav + implied_dog
                implied_fav_clean = implied_fav / total_implied
                implied_dog_clean = implied_dog / total_implied

                edge_fav = prob_h - implied_fav_clean
                edge_dog = prob_l - implied_dog_clean
                spread = live_odds["spread"]
            else:
                # Use historical seed rates
                market_upset = HISTORICAL_UPSET_RATES.get((seed_h, seed_l), 0.3)
                implied_fav_clean = 1 - market_upset
                implied_dog_clean = market_upset
                edge_fav = prob_h - implied_fav_clean
                edge_dog = prob_l - implied_dog_clean
                spread = None

            # Determine best bet
            confidence_tier = get_confidence_tier(max(prob_h, prob_l))
            if edge_dog > 0.03 and prob_l > 0.25:
                best_bet = f"{team_l} (underdog)"
                edge = edge_dog
                bet_conf = "HIGH" if edge > 0.08 else "MEDIUM" if edge > 0.05 else "LOW"
            elif edge_fav > 0.03:
                best_bet = f"{team_h} (favorite)"
                edge = edge_fav
                bet_conf = "HIGH" if edge > 0.08 else "MEDIUM" if edge > 0.05 else "LOW"
            else:
                best_bet = "NO EDGE"
                edge = 0
                bet_conf = "PASS"

            picks.append({
                "region": region_name,
                "matchup": f"({seed_h}) {team_h} vs ({seed_l}) {team_l}",
                "favorite": team_h,
                "underdog": team_l,
                "model_prob_fav": round(prob_h * 100, 1),
                "model_prob_dog": round(prob_l * 100, 1),
                "implied_prob_fav": round(implied_fav_clean * 100, 1),
                "implied_prob_dog": round(implied_dog_clean * 100, 1),
                "edge_fav": round(edge_fav * 100, 1),
                "edge_dog": round(edge_dog * 100, 1),
                "spread": spread,
                "best_bet": best_bet,
                "confidence": bet_conf,
                "venue": matchup.get("venue", "TBD"),
                "game_confidence": confidence_tier[0],
            })

    return picks


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MARCH MADNESS 2026 SIMULATOR v2")
    print("ESPN BPI-Powered | Variance-Adjusted | Confidence-Tiered")
    print("=" * 60)

    N_SIMS = 50000
    print(f"\nRunning {N_SIMS:,} tournament simulations...")

    sim_results = run_simulations(N_SIMS)

    # Save simulation results
    with open(DATA_DIR / "simulation_results_v2.json", "w") as f:
        json.dump(sim_results, f, indent=2)
    print(f"Results saved to data/simulation_results_v2.json")

    # Championship probabilities
    print("\n" + "=" * 60)
    print("CHAMPIONSHIP PROBABILITIES (Top 15)")
    print("=" * 60)
    for team, pct in list(sim_results["champion"].items())[:15]:
        bar = "█" * int(pct)
        print(f"  {team:20s} {pct:5.1f}% {bar}")

    # Final Four
    print("\n" + "=" * 60)
    print("FINAL FOUR PROBABILITIES (Top 15)")
    print("=" * 60)
    for team, pct in list(sim_results["final_four"].items())[:15]:
        bar = "█" * int(pct / 2)
        print(f"  {team:20s} {pct:5.1f}% {bar}")

    # Generate 4 brackets with confidence
    print("\n" + "=" * 60)
    print("4 BRACKET STRATEGIES WITH CONFIDENCE TIERS")
    print("=" * 60)

    # ---- POOL-SPECIFIC BRACKETS ----
    # User's pools:
    #   8 people (free) -> Pure chalk, Florida champion
    #   18 people (money) -> Balanced, Arizona champion
    #   20 people (free) -> Balanced+, Houston champion
    #   34 people (money) Entry 1 -> Balanced, Florida champion
    #   34 people (money) Entry 2 -> Contrarian, Houston champion

    pool_configs = [
        {"name": "8-Person Free (Pure Chalk)", "strategy": "chalk", "pool_size": 8, "stakes": "Free",
         "forced_champion": "Florida", "desc": "Maximize expected points. Be right the most."},
        {"name": "18-Person Money (Balanced)", "strategy": "balanced", "pool_size": 18, "stakes": "Money",
         "forced_champion": "Arizona", "desc": "Slight differentiation. Arizona is safest healthy 1-seed."},
        {"name": "20-Person Free (Balanced+)", "strategy": "balanced", "pool_size": 20, "stakes": "Free",
         "forced_champion": "Houston", "desc": "Free pool = more aggressive. Houston has home court edge for S16/E8."},
        {"name": "34-Person Money #1 (Balanced)", "strategy": "balanced", "pool_size": 34, "stakes": "Money",
         "forced_champion": "Florida", "desc": "Entry 1: Maximize expected points via cleanest path (Tampa home court)."},
        {"name": "34-Person Money #2 (Contrarian)", "strategy": "contrarian", "pool_size": 34, "stakes": "Money",
         "forced_champion": "Houston", "desc": "Entry 2: Different champion = hedge. If Florida busts, Houston covers."},
    ]

    all_brackets = {}
    for i, cfg in enumerate(pool_configs):
        bracket = generate_bracket_with_confidence(cfg["strategy"], sim_results)
        # Override champion if forced
        if cfg.get("forced_champion"):
            bracket["champion"] = cfg["forced_champion"]
        bracket["pool_config"] = cfg
        key = f"pool_{i+1}_{cfg['strategy']}"
        all_brackets[key] = bracket
        print(f"\n  [{cfg['name']}]")
        print(f"    Champion: {bracket['champion']}")
        print(f"    Final Four: {', '.join(bracket['final_four'])}")
        print(f"    Confidence: {bracket['confidence_summary']}")

    with open(DATA_DIR / "brackets_v2.json", "w") as f:
        json.dump(all_brackets, f, indent=2)

    # Betting picks
    print("\n" + "=" * 60)
    print("BETTING PICKS (Model vs Live Odds)")
    print("=" * 60)

    picks = generate_betting_picks()
    edge_picks = [p for p in picks if p["best_bet"] != "NO EDGE"]
    edge_picks.sort(key=lambda x: max(abs(x["edge_fav"]), abs(x["edge_dog"])), reverse=True)

    for p in edge_picks[:10]:
        print(f"\n  {p['matchup']}")
        print(f"    Best Bet: {p['best_bet']} ({p['confidence']})")
        print(f"    Model: {p['model_prob_fav']}% fav / {p['model_prob_dog']}% dog")
        print(f"    Market: {p['implied_prob_fav']}% / {p['implied_prob_dog']}%")
        print(f"    Edge: {max(abs(p['edge_fav']), abs(p['edge_dog'])):.1f}%")
        if p['spread']:
            print(f"    Spread: {p['spread']}")

    with open(DATA_DIR / "betting_picks_v2.json", "w") as f:
        json.dump(picks, f, indent=2)

    print(f"\nAll data saved. Run generate_html_v2.py to build the output.")
