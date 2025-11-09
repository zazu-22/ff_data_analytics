# Monte Carlo Simulation Design for Fantasy Football

## Core Concept

Monte Carlo simulation quantifies uncertainty by running thousands of scenarios with randomness, then analyzing the distribution of outcomes.

**Fantasy Applications:**
- Rest-of-season projections with uncertainty
- Championship probability estimation
- Trade scenario analysis
- Lineup optimization under uncertainty

## Basic Simulation Framework

```python
import numpy as np

def simulate_player_week(projection, std_dev, n_sims=1000):
    """
    Simulate player's weekly fantasy points

    Args:
        projection: Expected fantasy points
        std_dev: Standard deviation (historical or estimated)
        n_sims: Number of simulations

    Returns:
        Array of simulated outcomes
    """
    simulated_points = np.random.normal(projection, std_dev, n_sims)

    # Floor at zero (can't score negative points)
    simulated_points = np.maximum(simulated_points, 0)

    return simulated_points
```

## Rest-of-Season Projection

```python
def simulate_rest_of_season(roster, weekly_projections, weekly_std_devs, weeks_remaining, n_sims=10000):
    """
    Simulate rest of season for entire roster

    Args:
        roster: List of player IDs
        weekly_projections: Dict of {player_id: [week1_proj, week2_proj, ...]}
        weekly_std_devs: Dict of {player_id: std_dev}
        weeks_remaining: Number of weeks to simulate
        n_sims: Number of simulations (10,000 recommended)

    Returns:
        Array of total points distributions
    """
    total_points = np.zeros(n_sims)

    for week in range(weeks_remaining):
        for player_id in roster:
            projection = weekly_projections[player_id][week]
            std_dev = weekly_std_devs[player_id]

            # Simulate this player this week
            week_points = simulate_player_week(projection, std_dev, n_sims)
            total_points += week_points

    return total_points
```

## Championship Probability

```python
def calculate_championship_probability(my_roster, opponent_rosters, weekly_projections, std_devs, weeks_remaining, n_sims=10000):
    """
    Estimate championship probability via simulation

    Returns:
        Dictionary with win probabilities
    """
    # Simulate my team
    my_points = simulate_rest_of_season(my_roster, weekly_projections, std_devs, weeks_remaining, n_sims)

    # Simulate all opponents
    opponent_points = {}
    for team_name, roster in opponent_rosters.items():
        opponent_points[team_name] = simulate_rest_of_season(roster, weekly_projections, std_devs, weeks_remaining, n_sims)

    # Calculate win probability vs each team
    win_probs = {}
    for team_name, opp_points in opponent_points.items():
        wins = np.sum(my_points > opp_points)
        win_probs[team_name] = wins / n_sims

    # Championship probability (beat all opponents)
    all_opponents = np.column_stack(list(opponent_points.values()))
    beat_all = np.sum(np.all(my_points[:, np.newaxis] > all_opponents, axis=1))
    win_probs['Championship'] = beat_all / n_sims

    return win_probs
```

## Trade Impact Simulation

```python
def simulate_trade_impact(current_roster, players_out, players_in, weekly_projections, std_devs, weeks_remaining, n_sims=10000):
    """
    Quantify expected impact of trade

    Returns:
        Dictionary with before/after distributions and improvement probability
    """
    # Before trade
    before_points = simulate_rest_of_season(current_roster, weekly_projections, std_devs, weeks_remaining, n_sims)

    # After trade
    new_roster = [p for p in current_roster if p not in players_out] + players_in
    after_points = simulate_rest_of_season(new_roster, weekly_projections, std_devs, weeks_remaining, n_sims)

    # Calculate improvement probability
    improvement_prob = np.sum(after_points > before_points) / n_sims

    # Expected value changes
    ev_before = np.mean(before_points)
    ev_after = np.mean(after_points)
    ev_change = ev_after - ev_before

    return {
        'before_distribution': before_points,
        'after_distribution': after_points,
        'improvement_probability': improvement_prob,
        'expected_value_change': ev_change,
        'percentiles': {
            '10th': (np.percentile(before_points, 10), np.percentile(after_points, 10)),
            '50th': (np.percentile(before_points, 50), np.percentile(after_points, 50)),
            '90th': (np.percentile(before_points, 90), np.percentile(after_points, 90))
        }
    }
```

## Path Dependence and Within-Simulation Updates

**Problem:** Team performance isn't independent across weeks. If a team starts strong, their strategy/lineup changes.

**Solution (FiveThirtyEight approach):** Update team ratings within simulations

