"""Spillover and contagion analytics."""

from __future__ import annotations

from .gvd import (
    METHODS,
    GVDSpec,
    GVDSpecError,
    compute_spillover,
    compute_spillover_all,
    diebold_yilmaz_generalised_gvd,
    legacy_appendix_spillover,
    net_spillover,
    paper_equation_gvd,
    sims_structural_gvd,
    total_spillin,
    total_spillout,
)
from .surge import SurgeScore, rolling_spillout_history, spillout_surge_scores, surging_markets
from .var import VARFit, fit_var, impulse_response, select_var_order, vma_coefficients

__all__ = [
    "GVDSpec",
    "GVDSpecError",
    "METHODS",
    "SurgeScore",
    "VARFit",
    "compute_spillover",
    "compute_spillover_all",
    "diebold_yilmaz_generalised_gvd",
    "fit_var",
    "impulse_response",
    "legacy_appendix_spillover",
    "net_spillover",
    "paper_equation_gvd",
    "rolling_spillout_history",
    "select_var_order",
    "sims_structural_gvd",
    "spillout_surge_scores",
    "surging_markets",
    "total_spillin",
    "total_spillout",
    "vma_coefficients",
]
