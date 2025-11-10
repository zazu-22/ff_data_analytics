"""
Monte Carlo Simulation Template for Fantasy Football

Provides templates for common simulation scenarios:
- Rest-of-season projections
- Championship probability
- Trade impact analysis
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =============================================================================
# 1. BASIC SIMULATION FUNCTIONS
# =============================================================================

def simulate_player_week(projection, std_dev, n_sims=10000):
    """Simulate single player's weekly fantasy points"""
    simulated_points = np.random.normal(projection, std_dev, n_sims)
    return np.maximum(simulated_points, 0)  # Floor at zero

def estimate_std_dev(historical_points):
    """Estimate standard deviation from historical performance"""
    return np.std(historical_points)

# =============================================================================
# 2. REST-OF-SEASON SIMULATION
# =============================================================================

def simulate_rest_of_season(roster_projections, roster_std_devs, weeks_remaining, n_sims=10000):
    """
    Simulate rest of season for roster

    Args:
        roster_projections: Dict {player_id: [week1, week2, ...]} or list of weekly totals
        roster_std_devs: Dict {player_id: std_dev} or single value
        weeks_remaining: Number of weeks
        n_sims: Simulation count

    Returns:
        Array of total points (length n_sims)
    """
    total_points = np.zeros(n_sims)

    for week in range(weeks_remaining):
        # If roster_projections is a list of weekly totals
        if isinstance(roster_projections, (list, np.ndarray)):
            week_proj = roster_projections[week] if week < len(roster_projections) else roster_projections[-1]
            week_std = roster_std_devs if isinstance(roster_std_devs, (int, float)) else roster_std_devs[week]
            week_points = simulate_player_week(week_proj, week_std, n_sims)
            total_points += week_points
        else:
            # Dict of player projections
            for player_id, weekly_projs in roster_projections.items():
                proj = weekly_projs[week] if week < len(weekly_projs) else weekly_projs[-1]
                std = roster_std_devs[player_id]
                week_points = simulate_player_week(proj, std, n_sims)
                total_points += week_points

    return total_points

# =============================================================================
# 3. CHAMPIONSHIP PROBABILITY
# =============================================================================

def calculate_championship_probability(my_roster, opponent_rosters, n_sims=10000):
    """
    Estimate championship probability

    Args:
        my_roster: Dict {player: {'projections': [...], 'std_dev': X}}
        opponent_rosters: Dict {team_name: {player: {'projections': [...], 'std_dev': X}}}
        n_sims: Number of simulations

    Returns:
        Dict of win probabilities
    """
    weeks = len(list(my_roster.values())[0]['projections'])

    # Simulate my team
    my_projs = {p: stats['projections'] for p, stats in my_roster.items()}
    my_stds = {p: stats['std_dev'] for p, stats in my_roster.items()}
    my_points = simulate_rest_of_season(my_projs, my_stds, weeks, n_sims)

    # Simulate opponents
    opponent_points = {}
    for team_name, roster in opponent_rosters.items():
        opp_projs = {p: stats['projections'] for p, stats in roster.items()}
        opp_stds = {p: stats['std_dev'] for p, stats in roster.items()}
        opponent_points[team_name] = simulate_rest_of_season(opp_projs, opp_stds, weeks, n_sims)

    # Win probabilities
    win_probs = {}
    for team_name, opp_points in opponent_points.items():
        win_probs[f'vs_{team_name}'] = np.sum(my_points > opp_points) / n_sims

    # Championship (beat all)
    all_opp = np.column_stack(list(opponent_points.values()))
    beat_all = np.sum(np.all(my_points[:, np.newaxis] > all_opp, axis=1))
    win_probs['Championship'] = beat_all / n_sims

    return win_probs, my_points, opponent_points

# =============================================================================
# 4. TRADE IMPACT ANALYSIS
# =============================================================================

