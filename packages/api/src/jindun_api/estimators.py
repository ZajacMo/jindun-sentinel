"""Selection of the published spillover estimator.

The artefacts publish every estimator side by side, because the estimators
answer different questions and are not interchangeable: the generalised
decomposition is signed, the structural one depends on the variable ordering
and the legacy one is not a forecast error variance decomposition at all.

A client therefore asks for one explicitly, and an estimator that was not
computed is *refused* with the list of the ones that were — never silently
replaced by a different one, which is the failure mode this module exists to
prevent.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

__all__ = ["select_estimator"]


def select_estimator(
    block: dict[str, Any],
    *,
    scope: str,
    method: str | None = None,
    horizon: int | None = None,
) -> tuple[dict[str, Any], str, list[str]]:
    """Pick the requested estimator out of a published spillover block.

    Returns ``(block, method, available methods)``.  Raises a ``400`` when the
    requested estimator or horizon was not computed: the artefact publishes
    exactly one horizon and a fixed set of estimators, and answering with a
    different number than the one asked for would be a silent misalignment.
    """
    estimators = block.get("estimators") or {}
    default_method = block.get("default_method") or block.get("method") or "paper_equation"
    available = sorted(estimators) if estimators else [default_method]
    selected = method or default_method

    if estimators and selected not in estimators:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    f"the artefact for {scope!r} does not publish the estimator {selected!r}"
                ),
                "reason": "unknown_method",
                "available_methods": available,
            },
        )
    chosen = estimators.get(selected, block) if estimators else block

    published_horizon = int(chosen.get("horizon") or 0)
    if horizon is not None and published_horizon and horizon != published_horizon:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    f"the artefact for {scope!r} publishes a horizon of {published_horizon}; "
                    f"horizon {horizon} was not computed"
                ),
                "reason": "unknown_horizon",
                "available_horizons": [published_horizon],
            },
        )
    return chosen, selected, available
