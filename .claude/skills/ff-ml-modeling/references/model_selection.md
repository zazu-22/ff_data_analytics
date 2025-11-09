# Model Selection for Fantasy Football Predictions

## Decision Framework

```
Primary Goal?
├─ Interpretability
│  ├─ Linear/Logistic Regression (baseline + interpretable coefficients)
│  └─ Ridge/Lasso with Regularization (handles multicollinearity)
│
└─ Predictive Performance
   ├─ Small Sample (<1000 rows)
   │  ├─ Ridge/Lasso Regression
   │  └─ Elastic Net
   │
   ├─ Medium Sample (1000-10000)
   │  ├─ Random Forest (robust, handles non-linearity)
   │  └─ XGBoost/Gradient Boosting (typically best single model)
   │
   └─ Large Sample (>10000)
       ├─ XG Boost/LightGBM (speed + performance)
       ├─ Neural Networks (if non-linear patterns complex)
       └─ Ensemble (voting/stacking multiple models)
```

## Model Types

### 1. Linear Regression

**When to Use:**
- Baseline model establishment
- Need interpretable coefficients
- Small samples where complex models overfit

**Advantages:** Fast, explainable, stable with limited data

**Disadvantages:** Cannot capture non-linear patterns, assumes feature independence

### 2. Regularized Regression (Ridge/Lasso/Elastic Net)

**When to Use:**
- High-dimensional data (109 stat types!)
- Multicollinearity among features
- Automatic feature selection (Lasso)

**Lasso (L1):** Drives coefficients to zero → automatic feature selection

**Ridge (L2):** Shrinks coefficients → handles multicollinearity

**Elastic Net:** Combines both (recommended for fantasy football)

**Sports Finding:** Lasso outperformed Ridge/Elastic Net in college football prediction

### 3. Random Forest

**When to Use:**
- Medium-sized datasets
- Non-linear relationships
- Want feature importance rankings
- Robust to outliers

**Advantages:** Handles mixed data types, minimal tuning, interpretable via feature importance

**Disadvantages:** Can overfit with noisy features, slower than linear models

**Hyperparameters:**
- n_estimators: 100-500 trees
- max_depth: 10-30 (deeper for more complexity)
- min_samples_split: 2-10

### 4. XGBoost / LightGBM

**When to Use:**
- Want best single-model performance
- Have enough data (>1000 samples)
- Can invest time in hyperparameter tuning

**Advantages:** Typically leads in sports ML competitions, handles missing values, fast

**Disadvantages:** More hyperparameters to tune, can overfit without regularization

**Key Hyperparameters:**
- learning_rate: 0.01-0.1 (lower = more robust)
- max_depth: 3-7 (shallower for fantasy to avoid overfitting)
- n_estimators: 100-1000
- subsample: 0.6-0.9 (reduces overfitting)

**Research Finding:** XGBoost + Random Forest voting ensembles consistently achieve highest accuracy in sports

### 5. Ensemble Methods

**Voting:** Combine predictions from multiple models (average or weighted)

**Stacking:** Use meta-model to learn how to combine base models

**Recommended Ensemble:**
```python
from sklearn.ensemble import VotingRegressor

ensemble = VotingRegressor([
    ('ridge', Ridge(alpha=1.0)),
    ('rf', RandomForestRegressor(n_estimators=200)),
    ('xgb', XGBRegressor(learning_rate=0.05))
], weights=[1, 2, 2])  # Weight tree models higher
```

## Sports-Specific Considerations

### Small Sample Sizes

**Problem:** NFL has 17 games/season, limited data per player

**Solutions:**
- Use regularization (Ridge, Lasso, Elastic Net)
- Hierarchical models (pool similar players)
- Transfer learning from similar positions
- Bayesian priors (incorporate domain knowledge)

### Position-Specific Modeling

**Recommendation:** Train separate models per position

**Why:**
- RB features ≠ WR features ≠ QB features
- Age curves differ by position
- Opportunity metrics vary (carries vs targets vs pass attempts)

```python
# Position-specific pipeline
models = {
    'QB': XGBRegressor(max_depth=5),
    'RB': RandomForestRegressor(max_depth=7),
    'WR': XGBRegressor(max_depth=6),
    'TE': Ridge(alpha=10)  # Fewer samples, use simpler model
}

for position, model in models.items():
    X_pos = X[X['position'] == position]
    y_pos = y[X['position'] == position]
    model.fit(X_pos, y_pos)
```

### Handling Regime Changes

**Challenges:**
- Rule changes (extra game in 2021)
- Coaching changes
- New offensive schemes

**Solutions:**
- Weight recent seasons heavier (exponential decay)
- Include year as feature (captures meta-trends)
- Use expanding window validation (see validation_strategies.md)

## Model Selection Workflow

**Step 1: Establish Baseline**
- Simple linear regression or Marcel-style weighted average
- Provides floor performance to beat

**Step 2: Try Regularized Linear Model**
- Ridge/Lasso/Elastic Net
- Check if regularization helps with multicollinearity

**Step 3: Test Tree-Based Model**
- Random Forest first (robust, less tuning)
- XGBoost if you have time for hyperparameter tuning

**Step 4: Position-Specific Models**
- Train separate models per position
- Compare to unified model

**Step 5: Ensemble Top Performers**
- Combine best 2-3 models via voting
- Often 2-5% improvement over single model

**Step 6: Evaluate on Holdout**
- Use time-series validation (see validation_strategies.md)
- Check MAE, RMSE, R² on recent season

## Hyperparameter Tuning

Use **nested cross-validation** to avoid overfitting:

```python
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

# Outer loop: model evaluation
outer_cv = TimeSeriesSplit(n_splits=5)

# Inner loop: hyperparameter tuning
inner_cv = TimeSeriesSplit(n_splits=3)

param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [5, 7, 9],
    'learning_rate': [0.01, 0.05, 0.1]
}

model = GridSearchCV(
    XGBRegressor(),
    param_grid,
    cv=inner_cv,
    scoring='neg_mean_absolute_error'
)

# Evaluate on outer loop
for train_idx, test_idx in outer_cv.split(X):
    model.fit(X[train_idx], y[train_idx])
    score = model.score(X[test_idx], y[test_idx])
```

## Common Mistakes

1. **Not using time-series validation** → Data leakage, inflated metrics
2. **Over-tuning on small datasets** → Overfitting
3. **Ignoring position differences** → One-size-fits-all fails
4. **Chasing complexity** → Simple models often win with good features
5. **Not establishing baseline** → Don't know if complexity helps

## Python Implementation

```python
# Recommended starter stack
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, VotingRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

# Feature selection
from sklearn.feature_selection import SelectFromModel

# Hyperparameter tuning
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

# Evaluation
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
```

**Sources:**
- NumberAnalytics, Medium NFL ML articles, scikit-learn documentation, XGBoost/LightGBM docs
