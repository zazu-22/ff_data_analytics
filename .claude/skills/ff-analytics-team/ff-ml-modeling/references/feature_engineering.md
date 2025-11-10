# Feature Engineering for Fantasy Football Player Models

## Core Principle

**Feature engineering is more important than model selection for sports predictions.** Well-engineered features can make simple models outperform complex ones with raw statistics.

## 1. Age Curves and Temporal Features

### Marcel Projection System (Baseline Standard)

The Marcel system represents "minimum competence" using three core elements:

1. **Weighted Historical Data:** 3-year weighted average (most recent weighted heaviest)
2. **Age Adjustment:**
   - Peak age: 29 years old
   - If age > 29: `AgeAdj = (age - 29) * 0.003`
   - If age < 29: `AgeAdj = (age - 29) * 0.006`
3. **Regression to Mean:** Pull toward average player performance

**Key Insight:** Despite simplicity, Marcel typically performs on par with complex systems. Use as baseline.

### NFL Age Curves by Position

- **Quarterbacks:** Peak ~25, steep upward trend early career, gentler decline
- **Running Backs:** Sharp decline post-27 (wear-and-tear effects) - Exit Year 4!
- **Wide Receivers:** Third-year breakout pattern, peak 26-28
- **Tight Ends:** Sophomore breakout, maintain through Year 7

**Challenge:** Survivorship bias - only elite players play into 30s/40s, making age curves appear flatter.

**Solution:** Weight adjustments by snaps played and quality metrics.

### Implementation Pattern

```python
def apply_age_adjustment(player_stats, age, position_peak_age=27):
    """Apply age-based performance adjustment"""
    if age < position_peak_age:
        # Growth phase - larger adjustment
        age_factor = 1 + (position_peak_age - age) * 0.006
    else:
        # Decline phase - smaller adjustment
        age_factor = 1 - (age - position_peak_age) * 0.003

    return player_stats * age_factor
```

## 2. Opportunity-Based Features

**Philosophy:** Raw statistics are heavily influenced by opportunity. Normalize by touches/targets/snaps.

### Core Opportunity Metrics

| Metric | Formula | Use Case |
|--------|---------|----------|
| **Weighted Opportunities** | Carries + (Targets × 1.5) | RB usage context (targets more valuable) |
| **Fantasy Points Per Opportunity** | Total FP / (Carries + Targets) | Efficiency measure |
| **Target Share** | Player Targets / Team Total Targets | Pass-catching role |
| **Usage Rate** | Player Touches / Team Possessions | Overall involvement |
| **Snap Share** | Player Snaps / Team Total Snaps | Playing time |
| **Fantasy Points Per Target** | Total FP / Total Targets | WR/TE efficiency |

**Key Finding:** High usage rates correlate with lower efficiency due to defensive attention and fatigue. Context matters.

### Implementation

```python
features = {
    'points_per_opportunity': total_fantasy_points / (carries + targets),
    'target_share': player_targets / team_targets,
    'weighted_opportunities': carries + (targets * 1.5),
    'snap_weighted_production': total_fantasy_points / snap_share,
    'touch_efficiency': yards_from_scrimmage / total_touches
}
```

## 3. Efficiency Statistics

**Concept:** Separate skill from opportunity by measuring per-touch/per-target production.

### Common Efficiency Metrics

- **Yards Per Carry (YPC):** For RBs (min 50 carries for stability)
- **Yards Per Route Run (YPRR):** For WRs (captures route efficiency)
- **Yards After Contact (YAC):** Measures elusiveness and power
- **Catch Rate:** Targets converted to receptions (adjusted for depth)
- **Contested Catch Rate:** High-difficulty receptions
- **True Completion %:** QB accuracy adjusted for drops

**Warning:** Efficiency metrics are noisy with small samples. Use rolling averages (3-5 games) or require minimum thresholds.

## 4. Interaction Terms and Contextual Features

**Philosophy:** Player performance doesn't exist in a vacuum - it's influenced by teammates, opponents, and game context.

**Research Finding:** ~40% of unexplained team performance variation attributable to team synergy and player interactions.

### Teammate Quality Effects

```python
# QB quality affects receiver production
'qb_quality_x_targets': qb_passer_rating * target_share,
'offensive_line_score_x_carries': ol_pass_block_grade * carries,
'rb_quality_x_passing_attempts': rb_yards_after_contact * pass_attempts
```

### Opponent Strength Adjustments

```python
'opponent_defense_rank': opponent_points_allowed_rank,
'matchup_advantage': player_position_rank - opponent_position_defense_rank,
'dvoa_adjusted_production': raw_production / opponent_dvoa
```