```python
def simulate_season_with_updates(rosters, initial_projections, n_sims=10000, weeks=17):
    """
    Simulate season with within-simulation updates

    After each week, update team strength based on performance
    """
    championship_count = {team: 0 for team in rosters.keys()}

    for sim in range(n_sims):
        # Track team performance this simulation
        team_points = {team: 0 for team in rosters.keys()}
        team_ratings = {team: 1.0 for team in rosters.keys()}  # Start neutral

        for week in range(weeks):
            for team, roster in rosters.items():
                # Simulate week with current rating adjustment
                week_points = 0
                for player in roster:
                    base_proj = initial_projections[player][week]
                    adjusted_proj = base_proj * team_ratings[team]  # Adjust for hot/cold streaks
                    std_dev = base_proj * 0.3  # 30% std dev rule of thumb

                    points = np.random.normal(adjusted_proj, std_dev)
                    week_points += max(points, 0)

                team_points[team] += week_points

                # Update rating based on performance vs expectation
                expected = sum(initial_projections[p][week] for p in roster)
                if expected > 0:
                    performance_ratio = week_points / expected
                    team_ratings[team] = 0.9 * team_ratings[team] + 0.1 * performance_ratio

        # Winner this simulation
        winner = max(team_points, key=team_points.get)
        championship_count[winner] += 1

    # Convert to probabilities
    championship_probs = {team: count / n_sims for team, count in championship_count.items()}

    return championship_probs
```

## Number of Iterations

**Rule of Thumb:** Standard error ∝ 1/√n

- 1,000 sims: SE ≈ 1.6%
- 10,000 sims: SE ≈ 0.5% (recommended default)
- 100,000 sims: SE ≈ 0.16% (for final decisions)

**Practical Guideline:** Use 10,000 for most analyses, 100,000 for critical decisions

## Error Correlation

**Problem:** Player errors aren't independent. If QB has good game, his WRs likely do too.

**Solution:** Model correlations

```python
def simulate_correlated_players(qb_proj, wr_proj, qb_std, wr_std, correlation=0.6, n_sims=10000):
    """Simulate QB and WR with correlated performance"""
    # Create correlated normal random variables
    mean = [qb_proj, wr_proj]
    cov = [[qb_std**2, correlation * qb_std * wr_std],
           [correlation * qb_std * wr_std, wr_std**2]]

    samples = np.random.multivariate_normal(mean, cov, n_sims)

    qb_points = np.maximum(samples[:, 0], 0)
    wr_points = np.maximum(samples[:, 1], 0)

    return qb_points, wr_points
```

## Flaw of Averages

**Problem:** Nonlinear outcomes make "average" scenario misleading

**Example:** Roster with high variance might have:
- 40% chance of 150+ points (championship level)
- 40% chance of 80-100 points
- 20% chance of <80 points

Average = 110 points, but you never actually score 110!

**Solution:** Look at full distribution, not just mean:
- Percentiles (10th, 50th, 90th)
- Probability of exceeding thresholds
- Risk of downside scenarios

```python
def analyze_distribution(simulated_points):
    """Analyze full distribution beyond just mean"""
    return {
        'mean': np.mean(simulated_points),
        'median': np.median(simulated_points),
        'std_dev': np.std(simulated_points),
        'percentiles': {
            '10th': np.percentile(simulated_points, 10),
            '25th': np.percentile(simulated_points, 25),
            '50th': np.percentile(simulated_points, 50),
            '75th': np.percentile(simulated_points, 75),
            '90th': np.percentile(simulated_points, 90)
        },
        'prob_above_120': np.sum(simulated_points > 120) / len(simulated_points),
        'prob_below_80': np.sum(simulated_points < 80) / len(simulated_points)
    }
```

## Visualization

```python
import matplotlib.pyplot as plt

def visualize_simulation(before_dist, after_dist, labels=['Before Trade', 'After Trade']):
    """Visualize simulation results"""
    plt.figure(figsize=(12, 5))

    # Histogram
    plt.subplot(1, 2, 1)
    plt.hist(before_dist, bins=50, alpha=0.6, label=labels[0])
    plt.hist(after_dist, bins=50, alpha=0.6, label=labels[1])
    plt.xlabel('Total Fantasy Points')
    plt.ylabel('Frequency')
    plt.legend()
    plt.title('Distribution of Outcomes')

    # CDF
    plt.subplot(1, 2, 2)
    plt.hist(before_dist, bins=100, cumulative=True, density=True, alpha=0.6, label=labels[0], histtype='step')
    plt.hist(after_dist, bins=100, cumulative=True, density=True, alpha=0.6, label=labels[1], histtype='step')
    plt.xlabel('Total Fantasy Points')
    plt.ylabel('Cumulative Probability')
    plt.legend()
    plt.title('Cumulative Distribution')
    plt.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()
```

## Common Pitfalls

1. **Ignoring error correlation** - QB and his WRs are correlated
2. **Too few iterations** - Use 10,000+ for stable estimates
3. **Oversimplified assumptions** - Real performance isn't purely normal
4. **Flaw of averages** - Analyze full distribution, not just mean
5. **No path dependence** - Teams adjust based on earlier weeks

## Best Practices

**Use Realistic Distributions** - Normal is okay, but consider:
- Floor at zero (can't score negative)
- Right-skewed for TD-dependent players
- Position-specific variance patterns

**Model Key Correlations** - Teammates are correlated, opponents are negatively correlated

**Sufficient Iterations** - 10,000 default, 100,000 for important decisions

**Report Full Distribution** - Mean, median, percentiles, probability of key thresholds

**Validate** - Compare simulated distributions to historical actuals

**Sources:**
- FiveThirtyEight methodologies, statistics textbooks, sports analytics research
