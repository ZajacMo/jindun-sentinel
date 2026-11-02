"""Recurrent forecasting of a stress index (optional).

The LSTM engine mirrors the architecture of the original research — two
stacked LSTM layers with fifty units, a look-back of sixty observations and
a hundred epochs — but it is implemented on top of ``torch`` and it is
**optional**.  The pipeline never silently substitutes another engine for it:
if the dependency is missing the call fails with an explanation, because a
forecast published under the name of a model that was never fitted is worse
than no forecast at all.

Whether the LSTM is used at all is decided by the walk-forward backtest, not
by a preference; see :mod:`jindun.forecast.evaluate`.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["LstmFit", "lstm_available", "forecast_lstm"]


@dataclass(slots=True)
class LstmFit:
    """A fitted recurrent model and its forecast."""

    forecast: np.ndarray
    dates: list[str] = field(default_factory=list)
    train_loss: float = float("nan")
    validation_loss: float = float("nan")
    converged: bool = True
    notes: list[str] = field(default_factory=list)


def lstm_available() -> bool:
    """Whether the optional ``torch`` dependency is installed."""
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def _require_torch():
    try:
        import torch
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "the LSTM engine needs the optional 'ml' extra; install it with "
            "`uv sync --extra ml`. The ARIMA engine has no such requirement."
        ) from exc
    return torch


def forecast_lstm(
    series: pd.Series,
    *,
    horizon: int = 50,
    look_back: int = 60,
    units: int = 50,
    layers: int = 2,
    epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    train_ratio: float = 0.8,
    last_date: dt.date | None = None,
    seed: int = 20261103,
) -> LstmFit:
    """Fit a recurrent model on ``series`` and forecast ``horizon`` steps."""
    torch = _require_torch()

    clean = pd.Series(series).astype(float).dropna()
    if len(clean) < look_back * 3:
        raise ValueError(
            f"at least {look_back * 3} observations are required to fit the recurrent model"
        )

    values = clean.to_numpy(dtype=float)
    mean = float(values.mean())
    scale = float(values.std())
    if scale <= 0:
        scale = 1.0
    normalised = (values - mean) / scale

    windows = np.array(
        [
            normalised[index - look_back : index]
            for index in range(look_back, len(normalised))
        ],
        dtype="float32",
    )
    targets = normalised[look_back:].astype("float32")

    split = int(len(windows) * train_ratio)
    train_x, train_y = windows[:split], targets[:split]
    validation_x, validation_y = windows[split:], targets[split:]
    if len(validation_x) == 0:
        validation_x, validation_y = train_x, train_y

    torch.manual_seed(seed)

    class _Network(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lstm = torch.nn.LSTM(
                input_size=1,
                hidden_size=units,
                num_layers=layers,
                batch_first=True,
            )
            self.head = torch.nn.Linear(units, 1)

        def forward(self, batch):  # noqa: ANN001 - torch signature
            output, _ = self.lstm(batch)
            return self.head(output[:, -1, :])

    network = _Network()
    optimiser = torch.optim.Adam(network.parameters(), lr=learning_rate)
    loss_function = torch.nn.MSELoss()

    train_tensor = torch.from_numpy(train_x).unsqueeze(-1)
    train_target = torch.from_numpy(train_y).unsqueeze(-1)
    validation_tensor = torch.from_numpy(validation_x).unsqueeze(-1)
    validation_target = torch.from_numpy(validation_y).unsqueeze(-1)

    train_loss = float("nan")
    validation_loss = float("nan")
    network.train()
    for _ in range(max(1, epochs)):
        permutation = torch.randperm(len(train_tensor))
        epoch_loss = 0.0
        batches = 0
        for start in range(0, len(train_tensor), max(1, batch_size)):
            index = permutation[start : start + max(1, batch_size)]
            optimiser.zero_grad()
            prediction = network(train_tensor[index])
            loss = loss_function(prediction, train_target[index])
            loss.backward()
            optimiser.step()
            epoch_loss += float(loss.item())
            batches += 1
        train_loss = epoch_loss / max(1, batches)

        network.eval()
        with torch.no_grad():
            validation_loss = float(
                loss_function(network(validation_tensor), validation_target).item()
            )
        network.train()

    network.eval()
    history = list(normalised)
    predictions: list[float] = []
    with torch.no_grad():
        for _ in range(horizon):
            window = torch.from_numpy(
                np.asarray(history[-look_back:], dtype="float32")
            ).unsqueeze(0).unsqueeze(-1)
            next_value = float(network(window).item())
            predictions.append(next_value)
            history.append(next_value)

    forecast = np.asarray(predictions, dtype=float) * scale + mean

    dates: list[str] = []
    if isinstance(clean.index, pd.DatetimeIndex):
        anchor = clean.index[-1]
        step = clean.index[-1] - clean.index[-2]
        if step <= pd.Timedelta(0):
            step = pd.Timedelta(days=1)
        dates = [
            (anchor + step * (index + 1)).date().isoformat()
            for index in range(horizon)
        ]
    elif last_date is not None:
        dates = [
            (last_date + dt.timedelta(days=index + 1)).isoformat()
            for index in range(horizon)
        ]

    notes = [
        "the recurrent model is fitted on a normalised series and the forecast is "
        "transformed back; a model that predicts the mean will produce a flat line"
    ]
    if validation_loss > train_loss:
        notes.append(
            "the validation loss is above the training loss; the model is overfitting "
            "and its forecast should be treated with caution"
        )

    return LstmFit(
        forecast=forecast,
        dates=dates,
        train_loss=train_loss,
        validation_loss=validation_loss,
        converged=True,
        notes=notes,
    )
