# Statistical Methods and Simulation Techniques for Sports Analytics

**Research Compilation for Player Performance Modeling**
*Date: 2025-10-29*

______________________________________________________________________

## Table of Contents

1. [Regression Methodologies](#regression-methodologies)
2. [Monte Carlo Simulation](#monte-carlo-simulation)
3. [Variance Analysis & Uncertainty Quantification](#variance-analysis--uncertainty-quantification)
4. [Clustering Techniques](#clustering-techniques)
5. [Implementation Guide](#implementation-guide)
6. [Best Practices & Common Pitfalls](#best-practices--common-pitfalls)
7. [References & Resources](#references--resources)

______________________________________________________________________

## Regression Methodologies

### Overview

Regression analysis forms the backbone of sports analytics, enabling analysts to model relationships between player characteristics, game conditions, and performance outcomes. Choosing the right regression method depends on your data structure, feature relationships, and modeling objectives.

### 1. OLS (Ordinary Least Squares) Regression

**What it is:**
OLS is the foundational linear regression method that minimizes the sum of squared residuals between observed and predicted values. It estimates the relationship between independent variables (player stats, game conditions) and dependent variables (performance outcomes).

**When to use:**

- Relatively few predictors compared to sample size (general rule: at least 10-20 observations per predictor)
- Relationships between features and target are approximately linear
- Low multicollinearity among predictors (VIF < 4-5)
- Interpretability is paramount and you want unbiased coefficient estimates
- You have sufficient data quality and clean observations

**Strengths:**

- Simplest interpretation: coefficients represent the marginal effect of each variable
- Best Linear Unbiased Estimator (BLUE) under Gauss-Markov assumptions
- Well-established theory for inference (t-tests, F-tests, confidence intervals)
- Computationally efficient

**Weaknesses:**

- Sensitive to multicollinearity → inflated coefficient variances
- Prone to overfitting with many correlated predictors
- No built-in feature selection
- Sensitive to outliers
- Assumes linear relationships

**Sports Analytics Applications:**

- Basic player performance models with clean, well-understood features
- Establishing baseline models before moving to regularized methods
- Situations requiring precise coefficient interpretation for decision-making

**Python Implementation:**

```python
from sklearn.linear_model import LinearRegression
import statsmodels.api as sm

# Scikit-learn (prediction-focused)
ols_model = LinearRegression()
ols_model.fit(X_train, y_train)

# Statsmodels (statistical inference-focused)
X_with_const = sm.add_constant(X_train)
ols_model_sm = sm.OLS(y_train, X_with_const).fit()
print(ols_model_sm.summary())  # Detailed statistical output
```

______________________________________________________________________

### 2. Ridge Regression (L2 Regularization)

**What it is:**
Ridge regression adds an L2 penalty term (sum of squared coefficients) to the OLS loss function. This shrinks coefficient magnitudes toward zero but keeps all features in the model.

**When to use:**

- High multicollinearity among predictors (VIF > 5)
- Number of features approaches or exceeds number of observations
- Most predictors are believed to have some impact on the outcome
- You want to keep all features but reduce overfitting
- Prediction accuracy is more important than feature selection

**Strengths:**

- Handles multicollinearity well by distributing weights across correlated features
- Generally yields better predictions than OLS through bias-variance tradeoff
- Stable coefficients even with correlated predictors
- Works well when most features contribute to the outcome
- Always has a closed-form solution

**Weaknesses:**

- Keeps all features in the model (no automatic feature selection)
- Coefficients are harder to interpret due to shrinkage
- Requires tuning the regularization parameter (alpha/lambda)
- May overestimate/underestimate players with limited data

**Sports Analytics Applications:**

- Regularized Adjusted Plus-Minus (RAPM) in basketball → capturing player effects with correlated lineup data
- Situations with many correlated performance metrics (e.g., rushing yards, attempts, touchdowns)
- When you believe most stats contribute meaningful information

**Python Implementation:**

```python
from sklearn.linear_model import Ridge, RidgeCV

# Manual alpha selection
ridge = Ridge(alpha=1.0)
ridge.fit(X_train, y_train)

# Cross-validated alpha selection
ridge_cv = RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0], cv=5)
ridge_cv.fit(X_train, y_train)
print(f"Best alpha: {ridge_cv.alpha_}")
```

______________________________________________________________________

### 3. Lasso Regression (L1 Regularization)

**What it is:**
Lasso regression adds an L1 penalty term (sum of absolute coefficient values) to the OLS loss function. This shrinks some coefficients exactly to zero, performing automatic feature selection.

**When to use:**

- You have many features and believe only a subset are truly important
- Feature selection is a key objective
- You want a sparse, interpretable model
- Dealing with irrelevant or redundant features
- Number of predictors is large relative to sample size

**Strengths:**

- **Automatic feature selection**: Sets irrelevant coefficients to exactly zero
- Produces sparse models that are easier to interpret
- Better player discrimination than Ridge in some contexts
- Excellent for identifying key performance drivers
- Can handle p > n situations

**Weaknesses:**

- Among highly correlated features, tends to select only one arbitrarily
- Can be unstable with correlated predictors
- May underperform Ridge when most features are relevant
- No closed-form solution (requires iterative optimization)

**Sports Analytics Applications:**

- Identifying the most important stats for fantasy football scoring
- Feature selection for player projection models
- Lasso outperformed Ridge and Elastic Net in college football game outcome prediction
- LASSO multinomial models for in-play basketball indicators
- Predicting 400m hurdles race times (0.59s prediction error)

**Python Implementation:**

```python
from sklearn.linear_model import Lasso, LassoCV

# Manual alpha selection
lasso = Lasso(alpha=0.1)
lasso.fit(X_train, y_train)

# Cross-validated alpha selection with feature selection tracking
lasso_cv = LassoCV(alphas=None, cv=5, max_iter=10000)
lasso_cv.fit(X_train, y_train)

# Identify selected features
selected_features = X_train.columns[lasso_cv.coef_ != 0]
print(f"Selected {len(selected_features)} features: {list(selected_features)}")
```

**Practical Tip:** If predictors are highly correlated, consider Elastic Net (combines L1 + L2 penalties):

```python
from sklearn.linear_model import ElasticNetCV

elastic_net = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.7, 0.9, 0.95, 0.99], cv=5)
elastic_net.fit(X_train, y_train)
```

______________________________________________________________________

### 4. Generalized Additive Models (GAMs)

**What it is:**
GAMs extend linear models by replacing linear terms with smooth, non-linear functions (typically splines). Instead of assuming `y = β₀ + β₁x₁ + β₂x₂`, GAMs fit `y = β₀ + f₁(x₁) + f₂(x₂)` where `f` are smooth functions learned from the data.

**When to use:**

- Relationships between features and target are non-linear
- Modeling age curves and career trajectories
- Need interpretability along with flexibility
- Want to visualize how each feature affects the outcome
- Capturing diminishing returns or threshold effects

**Strengths:**

- **Automatically learns non-linear relationships** without manual feature engineering
- Maintains interpretability through visualizable smooth functions
- Built-in regularization prevents overfitting
- Ideal for age curves, experience effects, and performance trajectories
- Balances between simple linear models and "black box" algorithms

**Weaknesses:**

- More complex than linear models
- Slower to train than OLS/Ridge/Lasso
- Requires careful tuning of smoothness parameters
- Can still overfit with too much flexibility
- Harder to explain to non-technical stakeholders than linear models

**Sports Analytics Applications:**

1. **Age Curves**: Modeling how player performance changes with age

   - Baseball hitting statistics show different aging patterns (peak ~26-27, decline after 30)
   - NBA player aging curves using Bayesian structural models
   - NFL running back decline curves

2. **Career Trajectories**: Capturing development and deterioration phases

   - Youth athlete performance development (avoiding arbitrary age categories)
   - Peak performance ages across sports (typically 25-29y, varies by sport)

3. **Non-linear Effects**:

   - Diminishing returns on volume stats (e.g., RB carries → injury risk)
   - Threshold effects (QB passing attempts → efficiency drop-off)

**Example Age Curve Research:**

- Baseball: GAMs with piecewise smoothing show steeper aging curves in modern era (2012-2019 vs 2005-2011)
- Hockey: Flexible aging curves using GAM (Turtoro 2019)
- Basketball: Bayesian models with latent development/aging factors
- Track & Field: Peak performance at 25-27y for most events, ~28-29y for marathon/throwers

**Python Implementation:**

```python
# PyGAM - Pythonic GAM library
from pygam import LinearGAM, s, f

# Continuous features with splines, categorical with factors
gam = LinearGAM(s(0) + s(1) + f(2))  # s() = spline, f() = factor/categorical
gam.gridsearch(X_train, y_train)

# Visualize each smooth function
import matplotlib.pyplot as plt
for i, term in enumerate(gam.terms):
    if term.isintercept:
        continue
    XX = gam.generate_X_grid(term=i)
    plt.plot(XX[:, i], gam.partial_dependence(term=i, X=XX))
    plt.title(f'Partial dependence of feature {i}')
    plt.show()

# Alternative: statsmodels
from statsmodels.gam.api import GLMGam, BSplines

# Define spline basis for each feature
x_spline = X_train.columns[0]  # e.g., 'age'
bs = BSplines(X_train[x_spline], df=[10], degree=[3])
gam_sm = GLMGam.from_formula('y ~ bs(age)', data=data, smoother=bs)
res = gam_sm.fit()
```

**R Implementation (reference - mgcv is gold standard):**

```r
library(mgcv)

# Fit GAM with automatic smoothness selection
gam_model <- gam(points ~ s(age) + s(experience) + position,
                 data = player_data,
                 method = "REML")

# Visualize smooth terms
plot(gam_model, pages=1)
summary(gam_model)
```

______________________________________________________________________

### Method Selection Decision Tree

```
START: What's your goal and data situation?

┌─ Need feature selection? (Many irrelevant features)
│  └─ YES → Try LASSO first
│     ├─ High multicollinearity among important features?
│     │  └─ YES → Use Elastic Net (combines L1 + L2)
│     └─ NO → LASSO is good
│
├─ Many correlated features, most are important?
│  └─ YES → Use Ridge Regression
│
├─ Expect non-linear relationships? (Age, experience, volume effects)
│  └─ YES → Use GAM
│     └─ Can combine with regularization if needed
│
├─ Simple model, few features, want exact interpretation?
│  └─ YES → Start with OLS
│     └─ Check assumptions (VIF < 5, residuals normal, etc.)
│
└─ Not sure? → Run cross-validation comparing all methods
   └─ Use nested CV for unbiased evaluation
```

**Practical Workflow:**

1. Start with OLS as baseline → understand linear relationships
2. Check VIF for multicollinearity → if high, try Ridge/Lasso
3. Try Lasso for feature selection → identify key drivers
4. Explore GAMs for non-linear effects → especially age/experience
5. Use cross-validation to compare → select based on held-out performance
6. Validate on final test set → report realistic performance

______________________________________________________________________

## Monte Carlo Simulation

### Overview

Monte Carlo simulation uses repeated random sampling to model complex systems and quantify uncertainty. In sports analytics, it's essential for scenario analysis, championship probabilities, and rest-of-season projections where direct calculation is infeasible due to combinatorial complexity.

### Core Concept

Instead of calculating all possible outcomes analytically (often impossible), simulate the season/tournament thousands of times with random variation, then analyze the distribution of results:

```
For each simulation (1 to N):
    1. Sample from probability distributions (game outcomes, player performance)
    2. Simulate the sequence of events (games, weeks, playoffs)
    3. Record the outcome (champion, playoff qualification, wins)

Analyze results:
    - Playoff probability = # times team made playoffs / N
    - Championship probability = # times team won championship / N
    - Expected wins = mean(wins across all simulations)
    - Confidence intervals from percentiles of distribution
```

### When to Use Monte Carlo Simulation

**Ideal applications:**

- **Rest-of-season projections**: Simulate remaining games to estimate playoff odds
- **Championship probabilities**: Too many paths to calculate directly
- **Portfolio analysis**: Simulate season outcomes for multiple roster constructions
- **Risk assessment**: Quantify downside risk vs upside potential
- **Sensitivity analysis**: How do results change with different assumptions?
- **Bye week planning**: Simulate roster decisions across random player performances

**Examples from practice:**

- FiveThirtyEight NFL playoff predictions: 10,000+ simulations per week
- College Football Playoff scenarios: 10,000 simulations → Georgia 17.7% champion probability
- MLS season projections: 10,000 simulations → distribution of possible winners
- Premier League season forecasts: Monte Carlo methods for final standings

### Framework Design

**1. Define the probabilistic model:**

```python
import numpy as np
import pandas as pd

class GameSimulator:
    def __init__(self, team_strengths):
        """
        team_strengths: dict mapping team -> rating (e.g., Elo, power rating)
        """
        self.team_strengths = team_strengths

    def simulate_game(self, team_a, team_b):
        """
        Simulate single game outcome.
        Returns: (winner, team_a_score, team_b_score)
        """
        # Convert team strength differential to win probability
        # Example: Elo-based probability
        rating_diff = self.team_strengths[team_a] - self.team_strengths[team_b]
        win_prob_a = 1 / (1 + 10 ** (-rating_diff / 400))

        # Simulate winner
        winner = team_a if np.random.random() < win_prob_a else team_b

        # Optional: Simulate scores with noise
        expected_points_a = 24 + rating_diff / 25
        expected_points_b = 24 - rating_diff / 25

        score_a = np.random.poisson(expected_points_a)
        score_b = np.random.poisson(expected_points_b)

        return winner, score_a, score_b
```

**2. Handle path dependence:**

Critical insight from FiveThirtyEight: **Update team strengths within each simulation** to capture momentum and performance trends.

```python
def simulate_season(schedule, initial_strengths, n_sims=10000):
    """
    schedule: list of (week, team_a, team_b) tuples
    initial_strengths: dict of team -> initial rating
    """
    results = []

    for sim in range(n_sims):
        # Reset to initial conditions for each simulation
        team_strengths = initial_strengths.copy()
        wins = {team: 0 for team in team_strengths}

        for week, team_a, team_b in schedule:
            winner, score_a, score_b = simulate_game(team_a, team_b, team_strengths)

            wins[winner] += 1

            # Update strengths based on game result (path dependence)
            k_factor = 20  # Elo K-factor
            expected_a = 1 / (1 + 10 ** (-(team_strengths[team_a] - team_strengths[team_b]) / 400))
            actual_a = 1 if winner == team_a else 0

            team_strengths[team_a] += k_factor * (actual_a - expected_a)
            team_strengths[team_b] += k_factor * ((1 - actual_a) - (1 - expected_a))

        # Record final standings for this simulation
        results.append(wins.copy())

    return pd.DataFrame(results)
```

**3. Analyze distributions:**

```python
def analyze_simulation_results(results_df):
    """
    results_df: DataFrame with rows=simulations, columns=teams, values=wins
    """
    summary = {}

    for team in results_df.columns:
        summary[team] = {
            'mean_wins': results_df[team].mean(),
            'median_wins': results_df[team].median(),
            'std_wins': results_df[team].std(),
            '10th_percentile': results_df[team].quantile(0.10),
            '90th_percentile': results_df[team].quantile(0.90),
            'prob_playoffs': (results_df[team] >= 10).mean(),  # Example threshold
            'prob_division_win': (results_df[team] == results_df.max(axis=1)).mean()
        }

    return pd.DataFrame(summary).T
```

### Number of Simulations

**Rule of thumb**: Standard error ∝ 1/√n

- **1,000 sims**: Quick exploratory analysis (SE ≈ 1.6% for 50% probability)
- **10,000 sims**: Standard for most applications (SE ≈ 0.5%)
- **100,000 sims**: High precision for rare events (SE ≈ 0.16%)

**Convergence check:**

```python
def check_convergence(simulate_func, n_checks=10, target_sims=10000):
    """Run simulation multiple times to check stability"""
    results = []
    for _ in range(n_checks):
        results.append(simulate_func(n_sims=target_sims))

    # Calculate standard deviation across runs
    std_across_runs = np.std([r['prob_playoffs'] for r in results])
    print(f"Std dev across {n_checks} runs: {std_across_runs:.4f}")

    if std_across_runs < 0.01:  # Less than 1% variation
        print("✓ Results converged")
    else:
        print("⚠ Consider more simulations")
```

### Common Pitfalls & Solutions

#### 1. **Ignoring Error Correlation**

**Problem**: Models for each game share common errors (e.g., weather affects all teams). Simulating each game independently underestimates uncertainty.

**Solution**:

- Add correlated error terms for shared factors
- Model team strength uncertainty, not just game outcome uncertainty
- Use hierarchical models that share variance components

```python
# Bad: Independent game simulations ignore shared uncertainty
for game in schedule:
    winner = simulate_game(game)  # Each game independent

# Better: Acknowledge shared model uncertainty
def simulate_season_with_model_uncertainty(schedule, base_model, n_sims=10000):
    results = []
    for sim in range(n_sims):
        # Perturb model parameters each simulation
        model = base_model.copy()
        model['home_advantage'] = np.random.normal(model['home_advantage'], 1.5)

        season_result = simulate_full_season(schedule, model)
        results.append(season_result)
    return results
```

#### 2. **The Flaw of Averages**

**Problem**: Using average inputs produces average outputs, missing the range of possibilities and non-linear effects.

**Example**:

- Averaging player projections → expected points
- But fantasy football scoring is non-linear (bonuses, positional scarcity)
- Simulation captures these non-linearities

**Solution**: Always simulate full distributions, not just means.

#### 3. **Oversimplified Assumptions**

**Problem**: Real systems are complex. Simulations with too few factors give false confidence.

**Solutions**:

- Include known sources of variance (injuries, weather, home/away)
- Validate historical simulations against actual outcomes
- Communicate model limitations transparently
- Use simulations for relative comparisons, not absolute predictions

#### 4. **Not Updating Within Simulations**

**Problem**: Simulating all future games with current team ratings ignores momentum, injuries, and performance trends.

**Solution**: FiveThirtyEight approach - update team ratings after each simulated game within a simulation, creating path-dependent outcomes.

### Practical Implementation Example: Fantasy Football ROS Projections

```python
import numpy as np
import pandas as pd
from scipy import stats

class FantasyPlayerSimulator:
    def __init__(self, player_projections):
        """
        player_projections: DataFrame with columns [player, position, mean_points, std_points]
        """
        self.projections = player_projections

    def simulate_week(self, roster, week):
        """Simulate one week for a roster"""
        points = {}
        for player in roster:
            proj = self.projections.loc[player]

            # Model weekly variance (could be more sophisticated)
            weekly_points = np.random.normal(proj['mean_points'], proj['std_points'])
            weekly_points = max(0, weekly_points)  # Can't be negative

            points[player] = weekly_points

        return points

    def simulate_season(self, roster, weeks_remaining, n_sims=10000):
        """Simulate rest of season"""
        results = []

        for sim in range(n_sims):
            total_points = 0
            for week in range(weeks_remaining):
                week_points = self.simulate_week(roster, week)
                total_points += sum(week_points.values())

            results.append(total_points)

        return np.array(results)

    def compare_rosters(self, roster_a, roster_b, weeks_remaining, n_sims=10000):
        """Compare two roster constructions"""
        points_a = self.simulate_season(roster_a, weeks_remaining, n_sims)
        points_b = self.simulate_season(roster_b, weeks_remaining, n_sims)

        return {
            'roster_a_mean': points_a.mean(),
            'roster_b_mean': points_b.mean(),
            'roster_a_wins_pct': (points_a > points_b).mean(),
            'roster_a_10th': np.percentile(points_a, 10),
            'roster_a_90th': np.percentile(points_a, 90),
            'roster_b_10th': np.percentile(points_b, 10),
            'roster_b_90th': np.percentile(points_b, 90),
        }

# Usage
simulator = FantasyPlayerSimulator(player_projections_df)
comparison = simulator.compare_rosters(
    roster_a=['Mahomes', 'CMC', 'Jefferson'],
    roster_b=['Hurts', 'Barkley', 'Chase'],
    weeks_remaining=6,
    n_sims=10000
)
```

### Best Practices

1. **Start simple, add complexity gradually**: Begin with basic probability models, add features as needed
2. **Validate against history**: Run "retrodictions" on past seasons to test model quality
3. **Report distributions, not just means**: Show 10th/90th percentiles, probability of outcomes
4. **Document assumptions clearly**: What factors are included? What's ignored?
5. **Use version control**: Track model changes and assumption updates
6. **Parallelize for speed**: Use multiprocessing for large simulations
7. **Set random seeds for reproducibility**: `np.random.seed(42)` for debugging

### Python Libraries

- **NumPy**: Core random number generation (`np.random`)
- **SciPy**: Statistical distributions (`scipy.stats`)
- **Pandas**: Data manipulation and results analysis
- **Multiprocessing**: Parallelize simulations for speed
- **Matplotlib/Seaborn**: Visualize distributions and scenarios

______________________________________________________________________

## Variance Analysis & Uncertainty Quantification

### Regression to the Mean

**Concept**: Extreme performances during one period tend to move toward the average in subsequent periods. This is a statistical phenomenon, not a statement about player ability change—it reflects the role of luck/variance in observed outcomes.

**Why it matters in sports analytics**:

- Helps identify "fluky" performances vs. true talent changes
- Critical for in-season projection updates
- Prevents overreaction to small samples

**Fantasy Football Applications**:

1. **Running Backs**: RBs with 3 straight 1,000-yard seasons averaged 1,340 yards in those years but only 1,161 yards the next year; nearly 1/3 fell below 1,000 yards.

2. **Touchdown Regression**: Outlier TD rates always regress to the mean eventually. Example: A receiver with 15 TDs on 100 targets (15% TD rate) is likely to regress toward league average (8-10% TD rate) due to:

   - Unsustainable red zone usage
   - Luck in contested catches
   - Defensive game planning adjustments

3. **Sample Size and Certainty**:

   - **Quarterbacks**: 21 games for 50% regression to prior projection
   - **Running Backs**: 29-30 games for 50% regression
   - **Wide Receivers**: 13-14 games for 50% regression (faster due to higher variance)

**Practical Application:**

```python
def adjust_projection_with_regression(prior_projection, observed_performance, games_played, position):
    """
    Adjust projection based on observed performance with regression to mean.

    prior_projection: Preseason projection (points per game)
    observed_performance: Actual PPG so far this season
    games_played: Number of games observed
    position: QB, RB, WR, TE
    """
    # Games needed for 50% regression (from research)
    regression_constants = {
        'QB': 21,
        'RB': 29,
        'WR': 13,
        'TE': 15
    }

    k = regression_constants.get(position, 20)

    # Weight toward observed performance based on sample size
    # More games = more weight on observed, less regression to prior
    weight_observed = games_played / (games_played + k)
    weight_prior = 1 - weight_observed

    adjusted_projection = (weight_observed * observed_performance +
                          weight_prior * prior_projection)

    return adjusted_projection

# Example: WR had 25 PPG projection, averaging 30 PPG through 4 games
adjusted = adjust_projection_with_regression(
    prior_projection=25,
    observed_performance=30,
    games_played=4,
    position='WR'
)
print(f"Adjusted projection: {adjusted:.1f} PPG")
# Output: Adjusted projection: 26.2 PPG
# Only modest increase because small sample size → more regression to prior
```

**Key Insight**: The more sample size you have, the less regression to the mean occurs, and the more certain we are that observed performance reflects true talent level.

### Confidence Intervals vs. Prediction Intervals

Understanding these two types of intervals is crucial for proper uncertainty quantification in sports forecasting.

#### Confidence Intervals

**Definition**: Quantify uncertainty about a **population parameter** (e.g., mean player performance).

**Interpretation**: "We are 95% confident the true mean lies in this range"

**Width**: Narrower (only reflects sampling uncertainty)

**Formula** (for regression):

```
CI = ŷ ± t_{α/2} × SE(ŷ)
where SE(ŷ) = s × √(1/n + (x - x̄)² / Σ(xᵢ - x̄)²)
```

**Use cases**:

- Estimating a team's true strength
- Testing hypotheses (is this coefficient significantly different from zero?)
- Comparing model accuracy

#### Prediction Intervals

**Definition**: Quantify uncertainty about a **future individual observation** (e.g., a player's score next week).

**Interpretation**: "We are 95% confident the next observation will fall in this range"

**Width**: Wider (includes both sampling uncertainty AND individual variation)

**Formula** (for regression):

```
PI = ŷ ± t_{α/2} × SE(forecast)
where SE(forecast) = s × √(1 + 1/n + (x - x̄)² / Σ(xᵢ - x̄)²)
```

Note the additional "+1" term representing individual variance (σ²).

**Use cases**:

- Forecasting a player's fantasy points next week
- Setting ranges for risk assessment and decisions
- Communicating forecast uncertainty to users

#### Comparison Example

```python
import numpy as np
from scipy import stats
import statsmodels.api as sm

# Fit model
X_train_with_const = sm.add_constant(X_train)
model = sm.OLS(y_train, X_train_with_const).fit()

# New observation to predict
x_new = [1, 30]  # [intercept, age=30]

# Point prediction
y_pred = model.predict(x_new)[0]

# Confidence interval for the mean at age=30
# "What's the average performance for 30-year-old players?"
ci = model.get_prediction(x_new).conf_int(alpha=0.05)

# Prediction interval for a single player aged 30
# "What range might this specific 30-year-old player score?"
pi = model.get_prediction(x_new).conf_int(obs=True, alpha=0.05)

print(f"Point prediction: {y_pred:.1f}")
print(f"95% Confidence Interval: [{ci[0,0]:.1f}, {ci[0,1]:.1f}]")
print(f"95% Prediction Interval: [{pi[0,0]:.1f}, {pi[0,1]:.1f}]")

# Output example:
# Point prediction: 22.5
# 95% Confidence Interval: [21.8, 23.2]  # Narrower - uncertainty about mean
# 95% Prediction Interval: [15.3, 29.7]  # Wider - uncertainty about individual
```

#### Key Takeaway

- **Confidence intervals**: Use for model evaluation, comparing groups, understanding parameters
- **Prediction intervals**: Use for forecasting individual events, risk management, decision-making
- **Prediction intervals are always wider** because they account for individual variability on top of estimation uncertainty

### Handling Variance in Sports Analytics

**Sources of variance:**

1. **True talent variation**: Differences in player ability
2. **Within-player variance**: Game-to-game performance fluctuations (matchup, weather, luck)
3. **Measurement error**: Stat recording, missing data
4. **Model uncertainty**: Parameters estimated from limited data

**Hierarchical/Bayesian approaches** naturally separate these components:

```python
# Conceptual hierarchical model (would use PyMC3, Stan, etc.)
"""
Player i's performance in game j:
    y_ij ~ Normal(θ_i + β·X_ij, σ_within)  # Observed points
    θ_i ~ Normal(μ_position, σ_between)    # Player talent

Where:
    θ_i = true talent of player i
    σ_within = game-to-game variance (luck, matchup)
    σ_between = talent variance across players
"""
```

This approach:

- Pools information across players (partial pooling)
- Shrinks extreme observations toward group means (regression to mean)
- Provides natural uncertainty quantification
- Separates signal from noise

______________________________________________________________________

## Clustering Techniques

### Overview

Clustering groups similar observations together without predefined labels. In sports analytics, clustering enables player tiering, position classification, and portfolio construction based on statistical similarity.

### 1. K-Means Clustering

**What it is**:
K-means partitions observations into K clusters by minimizing within-cluster variance. Each cluster is represented by its centroid (mean of all points in the cluster).

**Algorithm**:

1. Initialize K cluster centroids (randomly or via smart initialization)
2. Assign each point to the nearest centroid
3. Recalculate centroids as the mean of assigned points
4. Repeat steps 2-3 until convergence

**When to use**:

- You have a target number of clusters in mind (e.g., "Tier 1/2/3 players")
- Features are continuous and relatively spherical clusters expected
- Computational efficiency is important (fast, scales well)
- Clusters should be of similar size/density

**Strengths**:

- Simple, interpretable, fast
- Works well with many features
- Easily scales to large datasets
- Useful for initial exploration

**Weaknesses**:

- Requires specifying K (number of clusters) upfront
- Sensitive to initialization and outliers
- Assumes spherical clusters of similar size
- Only uses Euclidean distance
- Hard assignments (each point belongs to exactly one cluster)

**Sports Analytics Applications**:

1. **Player Tiering**: Group players into talent tiers for draft/trade decisions
2. **Portfolio Construction**: Build diversified fantasy rosters by selecting from different clusters
3. **Style Classification**: Identify different player archetypes (e.g., power vs. speed RBs)
4. **Matchup Analysis**: Cluster defenses by strength profile

**Python Implementation**:

```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

# Prepare data: standardize features (K-means is sensitive to scale)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Determine optimal K using elbow method
inertias = []
K_range = range(2, 11)
for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    inertias.append(kmeans.inertia_)

# Plot elbow curve
plt.plot(K_range, inertias, 'bo-')
plt.xlabel('Number of Clusters (K)')
plt.ylabel('Inertia (within-cluster sum of squares)')
plt.title('Elbow Method for Optimal K')
plt.show()

# Fit with chosen K
kmeans = KMeans(n_clusters=4, random_state=42)
clusters = kmeans.fit_predict(X_scaled)

# Add cluster labels to dataframe
players_df['cluster'] = clusters
players_df['tier'] = players_df['cluster'].map({0: 'Elite', 1: 'High-End', 2: 'Mid-Tier', 3: 'Deep'})

# Analyze cluster characteristics
cluster_summary = players_df.groupby('tier').agg({
    'points_per_game': ['mean', 'std'],
    'consistency': 'mean',
    'upside': 'mean'
})
print(cluster_summary)
```

**Choosing K**:

- **Elbow method**: Plot inertia vs K, look for "elbow" where improvement slows
- **Silhouette score**: Measures how similar points are to their own cluster vs. other clusters
- **Domain knowledge**: Fantasy tiers (5 tiers for 12-team leagues), position groups, etc.

### 2. Hierarchical Clustering

**What it is**:
Hierarchical clustering builds a tree (dendrogram) of nested clusters without requiring K upfront. Can be agglomerative (bottom-up: merge) or divisive (top-down: split).

**Algorithm (Agglomerative)**:

1. Start with each point as its own cluster
2. Repeatedly merge the two closest clusters based on linkage criterion
3. Continue until one cluster remains
4. Cut dendrogram at desired level to get K clusters

**Linkage methods**:

- **Single**: Distance between closest points in clusters (sensitive to outliers)
- **Complete**: Distance between farthest points (more compact clusters)
- **Average**: Average distance between all pairs
- **Ward**: Minimize within-cluster variance (often best for balanced clusters)
- **Centroid**: Distance between centroids

**When to use**:

- Don't know K ahead of time (can explore different cuts)
- Want to visualize relationships via dendrogram
- Interested in nested groupings (sub-tiers within tiers)
- Working with non-Euclidean distances (e.g., correlation, dynamic time warping)
- Smaller datasets (O(n²) memory, slower than K-means)

**Strengths**:

- No need to specify K upfront
- Produces interpretable dendrogram showing relationships
- Works with any distance metric
- Captures nested structure (tiers within positions)
- Deterministic (no random initialization)

**Weaknesses**:

- Computationally expensive for large datasets (O(n²) memory)
- Once merged, clusters can't be split (greedy algorithm)
- Sensitive to outliers (especially single linkage)
- Harder to scale than K-means

**Sports Analytics Applications**:

1. **Player Taxonomy**: Discover natural groupings and sub-types
2. **Portfolio Diversification**: Ensure draft picks aren't clustered together (risk management)
3. **Time Series Clustering**: Group players by similar performance trajectory shapes (using DTW distance)
4. **Nested Tiers**: Position → tier → sub-tier hierarchy

**Python Implementation**:

```python
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist
import matplotlib.pyplot as plt

# Compute pairwise distances and perform hierarchical clustering
# Can use different distance metrics: 'euclidean', 'correlation', 'cosine', etc.
Z = linkage(X_scaled, method='ward', metric='euclidean')

# Plot dendrogram
plt.figure(figsize=(12, 6))
dendrogram(Z, labels=players_df['player_name'].values, leaf_font_size=8)
plt.title('Hierarchical Clustering Dendrogram (Ward Linkage)')
plt.xlabel('Player')
plt.ylabel('Distance')
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()

# Cut dendrogram at desired height or to get K clusters
k = 5
clusters = fcluster(Z, k, criterion='maxclust')
players_df['cluster'] = clusters

# Alternative: cut at specific distance threshold
# clusters = fcluster(Z, t=2.5, criterion='distance')

# Compare linkage methods
for method in ['single', 'complete', 'average', 'ward']:
    Z_method = linkage(X_scaled, method=method)
    clusters_method = fcluster(Z_method, k, criterion='maxclust')
    # Evaluate with silhouette score, domain knowledge, etc.
```

**Time Series Clustering with DTW**:

For clustering players by performance trajectory shape (not just levels):

```python
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform
from dtaidistance import dtw

# Player performance time series (rows = players, columns = weeks)
time_series_data = players_df[['week1', 'week2', ..., 'week17']].values

# Compute DTW distance matrix
dtw_distance_matrix = dtw.distance_matrix_fast(time_series_data)

# Convert to condensed form for scipy
condensed_dist = squareform(dtw_distance_matrix)

# Hierarchical clustering on DTW distances
Z = linkage(condensed_dist, method='average')
dendrogram(Z, labels=players_df['player_name'].values)
plt.show()
```

This groups players with similar **trajectory shapes** (e.g., consistent scorers vs. boom/bust).

### 3. Portfolio Diversification Applications

**Concept**: In financial portfolio theory, diversification reduces risk by holding uncorrelated assets. Applied to fantasy football:

- Don't draft all players from the same cluster (correlated risk)
- Balance high-floor (consistent) vs high-ceiling (volatile) players
- Spread risk across bye weeks, injury-prone profiles, etc.

**Hierarchical Clustering for Diversification**:

Research shows hierarchical clustering methods achieve the best risk-adjusted returns by appropriately distributing capital weights across nested clusters. The hierarchy naturally represents diversification levels:

- Top level: Position groups (QB, RB, WR, TE)
- Mid level: Tier within position (Elite, Mid, Deep)
- Lower level: Player archetypes (Speed vs Power RB, Possession vs Deep Threat WR)

**Implementation Pattern**:

```python
from scipy.cluster.hierarchy import linkage, fcluster
import numpy as np

def build_diversified_roster(players_df, budget_constraint, roster_slots):
    """
    Use hierarchical clustering to ensure roster diversification.
    """
    # 1. Feature engineering: performance + risk metrics
    features = players_df[['ppg', 'std_dev', 'ceiling', 'floor', 'consistency']]
    X_scaled = StandardScaler().fit_transform(features)

    # 2. Hierarchical clustering
    Z = linkage(X_scaled, method='ward')

    # 3. Cut into multiple tiers
    n_tiers = 5
    players_df['cluster'] = fcluster(Z, n_tiers, criterion='maxclust')

    # 4. Constraint: draft players from different clusters (diversification)
    # Optimization problem: maximize expected points subject to:
    #   - Budget constraint: sum(salary) <= budget
    #   - Roster constraints: 1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX
    #   - Diversification: max 2 players per cluster (reduces correlation risk)

    # (Would implement with integer programming or heuristic search)

    return optimal_roster

# Alternative: Correlation-based diversification
def correlation_diversified_roster(players_weekly_scores):
    """
    Use correlation matrix to avoid highly correlated players.
    """
    # Compute correlation between all players' weekly scores
    corr_matrix = players_weekly_scores.corr()

    # Build roster avoiding high correlation pairs
    # If player A and B have correlation > 0.7, don't draft both

    return optimal_roster
```

**Key Insight**: Hierarchical clustering + dendrogram provides a natural framework for risk diversification by ensuring selected assets/players come from different branches of the tree.

### K-Means vs. Hierarchical Clustering

| Aspect               | K-Means                   | Hierarchical                        |
| -------------------- | ------------------------- | ----------------------------------- |
| **K Selection**      | Must specify upfront      | Explore via dendrogram              |
| **Computation**      | Fast, O(n) memory         | Slow, O(n²) memory                  |
| **Scalability**      | Excellent                 | Limited to ~1000s                   |
| **Interpretability** | Simple cluster labels     | Rich dendrogram structure           |
| **Distance Metrics** | Euclidean only (standard) | Any metric (DTW, correlation, etc.) |
| **Stability**        | Random initialization     | Deterministic                       |
| **Nested Structure** | No                        | Yes                                 |
| **Best For**         | Large datasets, known K   | Exploration, nested relationships   |

**Practical workflow**:

1. Use hierarchical clustering for exploration on a sample
2. Determine appropriate K and cluster characteristics
3. Use K-means on full dataset for production tiering

______________________________________________________________________

## Implementation Guide

### Python Ecosystem for Sports Analytics

#### Core Statistical & ML Libraries

**1. NumPy**

- Numerical operations, array manipulation
- Random number generation for simulations

```python
import numpy as np
```

**2. Pandas**

- Data manipulation, time series analysis
- Essential for wrangling player/game data

```python
import pandas as pd
```

**3. Scikit-learn**

- Comprehensive ML: regression, clustering, preprocessing
- Cross-validation, model selection

```python
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.cluster import KMeans
```

**4. Statsmodels**

- Statistical inference: t-tests, F-tests, diagnostics
- Detailed regression output (p-values, R², confidence intervals)
- GAMs via `statsmodels.gam`

```python
import statsmodels.api as sm
from statsmodels.gam.api import GLMGam, BSplines
```

**5. SciPy**

- Statistical distributions, hypothesis tests
- Distance metrics, hierarchical clustering

```python
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram
```

#### GAMs (Generalized Additive Models)

**PyGAM** (Python)

- Pythonic, scikit-learn compatible
- Automatic smoothing parameter selection

```python
from pygam import LinearGAM, LogisticGAM, s, f, te

# Example: Age curve with spline
gam = LinearGAM(s(0, n_splines=10))  # Smooth term for feature 0
gam.gridsearch(X_train, y_train)
gam.summary()
```

**mgcv** (R - Gold Standard)

- Most mature GAM implementation
- Automatic smoothness estimation (REML/GCV)
- Rich plotting and diagnostics

```r
library(mgcv)
model <- gam(points ~ s(age) + s(experience) + position, data=df)
plot(model)
```

#### Advanced Methods

**PyMC** (Bayesian Modeling)

- Hierarchical models for player talent estimation
- Uncertainty quantification

```python
import pymc as pm
```

**Prophet** (Facebook Time Series)

- Automatic seasonality and trend detection
- Good for player performance over career

```python
from prophet import Prophet
```

### Multicollinearity Diagnostics

**Variance Inflation Factor (VIF)**:

VIF measures how much variance of a coefficient is inflated due to multicollinearity.

**Formula**:

```
VIF_j = 1 / (1 - R²_j)
```

where R²_j is from regressing feature j on all other features.

**Interpretation**:

- VIF = 1: No correlation with other features
- VIF = 5: Moderate multicollinearity (investigate)
- VIF = 10+: Severe multicollinearity (action required)

**Solution strategies**:

1. Drop one of the highly correlated features
2. Combine correlated features (e.g., via PCA)
3. Use Ridge or Elastic Net regularization

**Python Implementation**:

```python
from statsmodels.stats.outliers_influence import variance_inflation_factor
import pandas as pd

def calculate_vif(X):
    """
    Calculate VIF for each feature in X.
    X: DataFrame or 2D array
    """
    vif_data = pd.DataFrame()
    vif_data["Feature"] = X.columns
    vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]

    return vif_data.sort_values('VIF', ascending=False)

# Example usage
vif_results = calculate_vif(X_train)
print(vif_results)

# Flag high VIF features
high_vif = vif_results[vif_results['VIF'] > 5]
if not high_vif.empty:
    print("\n⚠ High multicollinearity detected:")
    print(high_vif)
    print("\nConsider: Ridge/Lasso regression, removing features, or PCA")
```

**Advanced MI-VIF Method**:

Combines Mutual Information (feature importance) with VIF (multicollinearity):

- Maximize correlation between features and target (MI)
- Minimize collinearity among selected features (VIF)

Useful for automated feature selection with both criteria.

### Cross-Validation & Model Selection

**Standard K-Fold Cross-Validation**:

```python
from sklearn.model_selection import cross_val_score, KFold

# Create K-Fold splitter
kf = KFold(n_splits=5, shuffle=True, random_state=42)

# Evaluate model
scores = cross_val_score(model, X, y, cv=kf, scoring='neg_mean_squared_error')
rmse_scores = np.sqrt(-scores)

print(f"RMSE: {rmse_scores.mean():.2f} (+/- {rmse_scores.std():.2f})")
```

**Time Series Cross-Validation**:

For data with temporal structure (player performance over weeks), use expanding window:

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)

for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"Test R²: {score:.3f}")
```

**Nested Cross-Validation** (for hyperparameter tuning + unbiased evaluation):

```python
from sklearn.model_selection import cross_val_score, GridSearchCV

# Outer CV: unbiased model evaluation
outer_cv = KFold(n_splits=5, shuffle=True, random_state=42)

# Inner CV: hyperparameter tuning
inner_cv = KFold(n_splits=3, shuffle=True, random_state=42)

# Hyperparameter grid
param_grid = {'alpha': [0.1, 1.0, 10.0, 100.0]}

# Nested CV loop
outer_scores = []
for train_idx, test_idx in outer_cv.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # Inner loop: find best hyperparameters on training fold
    grid_search = GridSearchCV(Ridge(), param_grid, cv=inner_cv)
    grid_search.fit(X_train, y_train)

    # Evaluate best model on test fold
    score = grid_search.score(X_test, y_test)
    outer_scores.append(score)

print(f"Nested CV R²: {np.mean(outer_scores):.3f} (+/- {np.std(outer_scores):.3f})")
```

**Why nested CV?**: Prevents "double dipping" (using the same data for tuning and evaluation), which inflates performance estimates.

### Complete Pipeline Example

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

# 1. Load and prepare data
players_df = pd.read_csv('player_stats.csv')
X = players_df[['age', 'experience', 'targets', 'snap_share', 'opponent_rank']]
y = players_df['fantasy_points']

# 2. Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 3. Standardize features (important for regularized models)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 4. Compare multiple models with hyperparameter tuning
models = {
    'Ridge': Ridge(),
    'Lasso': Lasso(),
    'ElasticNet': ElasticNet()
}

param_grids = {
    'Ridge': {'alpha': [0.1, 1.0, 10.0, 100.0]},
    'Lasso': {'alpha': [0.01, 0.1, 1.0, 10.0]},
    'ElasticNet': {'alpha': [0.1, 1.0, 10.0], 'l1_ratio': [0.3, 0.5, 0.7]}
}

results = {}
for name, model in models.items():
    # Hyperparameter tuning with CV
    grid = GridSearchCV(
        model,
        param_grids[name],
        cv=5,
        scoring='neg_mean_squared_error',
        n_jobs=-1
    )
    grid.fit(X_train_scaled, y_train)

    # Evaluate on test set
    y_pred = grid.predict(X_test_scaled)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    results[name] = {
        'model': grid.best_estimator_,
        'best_params': grid.best_params_,
        'rmse': rmse,
        'r2': r2
    }

    print(f"{name}:")
    print(f"  Best params: {grid.best_params_}")
    print(f"  Test RMSE: {rmse:.2f}")
    print(f"  Test R²: {r2:.3f}\n")

# 5. Select best model
best_model_name = min(results, key=lambda x: results[x]['rmse'])
best_model = results[best_model_name]['model']
print(f"✓ Best model: {best_model_name}")

# 6. Analyze feature importance (for Lasso/ElasticNet)
if hasattr(best_model, 'coef_'):
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'coefficient': best_model.coef_
    }).sort_values('coefficient', key=abs, ascending=False)

    print("\nFeature Importance:")
    print(feature_importance)
```

______________________________________________________________________

## Best Practices & Common Pitfalls

### Data Preparation

#### 1. **Feature Scaling**

**Problem**: Regularized models (Ridge, Lasso) and distance-based methods (K-means) are sensitive to feature scales.

**Solution**: Always standardize features before modeling.

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)  # Use same transformation

# ⚠ Common mistake: fitting scaler on test set
# X_test_scaled = scaler.fit_transform(X_test)  # WRONG - causes data leakage
```

#### 2. **Handling Missing Data**

**Strategies**:

- Drop if < 5% missing and missing completely at random
- Mean/median imputation for numerical features
- Mode imputation for categorical features
- Forward-fill for time series
- Model-based imputation (KNN, iterative)

```python
from sklearn.impute import SimpleImputer, KNNImputer

# Simple approach
imputer = SimpleImputer(strategy='median')
X_imputed = imputer.fit_transform(X_train)

# Advanced: KNN imputation
knn_imputer = KNNImputer(n_neighbors=5)
X_imputed = knn_imputer.fit_transform(X_train)
```

⚠ **Caution**: Always fit imputer on training data only, then transform test data.

#### 3. **Data Leakage Prevention**

**What is data leakage?**: Using information from test set during training → inflated performance estimates.

**Common sources**:

- Fitting scaler/imputer on entire dataset before split
- Including future information in features (e.g., rest-of-season stats to predict current week)
- Target leakage: Features derived from target variable

**Prevention**:

```python
# ✓ CORRECT: Fit on train, transform test
scaler.fit(X_train)
X_train_scaled = scaler.transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ✗ WRONG: Fit on full data
scaler.fit(X)  # Leaks test set statistics into training
X_train_scaled = scaler.transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

### Model Evaluation

#### 1. **Train-Validation-Test Split**

**Best practice**: Use three-way split

- **Training set** (60-70%): Fit models
- **Validation set** (15-20%): Hyperparameter tuning, model selection
- **Test set** (15-20%): Final unbiased evaluation (touch ONLY ONCE)

```python
from sklearn.model_selection import train_test_split

# Split data
X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.25, random_state=42)

# Train on train set, tune on validation set
# Evaluate ONCE on test set at the very end
```

#### 2. **Metrics Selection**

Choose metrics aligned with your objective:

| Metric   | Use Case                      | Interpretation                       |
| -------- | ----------------------------- | ------------------------------------ |
| **MSE**  | Penalize large errors heavily | Squared units, sensitive to outliers |
| **RMSE** | Standard regression metric    | Same units as target                 |
| **MAE**  | Robust to outliers            | Average absolute error               |
| **R²**   | Variance explained            | 0 = baseline, 1 = perfect            |
| **MAPE** | Percentage error              | Interpretable, but breaks at y=0     |

```python
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
```

#### 3. **Residual Analysis**

Always check residuals to validate model assumptions:

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Compute residuals
residuals = y_test - y_pred

# 1. Residuals vs Fitted (check for patterns)
plt.scatter(y_pred, residuals, alpha=0.5)
plt.axhline(y=0, color='r', linestyle='--')
plt.xlabel('Fitted Values')
plt.ylabel('Residuals')
plt.title('Residual Plot')
plt.show()

# 2. Q-Q Plot (check normality)
from scipy import stats
stats.probplot(residuals, dist="norm", plot=plt)
plt.title('Q-Q Plot')
plt.show()

# 3. Histogram of residuals
plt.hist(residuals, bins=30, edgecolor='k')
plt.xlabel('Residuals')
plt.ylabel('Frequency')
plt.title('Residual Distribution')
plt.show()
```

**Red flags**:

- Systematic patterns in residuals → model is missing structure
- Non-constant variance (heteroscedasticity) → consider transformations or different model
- Non-normal residuals → outliers, or need robust methods

### Sports-Specific Considerations

#### 1. **Small Sample Sizes**

**Problem**: Early-season data has high variance (4 games \<< 17 games).

**Solutions**:

- Use Bayesian priors (preseason projections)
- Regression to the mean (see earlier section)
- Pool information across similar players (hierarchical models)
- Be conservative with predictions (wider intervals)

#### 2. **Position Effects**

**Problem**: QB, RB, WR, TE have different variance structures and scoring distributions.

**Solutions**:

- Model positions separately
- Use position as categorical feature with interactions
- Position-specific variance adjustments

```python
# Separate models by position
models = {}
for position in ['QB', 'RB', 'WR', 'TE']:
    pos_data = players_df[players_df['position'] == position]
    X_pos = pos_data[features]
    y_pos = pos_data['fantasy_points']

    model = Ridge(alpha=1.0)
    model.fit(X_pos, y_pos)
    models[position] = model
```

#### 3. **Context Matters**

**Don't forget**:

- Opponent strength (defensive rankings)
- Game environment (weather, altitude, home/away)
- Teammate quality (offensive line, QB for pass-catchers)
- Game script (blowouts → garbage time stats)

These contextual features often improve models significantly.

#### 4. **Injuries and Uncertainty**

**Strategies**:

- Probabilistic injury modeling (e.g., 70% chance to play → simulate both scenarios)
- Replacement-level baselines (VORP - Value Over Replacement Player)
- Portfolio approach (diversify to hedge injury risk)

### Common Mistakes to Avoid

| Mistake                                 | Why It's Bad                                                  | Fix                                             |
| --------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------- |
| **Not scaling features**                | Regularization, clustering biased toward large-scale features | Standardize with `StandardScaler`               |
| **Overfitting to training data**        | Model learns noise, performs poorly out-of-sample             | Use regularization, CV, simpler models          |
| **Using test set multiple times**       | Inflates performance, "overfits" to test set                  | Hold out test set, use only ONCE                |
| **Ignoring multicollinearity**          | Unstable coefficients, wrong feature importance               | Check VIF, use Ridge/Lasso/PCA                  |
| **Cherry-picking best result**          | Publication bias, misleading conclusions                      | Preregister analysis plan, report all models    |
| **Assuming causality from correlation** | Confounders, reverse causation                                | Use causal inference methods, domain knowledge  |
| **Extrapolating beyond data range**     | Models unreliable outside training distribution               | Be cautious with predictions for unusual inputs |
| **Forgetting uncertainty**              | Point predictions hide risk                                   | Report prediction intervals, distributions      |

### Validation Checklist

Before deploying a model, verify:

- [ ] **Data quality**: Missing values handled, outliers investigated
- [ ] **No data leakage**: Train-test split before any preprocessing
- [ ] **Features scaled**: Standardization for regularized/distance-based methods
- [ ] **Multicollinearity checked**: VIF < 5 for OLS, or use Ridge/Lasso
- [ ] **Cross-validation used**: K-fold or time series CV for robust evaluation
- [ ] **Hyperparameters tuned**: Grid search or random search with nested CV
- [ ] **Residuals analyzed**: No systematic patterns, approximately normal
- [ ] **Test set held out**: Evaluated only once at the end
- [ ] **Uncertainty quantified**: Prediction intervals or confidence bands
- [ ] **Domain sense-check**: Results align with expert knowledge
- [ ] **Reproducible**: Random seeds set, code version controlled

______________________________________________________________________

## References & Resources

### Key Papers & Articles

#### Regression in Sports Analytics

1. **South, C., & Egros, E. (2020)**. "Forecasting college football game outcomes using modern modeling techniques." *Journal of Sports Analytics*, 6(4), 303-315.

   - Comparison of OLS, Ridge, Lasso, and Elastic Net for game prediction
   - Finding: Lasso outperformed other methods

2. **Castelo Damasceno Dantas, N.** "Lasso Multinomial Performance Indicators for in-play Basketball Data." arXiv:2406.09895v2.

   - LASSO regression for basketball RAPM

3. **Kumar, C.** "Cricket Analytics using Variable Selection, Ridge Regression, LASSO, PCR, PLS and Random Forest." Medium.

   - Applied comparison of regularization techniques

#### GAMs and Age Curves

4. **Wakim, A., & Rios, N. (2014)**. "Functional Data Analysis of Aging Curves in Sports." arXiv:1403.7548.

   - Foundational work on modeling athlete aging with functional data analysis

5. **Nguyen, Q. (2022)**. "Estimating Aging Curves: Using Multiple Imputation." CMU Sports Analytics Conference.

   - Bayesian approaches to aging curves with missing data

6. **Page, G. L., et al. (2013)**. "Effect of position, usage, and per game minutes played on NBA player aging." *Annals of Operations Research*.

   - Regression and imputation methods for player aging estimation

7. **Matan K. (2023)**. "No Sport for Old Men: Baseball's Changing Aging Curve." Medium.

   - GAM analysis showing steeper aging curves in modern baseball era

8. **Turtoro, J. (2019)**. "Flexible aging in the NHL using GAM."

   - Application of GAMs to hockey performance trajectories

#### Monte Carlo Simulation

09. **Demsyn-Jones, R. (2019)**. "Misadventures in Monte Carlo." *Journal of Sports Analytics*, 5(1), 1-10.

    - Critical analysis of common mistakes in sports Monte Carlo simulations
    - Discusses error correlation problem and FiveThirtyEight's solution

10. **Freymiller, A. (2018)**. "A Monte Carlo Simulation of the 2017–18 Premier League Season." Medium.

    - Practical implementation for soccer season forecasting

#### Clustering and Portfolio Theory

11. **Ren, Z.** "Portfolio construction Using clustering Methods." Worcester Polytechnic Institute.

    - Comprehensive review of K-means and hierarchical clustering for diversification

12. **Various authors (2024)**. "Network and Clustering-based Portfolio Optimization: Enhancing Risk-Adjusted Performance through Diversification." Stevens Institute of Technology.

    - Modern approaches combining graph theory and clustering

### Online Resources

#### Statistical Learning

- **Penn State STAT 501**: Linear Regression

  - <https://online.stat.psu.edu/stat501/>
  - Comprehensive coverage of OLS, diagnostics, multicollinearity (VIF)

- **Penn State STAT 415**: Prediction Intervals

  - <https://online.stat.psu.edu/stat415/lesson/8>
  - Clear explanation of prediction vs confidence intervals

- **Introduction to Statistical Learning** (ISLR)

  - <https://www.statlearning.com/>
  - Free textbook covering regression, regularization, cross-validation

#### GAMs

- **Michael Clark's GAM Tutorial**

  - <https://m-clark.github.io/generalized-additive-models/>
  - Excellent introduction to GAMs with R examples

- **GAM: The Predictive Modeling Silver Bullet** (Stitch Fix)

  - <https://multithreaded.stitchfix.com/blog/2015/07/30/gam/>
  - Industry perspective on when and why to use GAMs

- **How to interpret and report nonlinear effects from GAMs**

  - <https://ecogambler.netlify.app/blog/interpreting-gams/>
  - Practical guidance on GAM interpretation and visualization

#### Python Implementation

- **Scikit-learn User Guide**

  - <https://scikit-learn.org/stable/user_guide.html>
  - Official documentation for regression, clustering, preprocessing, CV

- **Statsmodels Documentation**

  - <https://www.statsmodels.org/stable/index.html>
  - Statistical inference, detailed regression output, GAMs

- **PyGAM Documentation**

  - <https://pygam.readthedocs.io/>
  - Python library for Generalized Additive Models

- **Python for Data Analysis, 3E** (Wes McKinney)

  - <https://wesmckinney.com/book/>
  - Modeling libraries chapter covers scikit-learn, statsmodels

#### Sports Analytics Blogs & Communities

- **FiveThirtyEight**

  - <https://fivethirtyeight.com/sports/>
  - Industry-leading sports forecasting and methodology transparency

- **Towards Data Science - Sports Analytics**

  - <https://towardsdatascience.com/>
  - Many tutorials on ML for sports (search "sports analytics", "fantasy football")

- **r/fantasyfootball** (Reddit)

  - <https://www.reddit.com/r/fantasyfootball/>
  - Community-driven analysis, often includes statistical deep dives

- **Carnegie Mellon Sports Analytics Conference**

  - <https://www.stat.cmu.edu/cmsac/>
  - Annual conference with papers on cutting-edge sports analytics methods

#### Monte Carlo Simulation

- **Practical Business Python - Monte Carlo Simulation**

  - <https://pbpython.com/monte-carlo.html>
  - Step-by-step Python implementation guide

- **Analytics Vidhya - Monte Carlo Guide**

  - <https://www.analyticsvidhya.com/blog/2021/07/a-guide-to-monte-carlo-simulation/>
  - Comprehensive tutorial with examples

#### Uncertainty Quantification

- **DataCamp - Confidence vs Prediction Intervals**

  - <https://www.datacamp.com/blog/confidence-intervals-vs-prediction-intervals>
  - Clear explanation with examples

- **MachineLearningMastery - Prediction Intervals**

  - <https://machinelearningmastery.com/prediction-intervals-for-machine-learning/>
  - Practical guide for ML prediction intervals

#### Cross-Validation & Model Selection

- **MachineLearningMastery - Nested CV**

  - <https://machinelearningmastery.com/nested-cross-validation-for-machine-learning-with-python/>
  - When and how to use nested CV

- **Python Data Science Handbook - Model Validation**

  - <https://jakevdp.github.io/PythonDataScienceHandbook/05.03-hyperparameters-and-model-validation.html>
  - Hyperparameter tuning and CV best practices

### Books

1. **James, G., Witten, D., Hastie, T., & Tibshirani, R. (2021)**. *An Introduction to Statistical Learning* (2nd ed.).

   - Accessible introduction to regression, regularization, cross-validation
   - Free PDF available: <https://www.statlearning.com/>

2. **Hastie, T., Tibshirani, R., & Friedman, J. (2009)**. *The Elements of Statistical Learning* (2nd ed.).

   - More advanced treatment of statistical learning methods
   - Free PDF available: <https://hastie.su.domains/ElemStatLearn/>

3. **Wood, S. N. (2017)**. *Generalized Additive Models: An Introduction with R* (2nd ed.).

   - Definitive text on GAMs, focused on mgcv package in R

4. **Gelman, A., et al. (2013)**. *Bayesian Data Analysis* (3rd ed.).

   - Hierarchical modeling, uncertainty quantification
   - Essential for sports analytics with small samples

5. **McKinney, W. (2022)**. *Python for Data Analysis* (3rd ed.).

   - Practical guide to pandas, NumPy, and Python data science ecosystem

### Software & Libraries

#### Python

- **Scikit-learn**: ML library (regression, clustering, CV)

  - `pip install scikit-learn`

- **Statsmodels**: Statistical inference and GAMs

  - `pip install statsmodels`

- **PyGAM**: Generalized Additive Models

  - `pip install pygam`

- **SciPy**: Statistical functions and distributions

  - `pip install scipy`

- **NumPy**: Numerical computing

  - `pip install numpy`

- **Pandas**: Data manipulation

  - `pip install pandas`

- **Matplotlib / Seaborn**: Visualization

  - `pip install matplotlib seaborn`

#### R (Reference)

- **mgcv**: GAMs with automatic smoothing selection

  - `install.packages("mgcv")`

- **glmnet**: Lasso, Ridge, Elastic Net

  - `install.packages("glmnet")`

- **caret**: ML framework with unified interface

  - `install.packages("caret")`

______________________________________________________________________

## Summary & Quick Reference

### When to Use Each Method

| Method           | Best For                             | Key Advantage                   | Key Limitation                       |
| ---------------- | ------------------------------------ | ------------------------------- | ------------------------------------ |
| **OLS**          | Simple, interpretable baselines      | Unbiased, well-understood       | Overfits with many features          |
| **Ridge**        | Many correlated features             | Handles multicollinearity       | Keeps all features                   |
| **Lasso**        | Feature selection, sparse models     | Automatic feature selection     | Arbitrary selection with correlation |
| **GAM**          | Non-linear relationships, age curves | Flexibility + interpretability  | More complex, slower                 |
| **Monte Carlo**  | Complex scenario analysis            | Quantifies full uncertainty     | Only as good as input models         |
| **K-Means**      | Player tiering, known # of tiers     | Fast, simple                    | Requires K upfront                   |
| **Hierarchical** | Exploratory, nested structure        | Dendrogram, any distance metric | Slow for large data                  |

### Workflow Checklist

**1. Data Preparation**

- [ ] Handle missing values (impute or drop)
- [ ] Check for outliers and anomalies
- [ ] Split into train-validation-test sets
- [ ] Standardize features (for regularization, clustering)

**2. Modeling**

- [ ] Start with OLS baseline
- [ ] Check multicollinearity (VIF)
- [ ] Try Lasso for feature selection
- [ ] Try Ridge if many features are relevant
- [ ] Explore GAMs for non-linear effects
- [ ] Use cross-validation for model selection

**3. Evaluation**

- [ ] Check residuals for patterns
- [ ] Evaluate on held-out test set
- [ ] Calculate prediction intervals
- [ ] Validate against domain knowledge

**4. Production**

- [ ] Implement regression to the mean for in-season updates
- [ ] Use Monte Carlo for scenario analysis
- [ ] Communicate uncertainty (intervals, probabilities)
- [ ] Monitor model performance over time

### Python Quick Start Template

```python
# Standard imports
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

# 1. Load data
df = pd.read_csv('player_data.csv')
X = df[['age', 'experience', 'usage', 'opponent_rank']]
y = df['fantasy_points']

# 2. Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Scale
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 4. Model with CV
model = RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0], cv=5)
model.fit(X_train_scaled, y_train)

# 5. Evaluate
y_pred = model.predict(X_test_scaled)
print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.2f}")
print(f"R²: {r2_score(y_test, y_pred):.3f}")

# 6. Analyze
plt.scatter(y_test, y_pred, alpha=0.5)
plt.xlabel('Actual')
plt.ylabel('Predicted')
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
plt.show()
```

______________________________________________________________________

**End of Report**

*This research compilation provides a foundation for implementing statistical methods in sports analytics and player performance modeling. For specific implementation questions, consult the referenced papers, documentation, and online resources. Always validate models against domain knowledge and real-world outcomes.*
