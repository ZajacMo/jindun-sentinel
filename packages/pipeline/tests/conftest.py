"""Shared fixtures for the pipeline test suite."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(20261103)


@pytest.fixture
def indicator_panel(rng: np.random.Generator) -> pd.DataFrame:
    """A panel of correlated indicators in [0, 1]."""
    size = 260
    index = pd.date_range("2015-01-01", periods=size, freq="B")
    base = rng.normal(size=size)
    frame = pd.DataFrame(
        {
            "alpha": base + rng.normal(scale=0.5, size=size),
            "beta": base * 0.8 + rng.normal(scale=0.7, size=size),
            "gamma": rng.normal(size=size),
            "delta": -base * 0.4 + rng.normal(scale=1.0, size=size),
        },
        index=index,
    )
    return (frame - frame.min()) / (frame.max() - frame.min())


@pytest.fixture
def market_indices(rng: np.random.Generator) -> pd.DataFrame:
    """Five correlated market stress indices."""
    size = 600
    index = pd.date_range("2018-01-01", periods=size, freq="B")
    equity = rng.normal(size=size)
    frame = pd.DataFrame(
        {
            "equity": equity,
            "bond": 0.5 * equity + rng.normal(scale=0.8, size=size),
            "fx": 0.2 * equity + rng.normal(scale=1.0, size=size),
            "money": -0.3 * equity + rng.normal(scale=1.2, size=size),
            "derivative": 0.9 * equity + rng.normal(scale=0.5, size=size),
        },
        index=index,
    )
    return (frame - frame.min()) / (frame.max() - frame.min())


@pytest.fixture
def composite_series(rng: np.random.Generator) -> pd.Series:
    size = 400
    index = pd.date_range("2019-01-01", periods=size, freq="B")
    values = np.abs(rng.normal(loc=1.0, scale=0.3, size=size))
    values[200:215] += 1.5
    return pd.Series(values, index=index, name="composite")
