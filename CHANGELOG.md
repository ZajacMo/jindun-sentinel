# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The **Unreleased** section describes the current state of the working tree. The
sections below it describe released versions.

## [Unreleased]

### Added

The initial monorepo: one uv workspace with the root project and two member packages,
plus one npm package and a shared locale catalogue at the repository root.

#### Pipeline — `packages/pipeline` (`jindun-pipeline`)

- Layered compute core under `src/jindun/`: `indicators` (GARCH volatility, log
  returns, first differences, z-score, EWMA volatility), `index` (CDF-rank
  normalisation by indicator direction, sub-market PCA, CRITIC objective weighting,
  the MBSED composite and its two reporting lenses), `regime` (HP-filter trend,
  Markov-switching autoregression, the two-component risk probability model),
  `contagion` (VAR estimation, generalised forecast error variance decomposition,
  spillover networks) and `global` (cross-country contagion, the global cycle factor).
- **Four spillover estimators**, each selectable through
  `contagion.method` and each carrying its own documented caveat:
  `paper_equation` (the default, implementing equations (6) and (7) of the source
  specification), `sims_structural` (Sims 1980 FEVD with Cholesky
  orthogonalisation), `dy_generalised` (Diebold-Yilmaz generalised FEVD, a signed
  quantity) and `legacy_appendix` (a literal transcription of the previously shipped
  code, retained so that published numbers can be regenerated).
- **Quality gates** (`jindun.quality`): eight named policy checks per series —
  `has_observations`, `enough_observations`, `unique_dates`, `ordered_dates`,
  `completeness`, `max_gap`, `freshness` and `value_bounds` — plus a
  `source_warning` check for every warning an adapter raised, with an explicit
  `ok` / `warning` / `failure` verdict. Staleness, gaps and low completeness are
  warnings; missing observations, duplicated dates, out-of-order dates and values
  outside the plausible range are failures, and a failure blocks the run.
- **Run manifest** (`jindun.manifest`): every run emits
  `manifest-<run_id>.json`, pinning the run id, the start time, the git commit and
  dirty flag, the artefact paths, the elapsed time and the warnings, so that a
  published number can be traced back to the payloads that produced it.
- **Read-only adapters** for the external services: `EcbCissAdapter` (ECB composite
  indicator of systemic stress), `BisAdapter` (BIS statistical API and bulk
  downloads), `BojAdapter` (Bank of Japan Time-Series Statistics Search API),
  `FsbAdapter` (FSB G-SIB list) and `AkshareAdapter` (Chinese market data, an
  optional dependency). Every response is written to a content-addressed snapshot
  store together with its URL, retrieval timestamp and SHA-256.
- **Configuration** in YAML, with no methodology parameter hard-coded in the compute
  code: `configs/global.yaml` (locales, index parameters, composite parameters,
  regime parameters, forecast parameters, contagion parameters, alert rules) and
  `configs/countries/*.yaml` (one file per economy).
- **Command line interface** `jindun-pipeline`, also runnable as
  `python -m jindun.cli`, with four subcommands: `sources` (the series the adapters
  can deliver and the coverage of every source), `fetch` (download the configured
  sources into the snapshot store), `run` (the full chain for one or more countries,
  writing the artefacts and the manifest) and `verify` (re-evaluate the quality gates
  against the stored snapshots without recomputing the indices).

#### API — `packages/api` (`jindun-api`)

- FastAPI application exposing the published artefacts as language-neutral
  payloads: numbers stay numbers, dates stay ISO-8601 strings and enumerations stay
  stable codes.
- Endpoints: `/api/v1/health`, `/api/v1/run-metadata`, `/api/v1/locales`,
  `/api/v1/messages`, `/api/v1/countries`,
  `/api/v1/countries/{code}/index`, `/api/v1/countries/{code}/spillover`,
  `/api/v1/countries/{code}/alerts`, `/api/v1/countries/{code}/data-quality`,
  `/api/v1/global/spillover`, `/api/v1/global/cycle`,
  `/api/v1/global/banking-network` and `/api/v1/global/gsib`.
- OpenAPI documentation at `/api/docs`, the schema at `/api/openapi.json`.
- A read-only artefact store with a small in-process cache, so the number on the
  screen is the number in the run manifest.

#### Front end — `packages/web` (`@jindun/web`)

