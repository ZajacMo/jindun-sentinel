"""The global layer: cross-country contagion, the global cycle and the
cross-border banking network.

The global layer is deliberately built from the *same* methods as the country
layer, one level up:

* the cross-country contagion network uses the identical generalised variance
  decomposition as the cross-market network, with the country composites as
  the nodes — so the two networks are directly comparable;
* the global cycle factor is a principal component of the country composites;
* the cross-border banking network is built from the BIS locational banking
  statistics, which are the only public measure of who lends to whom across
  borders.

Nothing here is country specific: adding an economy means adding a country
configuration, not new code.
"""

from __future__ import annotations

from .banking_network import BankingNetwork, build_banking_network, load_banking_network
from .cross_country import cross_country_spillover, cross_country_spillover_all
from .cycle import CycleFactor, extract_cycle_factor
from .run import GLOBAL_ARTEFACTS, load_country_composites, run_global_layer

__all__ = [
    "BankingNetwork",
    "CycleFactor",
    "GLOBAL_ARTEFACTS",
    "build_banking_network",
    "cross_country_spillover",
    "cross_country_spillover_all",
    "extract_cycle_factor",
    "load_banking_network",
    "load_country_composites",
    "run_global_layer",
]
