# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The **Unreleased** section describes the current state of the working tree. The
sections below it describe released versions.

## [Unreleased]

### Added

The initial monorepo: one uv workspace with the root project and three member packages,
plus one npm package and a shared locale catalogue at the repository root.

#### Pipeline — `packages/pipeline` (`jindun-pipeline`)

- Layered compute core under `src/jindun/`: `indicators` (GARCH volatility, log
  returns, first differences, z-score, EWMA volatility), `index` (CDF-rank
  normalisation by indicator direction, sub-market PCA, CRITIC objective weighting,
  the MBSED composite and its two reporting lenses), `regime` (HP-filter trend,
  Markov-switching autoregression, the two-component risk probability model),
  `contagion` (VAR estimation, generalised forecast error variance decomposition,
  spillover networks) and `global_layer` (cross-country contagion, the global cycle
  factor, the cross-border banking network and the G-SIB list).
- **Four spillover estimators**, each selectable through
  `contagion.method` and each carrying its own documented caveat:
  `paper_equation` (the default, implementing equations (6) and (7) of the source
  specification), `sims_structural` (Sims 1980 FEVD with Cholesky
  orthogonalisation), `dy_generalised` (Diebold-Yilmaz generalised FEVD, a signed
  quantity) and `legacy_appendix` (a literal transcription of the previously shipped
  code, retained so that published numbers can be regenerated).
  All four are now **published side by side in every artefact** under
  `spillover.estimators`, with the default one inlined at `spillover` itself.  The
  three that share a VAR fit use one fit, so publishing all four does not multiply
  the cost of a run; `legacy_appendix` needs a fit of its own because the shipped
  code used `lag_order = H = number of markets`.  An estimator that cannot be
  computed is listed in `spillover.failed_estimators` with its reason and never
  removes the others.
- **Capability metadata** in every run artefact: a `profile` (`mbsed` or
  `official_index`) and a `capabilities` map stating what the run can answer
  (`composite_synthesis`, `market_decomposition`, `market_attribution`,
  `spillover_network`, `regime`, `forecast`).  An economy measured by a published
  official index has no sub-market decomposition *by construction*, and this is now
  stated as data rather than left to be inferred from a missing section.
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
  `python -m jindun.cli`, with five subcommands: `sources` (the series the adapters
  can deliver and the coverage of every source), `fetch` (download the configured
  sources into the snapshot store), `run` (the full chain for one or more countries,
  writing the artefacts and the manifest), `global` (build the global layer from the
  country runs) and `verify` (re-evaluate the quality gates
  against the stored snapshots without recomputing the indices).
- **Two country profiles.** `mbsed` synthesises the composite from the sub-market
  indices; `official_index` uses a published official stress index and says in the
  artefact that no sub-market decomposition is available for that economy.
- **The spill-out surge test** (`contagion.surge`): the network is recomputed over
  rolling windows so that every market has a distribution of its own spill-out, and a
  surge is a z-score above the threshold *and* a material relative change.
