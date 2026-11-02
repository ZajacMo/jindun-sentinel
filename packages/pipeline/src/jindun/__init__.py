"""JinDun Sentinel computation pipeline.

The package is deliberately layered so that every stage can be tested in
isolation and re-used by the API server, the CLI and the research scripts:

``indicators``
    Normalisation and directional transforms of raw tertiary indicators.
``index``
    Sub-market PCA, CRITIC weighting and the MBSED composite index.
``regime``
    HP filter, Markov-switching regime model and the risk probability model.
``contagion``
    VAR estimation, generalized forecast error variance decomposition and the
    spillover networks.
``adapters`` (added in the data-access milestone)
    Read-only connectors to the external data sources.

Every public object is language neutral: identifiers are stable codes and
display strings live in the shared locale catalogues.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
