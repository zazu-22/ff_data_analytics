# Validation Strategies for Sports ML Models

## Critical Rule: Use Time-Series Validation

**Standard cross-validation CAUSES DATA LEAKAGE in sports analytics.**

❌ **Don't do this:**
```python
from sklearn.model_selection import KFold
cv = KFold(n_splits=5, shuffle=True)  # WRONG FOR SPORTS!
```

**Why it fails:** Shuffling mixes past and future data. Model "sees" future weeks during training, inflating performance by 15-20%.

## Correct Approaches

### 1. Time-Series Split (Expanding Window)

✅ **Use this:**
```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)

for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
```

**How it works:**
- Split 1: Train [Wk 1-4], Test [Wk 5]
- Split 2: Train [Wk 1-8], Test [Wk 9]
- Split 3: Train [Wk 1-12], Test [Wk 13]
- etc.

**Advantage:** Mimics real prediction scenario (training on past, predicting future)

### 2. Walk-Forward Validation (Sliding Window)

For detecting regime changes (new coaches, rule changes):

```python
window_size = 52  # Use last 52 weeks

for i in range(window_size, len(X)):
    train_start = i - window_size
    train_end = i
    test_idx = i

    X_train = X[train_start:train_end]
    X_test = X[test_idx:test_idx+1]

    model.fit(X_train, y_train)
    pred = model.predict(X_test)
```

**Advantage:** Adapts to recent trends, doesn't let old data dominate

**Disadvantage:** Smaller training sets

### 3. Blocked Cross-Validation

Group by player or season to prevent leakage:

```python
from sklearn.model_selection import GroupKFold

# Prevent same player appearing in train AND test
gkf = GroupKFold(n_splits=5)

for train_idx, test_idx in gkf.split(X, y, groups=player_ids):
    # Now same player never in both train and test
    model.fit(X[train_idx], y[train_idx])
    score = model.score(X[test_idx], y[test_idx])
```

**Use when:** Worried about player-specific overfitting

## Position-Specific Validation

Train and validate separately per position:

```python
for position in ['QB', 'RB', 'WR', 'TE']:
    mask = (df['position'] == position)
    X_pos = X[mask]
    y_pos = y[mask]

    tscv = TimeSeriesSplit(n_splits=5)
    for train_idx, test_idx in tscv.split(X_pos):
        # Position-specific model
        model_pos.fit(X_pos[train_idx], y_pos[train_idx])
```

## Nested Cross-Validation

For unbiased hyperparameter tuning:

```python
from sklearn.model_selection import GridSearchCV

# Outer loop: evaluate model generalization
outer_cv = TimeSeriesSplit(n_splits=5)

# Inner loop: tune hyperparameters
inner_cv = TimeSeriesSplit(n_splits=3)

param_grid = {'max_depth': [5, 7, 9], 'n_estimators': [100, 200]}

scores = []
for train_idx, test_idx in outer_cv.split(X):
    # Tune on inner loop
    grid_search = GridSearchCV(
        model, param_grid, cv=inner_cv, scoring='neg_mean_absolute_error'
    )
    grid_search.fit(X[train_idx], y[train_idx])

    # Evaluate best model on outer test set
    best_model = grid_search.best_estimator_
    score = best_model.score(X[test_idx], y[test_idx])
    scores.append(score)

print(f"True generalization score: {np.mean(scores)}")
```

## Appropriate Metrics

### Regression (Fantasy Points Prediction)

- **MAE (Mean Absolute Error):** Interpretable, robust to outliers
  - "Model is off by 3.2 fantasy points on average"
- **RMSE (Root Mean Squared Error):** Penalizes large errors more
- **R² (R-squared):** Proportion of variance explained
- **MAPE (Mean Absolute Percentage Error):** For relative accuracy

```python
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

mae = mean_absolute_error(y_test, predictions)
rmse = np.sqrt(mean_squared_error(y_test, predictions))
r2 = r2_score(y_test, predictions)
```

**Recommendation:** Use MAE as primary metric (most interpretable)

### Classification (Injury Prediction, Bust/Boom)

- **Accuracy:** Only if classes balanced
- **Precision/Recall:** When false positives/negatives have different costs
- **F1-Score:** Harmonic mean of precision and recall
- **ROC-AUC:** Probability-based, good for imbalanced classes

## Common Validation Mistakes

1. **Using shuffle=True in sports data** → Data leakage
2. **Not accounting for sample size differences** → TEs have fewer samples than WRs
3. **Tuning hyperparameters on test set** → Overfitting
4. **Ignoring temporal dependencies** → Autocorrelation in weekly stats
5. **Not validating on recent season** → Model may not generalize to current year

## Best Practice Workflow

**Step 1:** Split data by time
```python
# Hold out most recent season as final test
train_data = df[df['season'] < 2024]
test_data = df[df['season'] == 2024]
```

**Step 2:** Use TimeSeriesSplit on training data
```python
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(train_data):
    # Train and validate
    pass
```

**Step 3:** Tune hyperparameters with nested CV
```python
# Inner loop for tuning, outer loop for evaluation
```

**Step 4:** Final evaluation on held-out recent season
```python
final_score = model.score(test_data[features], test_data['fantasy_points'])
```

**Step 5:** Check position-specific performance
```python
for pos in positions:
    pos_test = test_data[test_data['position'] == pos]
    pos_score = mae(pos_test['fantasy_points'], pos_test['predictions'])
    print(f"{pos}: MAE = {pos_score:.2f}")
```

## Python Implementation

```python
from sklearn.model_selection import (
    TimeSeriesSplit,
    GroupKFold,
    GridSearchCV,
    cross_val_score
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

# Time-series split
tscv = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(
    model, X, y, cv=tscv, scoring='neg_mean_absolute_error'
)
print(f"CV MAE: {-scores.mean():.2f} (+/- {scores.std():.2f})")
```

**Sources:**
- scikit-learn documentation, sports analytics research, ML best practices literature