- **Five economies.** China and Japan are measured with the full construction (the
  Japanese one from the Bank of Japan's daily call rates and the USD/JPY market);
  the United States, the United Kingdom and the euro area are measured with the
  official ECB composite stress index.

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
- **The estimator choice is part of the contract.**  `GET /api/v1/countries/{code}/spillover`
  and `GET /api/v1/global/spillover` take a `method` parameter, return the estimator that
  was asked for, and refuse an estimator the artefact does not publish with a `400` that
  lists the ones it does.  A request can never be answered with a different estimator
  than the one requested, and an unpublished horizon is refused the same way.
- **A designed absence is reported as one.**  An economy measured by a published
  official index has no cross-market network; the endpoint answers `404` with a
  structured `reason` (`not_applicable`) instead of a generic failure, so the front
  end can tell "this economy has no network" from "the computation failed".
- 14 tests that pin the contract against a miniature artefact tree, so the CI covers
  the API rather than only the compute core.
- OpenAPI documentation at `/api/docs`, the schema at `/api/openapi.json`.
- A read-only artefact store with a small in-process cache, so the number on the
  screen is the number in the run manifest.

#### Front end — `packages/web` (`@jindun/web`)

- Vue 3 application (Vite, TypeScript, Element Plus, ECharts, Pinia, vue-router,
  vue-i18n) with a typed API client, a store layer, shared formatting and label
  composables, and a Vite plugin that reads the shared locale catalogue at build
  time.
- Seven workspaces, each with a hand-written inline SVG **mechanism diagram** that
  shows what the page's computation actually does — the pipeline, the spillover
  decomposition, the regime model, the alerting loop, the global network and the
  quality gate.  The diagrams are mechanisms, not result charts.
- A language switcher and a theme toggle, with all four shipped locales
  left-to-right.
- An **estimator selector** on the spillover workspaces, so the four published
  estimators are a choice the reader makes rather than a distinction hidden in
  the documentation.
- The absence of a cross-market network for the three official-index economies
  is rendered as what it is — an explanation, not a failed request.
- 58 front-end tests, including a page-level smoke test that mounts every route and
  asserts that its diagram is present.

#### Agent — `packages/agent` (`jindun-agent`)

- A question answering layer over the same artefacts as the API: a language-neutral
  context pack, a registry of read-only tools and an orchestrator that renders a
  deterministic localised answer offline and asks an OpenAI-compatible endpoint when
  one is configured.
- The offline path never touches the network and never prints a number that does not
  appear in a published artefact; the prompt says the same to the model.

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
- **Japan** (`configs/countries/jp.yaml`): two sub-markets — the money market (the
  dispersion of the overnight call rate) and foreign exchange (the USD/JPY volatility
  and its deviation from trend) — built from the Bank of Japan's daily statistics, with
  three derived series computed in the adapter.
- **United States, United Kingdom and euro area** (`configs/countries/{us,gb,eu}.yaml`):
  the official ECB composite stress index, with the profile `official_index`.
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
- `scripts/set_locale_key.py`: the tool that adds a key to all four locale catalogues
  at once.  It refuses to write a key that is present in only some of the catalogues,
  so a half-translated key can never reach the tree.  `scripts/audit_locale_keys.py`
  checks afterwards that the four catalogues still agree.
- `scripts/serve_dev.py`: starts the API and the front end together, streams their
  output with a prefix and stops both on Ctrl-C, so the application can be run with
  one command instead of two terminals.

### Fixed

- **The contagion mechanism diagram drew the wrong nodes.**  It always showed the five
  Chinese sub-markets, even while the table above it listed five *countries* in the
  global layer.  It now follows the network that is actually on screen.  Its heading
  follows the selected estimator as well, and the box that holds the VAR's impulse
  responses is labelled with the step it draws (`spillover.impulseResponses`) instead
  of a method name.
- **The ECB CISS adapter built its URL with slashes between the dimensions.**  The
  SDMX key is a single path segment with dots, so every request answered 404 and the
  adapter silently returned no data for every economy.  It now returns 5 236
  observations for China and 12 226 for the United States.
- **The repository root was counted rather than discovered.**  Two modules sat one
  directory deeper than the others, so the snapshot store wrote into
  `packages/data/snapshots` and the locale catalogue resolved to an empty
  directory.  Both now go through `jindun.paths`, which finds the root by looking
  for the workspace manifest and a populated catalogue.
- **The walk-forward evaluation refitted the model at every origin.**  On a series
  of twelve thousand daily observations that is tens of thousands of model fits and a
  run that never finished.  The order is now chosen once on the first training
  window, the origins are strided and capped, and a run of the five economies takes
  about three minutes.
- **The regime model and the forecast used the whole history.**  A
  Markov-switching model with several lags on four decades of daily data is slow and
  over-parameterised; both now use the most recent 2 500 observations.
- **`pandas` 3 makes `to_numpy()` read-only.**  The attribution and the composite
  wrote into the result and failed; both copy first.
- **`from .global import …` does not parse** — `global` is a keyword.  The package
  that carries the global layer is called `global_layer`.
- **`Alert.state` was a string where the model expects the enum**, which broke the
  serialisation of the first alert that actually fired.
- The alert fired on a flat series: a single outlier among equal values always
  produces the same standardised distance.  A surge now needs a material relative
  change as well.
- The BIS bulk download stopped silently at a third of the file; it is now chunked,
  resumable and verified against the archive before it is published.

- Japan has two markets instead of five: the Bank of Japan publishes no daily equity
  index, no daily derivatives market and no daily government bond yield curve. The
  monthly and quarterly price databases are not mixed into the daily panel, because
  that would reduce the whole index to the frequency of its slowest component.
- The United States, the United Kingdom and the euro area are measured with the
  official ECB composite stress index and therefore have no sub-market decomposition,
  no market attribution and no cross-market spillover network.
- The bilateral BIS matrix is only served by the bulk archive, which is downloaded
  once into `data/cache/` and streamed into a filtered snapshot of about two
  megabytes under `data/snapshots/bis/`.
- The published table 5-2 of the source specification cannot be reproduced to the
  digit; `docs/methodology/spillover-legacy-vs-paper.md` states the evidence and the
  regression strategy that replaced it.
- `ruff check` is clean for the three Python packages. `mypy` still reports 22
  findings in the pipeline — annotation precision in the adapter layer, with no known
  runtime defect among them.

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
