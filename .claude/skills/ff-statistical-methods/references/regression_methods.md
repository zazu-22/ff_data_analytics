# Regression Methods for Fantasy Football Analytics

## When to Use Each Method

### Linear Regression (OLS)

**When to use:**
- Baseline model
- Need interpretable coefficients
- Relationship is approximately linear
- Small sample sizes

**Strengths:**
- Fast, simple, interpretable
- Well-understood statistical properties
- Hypothesis testing on coefficients

**Limitations:**
- Cannot capture non-linear relationships
- Assumes independence, homoscedasticity
- Sensitive to outliers

**Python:**
```python
from sklearn.linear_model import LinearRegression
from statsmodels.api import OLS

# sklearn (prediction focus)
model = LinearRegression()
model.fit(X_train, y_train)

# statsmodels (statistical inference)
import statsmodels.api as sm
X_with_const = sm.add_constant(X_train)
model = sm.OLS(y_train, X_with_const).fit()
print(model.summary())  # p-values, R², etc.
```

### Ridge Regression (L2 Regularization)

**When to use:**
- Multicollinearity among features
- Many correlated features (109 stat types!)
- Want to keep all features but shrink coefficients

**How it works:**
- Adds penalty: `Loss = MSE + α * Σ(coefficients²)`
- Shrinks coefficients toward zero (but not to zero)
- α controls regularization strength (higher = more shrinkage)

**Strengths:**
- Handles multicollinearity well
- Keeps all features
- More stable than OLS with correlated features

**Python:**
```python
from sklearn.linear_model import Ridge, RidgeCV

# Manual alpha
model = Ridge(alpha=1.0)

# Cross-validated alpha selection
model = RidgeCV(alphas=[0.1, 1.0, 10.0], cv=5)
model.fit(X_train, y_train)
print(f"Best alpha: {model.alpha_}")
```

### Lasso Regression (L1 Regularization)

**When to use:**
- High-dimensional data (many features)
- Want automatic feature selection
- Believe many features are irrelevant

**How it works:**
- Adds penalty: `Loss = MSE + α * Σ|coefficients|`
- Drives some coefficients exactly to zero
- Performs feature selection automatically

**Strengths:**
- Automatic feature selection
- Interpretable (sparse models)
- Handles high-dimensional data

**Research Finding:** Lasso outperformed Ridge/Elastic Net in college football prediction

**Python:**
```python
from sklearn.linear_model import Lasso, LassoCV

# Cross-validated alpha
model = LassoCV(alphas=[0.001, 0.01, 0.1, 1.0], cv=5)
model.fit(X_train, y_train)

# See which features were selected
selected_features = X.columns[model.coef_ != 0]
print(f"Selected {len(selected_features)} features")
```

### Elastic Net

**When to use:**
- High-dimensional data with correlated features
- Want balance of Ridge and Lasso benefits
- Default choice for fantasy football models

**How it works:**
- Combines L1 and L2: `Loss = MSE + α * (ρ * L1 + (1-ρ) * L2)`
- ρ = 0: Pure Ridge
- ρ = 1: Pure Lasso
- ρ = 0.5: Balanced

**Strengths:**
- Best of both worlds
- Feature selection + handles multicollinearity
- More stable than Lasso alone

**Python:**
```python
from sklearn.linear_model import ElasticNetCV

model = ElasticNetCV(
    l1_ratio=[0.1, 0.5, 0.7, 0.9, 0.95, 0.99],
    alphas=[0.001, 0.01, 0.1, 1.0],
    cv=5
)
model.fit(X_train, y_train)
print(f"Best l1_ratio: {model.l1_ratio_}, Best alpha: {model.alpha_}")
```

### Generalized Additive Models (GAMs)

**When to use:**
- Non-linear relationships (e.g., aging curves)
- Want to visualize smooth curves
- Need interpretability + flexibility

**How it works:**
- Fits smooth functions for each feature: `y = β₀ + f₁(x₁) + f₂(x₂) + ... + ε`
- Each f() is a smooth spline
- Can specify which features are non-linear

