"""
Fantasy Football Player Projection Model Template

This template provides a starting point for building ML-based player projection models.
Includes feature engineering, model training, validation, and evaluation.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestRegressor, VotingRegressor
from sklearn.linear_model import Ridge
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

# =============================================================================
# 1. FEATURE ENGINEERING
# =============================================================================

def create_player_features(df):
    """
    Generate features for player projection model

    Args:
        df: DataFrame with player statistics

    Returns:
        DataFrame with engineered features
    """
    features = pd.DataFrame()

    # Age features (from feature_engineering.md)
    features['age'] = df['age']
    features['age_squared'] = df['age'] ** 2
    features['career_year'] = df['season'] - df['rookie_season']

    # Opportunity features
    features['target_share'] = df['targets'] / df['team_targets']
    features['snap_share'] = df['snaps'] / df['team_snaps']
    features['weighted_opportunities'] = df['carries'] + (df['targets'] * 1.5)

    # Efficiency features
    features['yprr'] = df['receiving_yards'] / df['routes_run'].replace(0, 1)
    features['ypc'] = df['rushing_yards'] / df['carries'].replace(0, 1)
    features['points_per_opportunity'] = df['fantasy_points'] / (df['carries'] + df['targets']).replace(0, 1)

    # Rolling features (3-game and 5-game averages)
    for window in [3, 5]:
        features[f'last_{window}_avg_fp'] = df.groupby('player_id')['fantasy_points'].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )

    # Position dummy variables
    features = pd.concat([features, pd.get_dummies(df['position'], prefix='pos')], axis=1)

    return features

# =============================================================================
# 2. MODEL TRAINING
# =============================================================================

def train_position_specific_models(X_train, y_train, positions):
    """
    Train separate models for each position

    Args:
        X_train: Training features
        y_train: Training target
        positions: Series of player positions

    Returns:
        Dictionary of position-specific models
    """
    models = {}

    for position in positions.unique():
        print(f"\nTraining {position} model...")

        # Filter to position
        pos_mask = (positions == position)
        X_pos = X_train[pos_mask]
        y_pos = y_train[pos_mask]

        if len(X_pos) < 50:  # Use simpler model for small samples
            model = Ridge(alpha=10)
        else:
            # Ensemble model
            model = VotingRegressor([
                ('ridge', Ridge(alpha=1.0)),
                ('rf', RandomForestRegressor(n_estimators=100, max_depth=7, random_state=42)),
                ('xgb', XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42))
            ], weights=[1, 2, 2])

        model.fit(X_pos, y_pos)
        models[position] = model

    return models

# =============================================================================
# 3. TIME-SERIES VALIDATION
# =============================================================================

def time_series_validate(X, y, model, n_splits=5):
    """
    Perform time-series cross-validation

    Args:
        X: Features
        y: Target
        model: Model to validate
        n_splits: Number of CV splits

    Returns:
        Dictionary of validation metrics
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    maes = []
    rmses = []
    r2s = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
        model.fit(X[train_idx], y[train_idx])
        predictions = model.predict(X[test_idx])

        mae = mean_absolute_error(y[test_idx], predictions)
        rmse = np.sqrt(mean_squared_error(y[test_idx], predictions))
        r2 = r2_score(y[test_idx], predictions)

        maes.append(mae)
        rmses.append(rmse)
        r2s.append(r2)

        print(f"Fold {fold}: MAE={mae:.2f}, RMSE={rmse:.2f}, R²={r2:.3f}")

    return {
        'mae_mean': np.mean(maes),
        'mae_std': np.std(maes),
        'rmse_mean': np.mean(rmses),
        'r2_mean': np.mean(r2s)
    }

# =============================================================================
# 4. EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Load your data (replace with actual data loading)
    # df = pd.read_parquet('path/to/player_stats.parquet')

    # Create features
    # features = create_player_features(df)

    # Train/test split by season
    # train_mask = df['season'] < 2024
    # X_train, y_train = features[train_mask], df.loc[train_mask, 'fantasy_points']
    # X_test, y_test = features[~train_mask], df.loc[~train_mask, 'fantasy_points']

    # Train position-specific models
    # models = train_position_specific_models(X_train, y_train, df.loc[train_mask, 'position'])

    # Validate
    # results = time_series_validate(X_train, y_train, models['WR'], n_splits=5)
    # print(f"\nOverall CV MAE: {results['mae_mean']:.2f} (+/- {results['mae_std']:.2f})")

    print("Template loaded. Replace example usage with actual data pipeline.")