def simulate_trade_impact(current_roster, players_out, players_in, weeks_remaining, n_sims=10000):
    """
    Quantify trade impact

    Args:
        current_roster: Dict {player: {'projections': [...], 'std_dev': X}}
        players_out: List of player IDs to trade away
        players_in: Dict {player: {'projections': [...], 'std_dev': X}} - players acquired
        weeks_remaining: Number of weeks
        n_sims: Simulations

    Returns:
        Dict with analysis
    """
    # Before trade
    curr_projs = {p: stats['projections'] for p, stats in current_roster.items()}
    curr_stds = {p: stats['std_dev'] for p, stats in current_roster.items()}
    before_points = simulate_rest_of_season(curr_projs, curr_stds, weeks_remaining, n_sims)

    # After trade
    new_roster = {p: stats for p, stats in current_roster.items() if p not in players_out}
    new_roster.update(players_in)
    new_projs = {p: stats['projections'] for p, stats in new_roster.items()}
    new_stds = {p: stats['std_dev'] for p, stats in new_roster.items()}
    after_points = simulate_rest_of_season(new_projs, new_stds, weeks_remaining, n_sims)

    # Analysis
    improvement_prob = np.sum(after_points > before_points) / n_sims
    ev_change = np.mean(after_points) - np.mean(before_points)

    return {
        'before_dist': before_points,
        'after_dist': after_points,
        'improvement_probability': improvement_prob,
        'expected_value_change': ev_change,
        'before_mean': np.mean(before_points),
        'after_mean': np.mean(after_points),
        'percentiles': {
            'before_10th': np.percentile(before_points, 10),
            'after_10th': np.percentile(after_points, 10),
            'before_50th': np.percentile(before_points, 50),
            'after_50th': np.percentile(after_points, 50),
            'before_90th': np.percentile(before_points, 90),
            'after_90th': np.percentile(after_points, 90)
        }
    }

# =============================================================================
# 5. VISUALIZATION
# =============================================================================

def visualize_trade_impact(results):
    """Visualize trade simulation results"""
    before = results['before_dist']
    after = results['after_dist']

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    axes[0].hist(before, bins=50, alpha=0.6, label='Before Trade')
    axes[0].hist(after, bins=50, alpha=0.6, label='After Trade')
    axes[0].axvline(np.mean(before), color='blue', linestyle='--', alpha=0.7, label=f'Before Mean: {np.mean(before):.1f}')
    axes[0].axvline(np.mean(after), color='orange', linestyle='--', alpha=0.7, label=f'After Mean: {np.mean(after):.1f}')
    axes[0].set_xlabel('Total Fantasy Points')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('Distribution of Outcomes')
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    # CDF
    axes[1].hist(before, bins=100, cumulative=True, density=True, alpha=0.7, label='Before Trade', histtype='step', linewidth=2)
    axes[1].hist(after, bins=100, cumulative=True, density=True, alpha=0.7, label='After Trade', histtype='step', linewidth=2)
    axes[1].set_xlabel('Total Fantasy Points')
    axes[1].set_ylabel('Cumulative Probability')
    axes[1].set_title('Cumulative Distribution Function')
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    return fig

# =============================================================================
# 6. EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Trade impact analysis
    print("Monte Carlo Template Loaded")
    print("\nExample Usage:")
    print("=" * 60)

    # Define current roster (simplified)
    current_roster = {
        'player_1': {'projections': [15, 16, 14, 15, 17], 'std_dev': 5},
        'player_2': {'projections': [12, 11, 13, 12, 11], 'std_dev': 4},
        'player_3': {'projections': [18, 19, 17, 18, 20], 'std_dev': 6}
    }

    # Players to acquire
    players_in = {
        'player_4': {'projections': [20, 21, 19, 20, 22], 'std_dev': 7}
    }

    # Simulate trade (trade away player_1 for player_4)
    results = simulate_trade_impact(
        current_roster,
        players_out=['player_1'],
        players_in=players_in,
        weeks_remaining=5,
        n_sims=10000
    )

    print(f"Improvement Probability: {results['improvement_probability']:.1%}")
    print(f"Expected Value Change: {results['expected_value_change']:+.1f} points")
    print(f"Before Trade Mean: {results['before_mean']:.1f}")
    print(f"After Trade Mean: {results['after_mean']:.1f}")

    # Visualize
    # fig = visualize_trade_impact(results)
    # plt.show()
