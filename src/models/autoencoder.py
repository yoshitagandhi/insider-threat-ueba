import torch
import torch.nn as nn
import numpy as np
import pandas as pd

from src.baselines.personal_baseline import FEATURE_COLS
from src.utils.config import RANDOM_SEED

ZSCORE_COLS = [f"{c}_zscore" for c in FEATURE_COLS]


class BehaviorAutoencoder(nn.Module):
    def __init__(self, n_features: int, bottleneck: int = 4):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(n_features, 8),
            nn.ReLU(),
            nn.Linear(8, bottleneck),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck, 8),
            nn.ReLU(),
            nn.Linear(8, n_features),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


def train_autoencoder(daily: pd.DataFrame, epochs: int = 50, lr: float = 1e-3):
    """Train unsupervisedly on all score-ready observations.

    Ground-truth labels are evaluation-only data and must not affect training.
    """
    torch.manual_seed(RANDOM_SEED)
    train_df = daily.dropna(subset=ZSCORE_COLS)
    if train_df.empty:
        raise ValueError("No rows with complete z-score features are available for training.")
    X = torch.tensor(train_df[ZSCORE_COLS].values, dtype=torch.float32)

    model = BehaviorAutoencoder(n_features=len(ZSCORE_COLS))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        reconstructed = model(X)
        loss = loss_fn(reconstructed, X)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            print(f"epoch {epoch}, loss {loss.item():.4f}")

    return model


def score_autoencoder(model: BehaviorAutoencoder, daily: pd.DataFrame) -> pd.DataFrame:
    scored = daily.dropna(subset=ZSCORE_COLS).copy()
    model.eval()
    with torch.no_grad():
        X = torch.tensor(scored[ZSCORE_COLS].values, dtype=torch.float32)
        reconstructed = model(X)
        error = torch.mean((reconstructed - X) ** 2, dim=1)
    scored["ae_anomaly_score"] = error.numpy()
    return scored