- Vue 3 application (Vite, TypeScript, Element Plus, ECharts, Pinia, vue-router,
  vue-i18n) with a typed API client, a store layer, shared formatting and label
  composables, and a Vite plugin that reads the shared locale catalogue at build
  time.
- A language switcher and a theme toggle, with all four shipped locales
  left-to-right.

#### Locales

- **Four locale catalogues** at `locales/`: `en-US.json`, `zh-CN.json`, `zh-TW.json`
  and `ja-JP.json`. Simplified and Traditional Chinese are written by hand rather
  than converted, because the financial vocabulary differs between them.
- The catalogue is the single source of truth, shared by the server
  (`jindun.i18n`) and the front end (the Vite locale-catalogue plugin), so a report,
  a push notification and an on-screen label cannot drift apart.

#### Country configuration

- **China** (`configs/countries/cn.yaml`): five sub-markets — equity, bond, fx, money
  and derivative — with 11 enabled indicators and 4 indicators kept with
  `enabled: false` because their original source is a commercial terminal or a
  research construction and no free verified feed exists for them.
- The ECB CISS daily composite is registered as China's external cross-check
  anchor.

#### Repository

- Apache License 2.0, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` and
  this changelog.
- `docs/methodology/spillover-legacy-vs-paper.md`: the published specification, the
  code that actually shipped, the current estimators, and a quantified account of why
  the originally published matrix cannot be reproduced bit for bit.
- `data/baseline/`: the vendored regression assets and their provenance, and
  `scripts/freeze_baseline.py` to regenerate them.

### Known limitations

- Only the China country configuration is shipped. The United States, the euro area,
  the United Kingdom and Japan have their cross-check anchors identified, but no
  configuration file yet.
- The `jindun.global` package cannot be imported:
  `packages/pipeline/src/jindun/global/banking_network.py` is missing from the tree.
  `global/cycle.py` and `global/cross_country.py` are present.
- No CLI subcommand writes the global artefacts, so the four `/api/v1/global/*`
  endpoints answer 404 until `data/runs/global/*.json` exists.
- The web front end is under active development and its build is not green at the time
  of writing: `src/router/index.ts` defines seven pages and the page, chart and diagram
  components under `packages/web/src/` are still being added to match it.
  `npm run typecheck` and `npm run build` in `packages/web` are the acceptance gates.
- The front end requests `/api/v1/data-quality/{code}` while the API serves
  `/api/v1/countries/{code}/data-quality`.
- The `spillout.surge` alert rule is declared in `global.yaml`, but its firing
  condition is not implemented.
- `uv sync` fails on the current tree: the workspace member glob `packages/*` also
  matches `packages/data`, the snapshot store's default directory, which has no
  `pyproject.toml`.
- `jindun.i18n` resolves the catalogue to the empty `packages/pipeline/locales`
  directory in a source checkout; set `JINDUN_LOCALE_DIR` to the repository's
  `locales/` directory.
- No continuous integration is configured: `.github/workflows` and
  `.github/ISSUE_TEMPLATE` are empty.
- The test suite passes (51 tests), but the static-analysis checks do not:
  `ruff check` reports 61 findings in the pipeline and 14 in the API,
  `ruff format --check` would reformat 23 files, and `mypy` reports 43 errors in 24 of
  46 files.

## [0.1.0] - 2026-11-03

The first release of the pipeline, the API and the front end.

### Added

- `jindun-pipeline` 0.1.0 — the computation core: normalisation, sub-market PCA,
  the MBSED composite, regime identification, the risk probability model, four
  spillover estimators, the quality gates and the run manifest.
- `jindun-api` 0.1.0 — the FastAPI server over the published artefacts, with the
  documentation at `/api/docs`.
- `@jindun/web` 0.1.0 — the Vue 3 front end.
- Four locale catalogues and the China country configuration.
- The `jindun-pipeline` console script, and the `jindun-pipeline sources`,
  `jindun-pipeline fetch`, `jindun-pipeline run` and `jindun-pipeline verify`
  subcommands.

### Notes

- Requires Python 3.11 or newer.
- Optional extras: `arch`, `market` (akshare), `ml`, `dev`.
- The package is published under the Apache License 2.0.

[Unreleased]: https://github.com/ZajacMo/jindun-sentinel/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ZajacMo/jindun-sentinel/releases/tag/v0.1.0