### Game Script and Context

```python
'score_differential': team_score - opponent_score,
'game_script': 'rushing' if leading else 'passing',
'vegas_implied_total': betting_market_team_points,
'home_away_indicator': 1 if home else 0
```

## 5. Rolling Averages and Lag Features

**Time-Series Features:** Recent performance is more predictive than season-long averages.

### Multi-Window Rolling Features

```python
features = {
    'last_3_games_avg': df.rolling(3).mean(),
    'last_5_games_avg': df.rolling(5).mean(),
    'season_long_avg': df.expanding().mean(),
    'last_game_lag': df.shift(1),
    'same_opponent_last_season': df.lag_by_opponent(seasons=1),
    'home_away_split': df.groupby('home_indicator').mean()
}

# Trend features
features['performance_trend'] = (
    features['last_3_games_avg'] - features['last_5_games_avg']
)
```

**Best Practice:** Include multiple time windows to capture both recent form and established baseline.

## 6. Fantasy Football Specific Features

### High-Value Engineered Features

```python
engineered_features = {
    # Production rates
    'avg_fantasy_points_per_game': total_fp / games_played,
    'avg_touches_per_game': total_touches / games_played,

    # Opportunity-adjusted efficiency
    'offensive_ability': (rushing_yards + receiving_yards + TDs) / total_touches,
    'red_zone_efficiency': red_zone_TDs / red_zone_touches,

    # Consistency metrics
    'coefficient_of_variation': std(weekly_fp) / mean(weekly_fp),
    'boom_rate': weeks_above_20fp / total_weeks,
    'bust_rate': weeks_below_5fp / total_weeks,

    # Usage stability
    'target_share_volatility': std(weekly_target_share),
    'snap_share_trend': linear_slope(snap_share_by_week)
}
```

## Feature Engineering Workflow

**Step 1: Start with Raw Statistics**
- Yards, TDs, receptions, carries, targets, snaps

**Step 2: Apply Correlation Analysis**
- Identify stats most correlated with fantasy points
- Remove highly correlated features (multicollinearity)

**Step 3: Incorporate Domain Knowledge**
- Age curves, positional differences, usage patterns
- TD regression tendencies (xTD vs actual)

**Step 4: Create Ratio/Rate Features**
- Points per opportunity, yards per route, efficiency metrics
- Normalize by opportunity (targets, snaps, touches)

**Step 5: Add Contextual Adjustments**
- Opponent strength, teammate quality, game script
- Interaction terms for synergy effects

**Step 6: Test Feature Importance**
- Use Lasso for automatic feature selection
- SHAP values for model-agnostic importance
- Remove low-importance features (reduce noise)

## Common Feature Engineering Mistakes

**1. Leaking Future Information**
- Don't include end-of-season stats when predicting mid-season
- Only use data available at prediction time

**2. Ignoring Position Differences**
- WR and RB features shouldn't be identical
- Position-specific features capture unique roles

**3. Over-engineering Without Domain Knowledge**
- Random polynomial features rarely help
- Use domain expertise to guide feature creation

**4. Not Handling Missing Values**
- Rookies lack historical data
- Injured players missing games
- Use imputation strategies (mean, positional average, similar player)

**5. Forgetting Feature Scaling**
- Tree-based models don't need scaling
- Linear models and neural nets require normalization

## Python Libraries for Feature Engineering

```python
# Core libraries
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler

# Feature engineering
from feature_engine.creation import CyclicalFeatures
from feature_engine.timeseries import LagFeatures, WindowFeatures

# Domain-specific
import nfl_data_py  # NFL statistics
import nflreadr     # NFLverse data access
```

## Feature Store Pattern

Create reusable feature definitions:

```python
# features/player_features.py
def create_player_features(df):
    """Generate standard player features for modeling"""
    features = pd.DataFrame()

    # Age features
    features['age'] = df['age']
    features['age_squared'] = df['age'] ** 2
    features['career_year'] = df['season'] - df['rookie_season']

    # Opportunity features
    features['target_share'] = df['targets'] / df['team_targets']
    features['snap_share'] = df['snaps'] / df['team_snaps']

    # Efficiency features
    features['yprr'] = df['receiving_yards'] / df['routes_run']
    features['ypc'] = df['rushing_yards'] / df['carries']

    # Rolling features
    features['last_3_avg_fp'] = df.groupby('player_id')['fantasy_points'].rolling(3).mean()

    return features
```

**Sources:**
- Baseball-Reference, FanGraphs, PFF, PlayerProfiler, Berkeley Sports Analytics, MIT, SMU, Medium