**Strengths:**
- Captures non-linear patterns (inverted-U age curves)
- Interpretable via partial dependence plots
- Automatic smoothing

**Use Cases:**
- Modeling aging curves (QB peaks at 28-33, RB declines post-27)
- Position-specific performance curves
- Experience effects on production

**Research Finding:** GAMs show baseball players peak at ~26-27, revealing non-linear age effects

**Python:**
```python
from pygam import LinearGAM, s, f

# s() = smooth term (non-linear), f() = factor term (categorical)
gam = LinearGAM(s(0) + s(1) + f(2))  # smooth age, smooth experience, factor position
gam.fit(X_train, y_train)

# Visualize smooth functions
import matplotlib.pyplot as plt
for i, term in enumerate(gam.terms):
    if term.isintercept:
        continue
    plt.figure()
    plt.plot(gam.partial_dependence(term=i))
    plt.title(f'Partial dependence of feature {i}')
```

**R (mgcv):**
```r
library(mgcv)
model <- gam(fantasy_points ~ s(age) + s(experience) + position, data=df)
summary(model)
plot(model, pages=1)
```

## Regression to the Mean

**Concept:** Extreme values tend to regress toward the average in subsequent measurements

**Fantasy Football Application:**
- Players with unusually high TD rates regress downward
- Players with low TD rates improve
- +TDOE declines 86%, -TDOE improves 93% next year

**Position-Specific Sample Sizes for 50% Regression:**
- QB: 21 games
- RB: 29-30 games
- WR: 13-14 games

**Implementation:**
```python
def apply_regression_to_mean(current_stat, position_mean, sample_size, position='WR'):
    """Apply regression to the mean"""
    # Sample sizes for 50% regression
    n_50 = {'QB': 21, 'RB': 30, 'WR': 14, 'TE': 20}

    # Regression factor
    regression_factor = sample_size / (sample_size + n_50[position])

    # Regressed estimate
    regressed = (regression_factor * current_stat) + ((1 - regression_factor) * position_mean)

    return regressed
```

## Confidence Intervals vs Prediction Intervals

**Confidence Interval:** Uncertainty in the estimated mean

**Prediction Interval:** Uncertainty for a new individual observation (always wider)

**Fantasy Use:** Prediction intervals for projecting individual player performance

```python
from scipy import stats
import numpy as np

def prediction_interval(model, X_new, confidence=0.95):
    """Calculate prediction interval for new observation"""
    predictions = model.predict(X_new)

    # Get residual standard error
    residuals = y_train - model.predict(X_train)
    rse = np.std(residuals)

    # t-score for confidence level
    t_score = stats.t.ppf((1 + confidence) / 2, len(y_train) - len(X_train.columns))

    # Prediction interval
    margin = t_score * rse
    lower = predictions - margin
    upper = predictions + margin

    return lower, upper
```

## Model Comparison

**Use Case:** Compare multiple regression approaches

```python
from sklearn.metrics import mean_absolute_error, r2_score

models = {
    'OLS': LinearRegression(),
    'Ridge': Ridge(alpha=1.0),
    'Lasso': Lasso(alpha=0.1),
    'Elastic Net': ElasticNet(alpha=0.1, l1_ratio=0.5)
}

results = {}
for name, model in models.items():
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    results[name] = {
        'MAE': mean_absolute_error(y_test, predictions),
        'R²': r2_score(y_test, predictions)
    }

# Print comparison
import pandas as pd
pd.DataFrame(results).T.sort_values('MAE')
```

## Practical Guidelines

**Start Simple:** Begin with OLS to establish baseline

**Check Assumptions:** Plot residuals to verify linearity, homoscedasticity

**Handle Multicollinearity:** Use Ridge or Elastic Net if VIF > 5

**Feature Selection:** Use Lasso if you have many irrelevant features

**Non-linearity:** Use GAMs for clear non-linear patterns (aging curves)

**Always Validate:** Use time-series cross-validation for sports data

**Sources:**
- scikit-learn, statsmodels, PyGAM documentation, sports analytics research
