# User guide

How to install JinDun Sentinel, run it, read what it publishes and query it.

For a five-minute version read [`quickstart.md`](quickstart.md); this page is
the reference.

## Contents

| section | what it covers |
| --- | --- |
| [1. Install](#1-install) | the Python workspace and the front end |
| [2. Run the daily pipeline](#2-run-the-daily-pipeline) | the five commands of `jindun-pipeline` |
| [3. A worked example](#3-a-worked-example) | one full cycle, from the sources to the screen |
| [4. Read the artefacts](#4-read-the-artefacts) | what every published file contains |
| [5. The API](#5-the-api) | every endpoint, its parameters and its response |
| [6. The agent](#6-the-agent) | asking a question instead of reading a chart |
| [7. Where the data comes from](#7-where-the-data-comes-from) | the snapshot store and the cache |

## 1. Install

The Python side is a [uv](https://docs.astral.sh/uv/) workspace. The root
`pyproject.toml` declares `packages/*` as its members, so one command installs
the pipeline, the API and the analyst agent together:

```bash
uv sync --extra dev --extra market --all-packages
```

| extra | provided by | what it adds |
| --- | --- | --- |
| `dev` | the root project, `jindun-pipeline`, `jindun-api`, `jindun-agent` | `pytest`, `pytest-cov`, `ruff`, `mypy` |
| `market` | `jindun-pipeline` | `akshare`, the Chinese market data source |
| `arch` | `jindun-pipeline` | `arch`, the GARCH volatility model |
| `ml` | `jindun-pipeline` | `torch`, for the LSTM forecast engine |
| `llm` | `jindun-agent` | `httpx`, for the optional model endpoint |

Without the `market` extra the pipeline still installs and still runs: every
Chinese indicator is then reported as unavailable with a warning, never as a
silent zero.

The front end is a separate npm package and is not part of the uv workspace:

```bash
cd packages/web
npm install
```

Python 3.11 or newer is required; the CI tests 3.11, 3.12 and 3.13. Node 22 and
npm 10 are expected for the front end.

## 2. Run the daily pipeline

The command is `jindun-pipeline`, or `python -m jindun.cli` if the console
script is not on the path. Two global options come before the subcommand:

| option | meaning |
| --- | --- |
| `--config <path>` | the configuration directory (or a single YAML file) to read instead of `packages/pipeline/configs` |
| `--snapshot-dir <path>` | where the raw source payloads are cached, instead of `data/snapshots` |

### `sources` — what the adapters can deliver

```bash
jindun-pipeline sources
```

Prints JSON: the configured countries with their market and indicator counts,
every registered `akshare` series, the ECB CISS reference areas, the BIS flows
and the BOJ databases. Nothing is downloaded; this is the inventory.

### `fetch` — download the configured sources

```bash
jindun-pipeline fetch                      # every enabled country
jindun-pipeline fetch --country CN         # one country (repeatable)
jindun-pipeline fetch --refresh            # ignore the snapshot cache
```

Each response is written to the snapshot store with its URL, its retrieval
timestamp and the SHA-256 of the payload, so a later run can be replayed from
the same bytes. The command prints one line per series and exits **1** if any
series came back empty.

### `run` — execute the chain and publish the artefacts

```bash
jindun-pipeline run
jindun-pipeline run --country CN --out data/runs
jindun-pipeline run --refresh
```

Writes one directory per country and one manifest per run; the layout is in
[§4](#4-read-the-artefacts). The command exits **1** if any country's quality
report contains a failure.

### `verify` — re-check the gates without recomputing

```bash
jindun-pipeline verify
jindun-pipeline verify --country CN
```

Re-evaluates the quality gates against the stored snapshots and prints the
report as JSON. Exits **1** when the report contains a failure. Use it to
answer "would today's data pass?" without spending a run on it.

### `global` — build the global layer

```bash
jindun-pipeline global
jindun-pipeline global --country CN --country JP
jindun-pipeline global --banking-snapshot data/snapshots/bis/lbs_bilateral.csv
```

| option | meaning |
| --- | --- |
| `--country <code>` | the countries to include (repeatable); the default is every enabled country |
| `--out <path>` | where to write the artefacts; the default is `data/runs/global` |
| `--banking-snapshot <path>` | the filtered BIS bilateral snapshot; the default is `data/snapshots/bis/lbs_bilateral.csv` |
| `--refresh` | ignore the snapshot cache |

Writes four files into `data/runs/global/`: `spillover.json` (the cross-country
network), `cycle.json` (the global financial cycle factor), `banking_network.json`
(the BIS cross-border banking network) and `gsib.json` (the FSB G-SIB list).
The cross-country network needs at least two country runs; with fewer, the
artefact is still written, with an empty node set and a note saying why.

## 3. A worked example

One full cycle, from the raw sources to a number on the screen.

```bash
# 1. What can be fetched at all?
jindun-pipeline sources

# 2. Download today's payloads (cached; add --refresh to force a re-download).
jindun-pipeline fetch --country CN

# 3. Would the data pass the gates? (cheap; uses the cache only)
jindun-pipeline verify --country CN

# 4. Compute and publish.
jindun-pipeline run --country CN

# 5. Build the global layer from the country runs.
jindun-pipeline global
```

Step 4 prints something like:

```
[run] CN: as of 2026-11-03, 1121 market observations, 0 alerts
       warning: method paper_equation; VAR order 2 (selected by bic); horizon 10; sample 2017-03-30–2026-10-30
       warning: CN: cn.equity.sse_composite_volume -> warning

manifest: F:\Projects\03_projects\jindun-sentinel\data\runs\manifest-2026-11-03T02-15-44Z.json
```

and step 5 prints the four global artefacts:

```
[global] spillover: ...\data\runs\global\spillover.json
[global] cycle: ...\data\runs\global\cycle.json
[global] banking_network: ...\data\runs\global\banking_network.json
[global] gsib: ...\data\runs\global\gsib.json
```

Now read the number:

```bash
python -c "import json;d=json.load(open('data/runs/CN/run.json',encoding='utf-8'));\
print(d['as_of'], d['percentile'][-1], d['regime']['labels'][-1])"
```

```
2026-11-03 {'date': '2026-11-03', 'value': 0.5534} high
```

and serve it:

```bash
python scripts/serve_dev.py        # API on :8000, front end on :5173
```

## 4. Read the artefacts

A run publishes four kinds of file. The API serves exactly these; it never
recomputes an index.

### `data/runs/<CODE>/run.json` — the country run

| key | content |
| --- | --- |
| `country_code`, `as_of` | the economy and the date the run belongs to |
| `profile` | `mbsed` (the index is synthesised) or `official_index` (it is a published official index) |
| `capabilities` | what this run can answer: `composite_synthesis`, `market_decomposition`, `market_attribution`, `spillover_network`, `regime`, `forecast` — each `true`/`false` |
| `market_indices` | `dates` (ISO-8601) and `series` (one array per sub-market) |
| `composite`, `percentile`, `deviation` | three arrays of `{date, value}`: the composite in its own units, its within-country percentile and its deviation from the country's own trend |
| `regime` | `dates`, `labels` (`moderate`/`high`), `probability_moderate`, `probability_high` and the fitted `params` |
| `spillover` | the default network, plus `default_method`, `estimators` (every published estimator side by side), `failed_estimators` (with the reason) and `spillout_history` (the rolling windows behind the surge alert) |
| `alerts` | the alerts that fired, with their severity, state, message key and parameters |
| `attribution` | the decomposition of the last move into its market contributions |
| `forecast` | the ARIMA forecast with its walk-forward score |
| `warnings` | everything that went wrong, as a catalogue key and the facts that fill it — never as a finished sentence, so the reader gets it in their own language |

`profile` and `capabilities` matter: an economy measured by an official index
has no sub-market decomposition *by construction*, and the artefact says so
instead of publishing a decomposition that was never computed.

### `data/runs/<CODE>/quality.json` — the quality verdict

| key | content |
| --- | --- |
| `generated_at` | when the verdict was produced |
| `passed` | `false` if any series failed a gate |
| `counts` | `total`, `ok`, `warning`, `failure` |
| `series` | one entry per series: `series_id`, `adapter`, `country_code`, `severity`, `passed`, `observations`, `first_date`, `last_date` and the `checks` |

Every check is named and carries the measured value and the threshold it
breached: `has_observations`, `enough_observations`, `unique_dates`,
`ordered_dates`, `completeness`, `max_gap`, `freshness` and, when a range is
configured, `value_bounds`. A stale series is a **warning**; a broken one is a
**failure** and blocks the run.

### `data/runs/<CODE>/market_indices.csv` — the sub-market indices

A CSV with an ISO-8601 date in the first column and one column per sub-market
(`equity`, `bond`, `fx`, `money`, `derivative` for China; `money` and `fx` for
Japan). This is the file to load into a spreadsheet or a notebook.

### `data/runs/manifest-<run_id>.json` — the run manifest

| key | content |
| --- | --- |
| `run_id`, `started_at`, `elapsed_sec` | the identity and the cost of the run |
| `code_version` | the git commit and the dirty flag |
| `sources` | the vintages that were read |
| `outputs` | the artefact paths, per country |
| `config`, `environment` | the configuration and the environment of the run |
| `warnings` | the warnings of every country in the run |

## 5. The API

The server is a read-only view over the artefacts. Start it with

```bash
uvicorn jindun_api.app:app --reload --port 8000
```

The interactive documentation is at `/api/docs` and the OpenAPI schema at
`/api/openapi.json`. Every route is under the prefix `/api/v1`.

### System routes

| method | path | query parameters | response |
| --- | --- | --- | --- |
| GET | `/api/v1` | — | `{service, version, docs}` — the service name, its version and the location of the documentation |
| GET | `/api/v1/health` | — | `{status, version, countries[], last_run_id}` — liveness, the countries the store holds and the id of the last run |
| GET | `/api/v1/run-metadata` | — | `{root, countries[], last_run_id, last_started_at, generated_at}` — where the artefacts are read from and which run they belong to |
| GET | `/api/v1/locales` | — | `{default, locales[], fallback}` — the locales the server can render; the list is exactly the catalogues on disk |
| GET | `/api/v1/messages` | `locale` (default `en-US`), `key` (optional) | with `key`: `{locale, key, text, found}` for one rendered message; without it: `{locale, messages}` with the whole catalogue |

### Country routes

| method | path | query parameters | response |
| --- | --- | --- | --- |
| GET | `/api/v1/countries` | — | `{countries[]}` — one summary per country in the store: `code`, `name_en`, `profile`, `capabilities`, `as_of`, `markets[]`, `latest_percentile`, `latest_deviation`, `regime`, `probability_high`, `open_alerts` |
| GET | `/api/v1/countries/{code}/index` | `lens` — `percentile` (default), `deviation` or `composite` | `country_code`, `as_of`, `profile`, `capabilities`, `lens`, the three series, `market_indices` (per market, `{date, value}` points), `market_dates`, the `regime` block and `warnings` |
| GET | `/api/v1/countries/{code}/spillover` | `method` (optional), `horizon` (optional) | `scope`, `nodes[]`, `matrix[]`, `total_spillout`, `total_spillin`, `net`, `horizon`, `method`, `default_method`, `available_methods[]`, `var_order`, `window`, `notes[]` |
| GET | `/api/v1/countries/{code}/alerts` | — | `{alerts[]}` — `alert_id`, `country_code`, `rule_id`, `severity`, `state`, `fired_at`, `message_key`, `message_params`, `attribution`, `detail` |
| GET | `/api/v1/countries/{code}/data-quality` | — | `{generated_at, passed, counts, series[]}` — the quality verdict of the last run |

### Global routes

| method | path | query parameters | response |
| --- | --- | --- | --- |
| GET | `/api/v1/global/spillover` | `method` (optional), `horizon` (optional) | the same shape as the country network, with the country codes as the nodes |
| GET | `/api/v1/global/cycle` | — | the cycle factor: `dates`, `factor`, `loadings`, the explained variance, the cross-check against the country panel, `status`, `source`, `notes` |
| GET | `/api/v1/global/banking-network` | — | the bilateral claims matrix: `nodes` and `edges`, the countries it covers and its source |
| GET | `/api/v1/global/gsib` | — | the G-SIB list: `banks[]` with their buckets, `count`, the bucket histogram, the source URL and the retrieval time |

### Choosing an estimator

The spillover endpoints publish four estimators side by side, and they are not
interchangeable. `?method=` selects one of them; `?horizon=` selects a forecast
horizon when the artefact publishes more than one. A request for an estimator
the artefact does not publish is refused with a **400** that lists the ones it
does — a request is never silently answered with a different estimator than the
one asked for.

### Errors

| status | when |
| --- | --- |
| 404 | the country has no run artefact; the global artefact has not been produced yet; or the country has no spillover network. The last case carries a structured `reason`: `not_applicable` for an economy measured by an official index, `unavailable` when the computation failed in that run |
| 400 | the requested estimator or horizon is not published |

### Configuration

| variable | default | effect |
| --- | --- | --- |
| `JINDUN_RUNS_DIR` | the repository's `data/runs` | where the artefacts are read from |
| `JINDUN_LOCALE_DIR` | the repository's `locales/` | where the shared locale catalogue is read from |
| `JINDUN_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | the browser origins that may call the API |
| `JINDUN_ROOT` | the discovered repository root | the root every other path is resolved from |

The API accepts `GET` and `OPTIONS` only, and it never writes.

## 6. The agent

The analyst agent answers questions over the same artefacts:

```bash
jindun-agent ask --question "How stressed is China?" --country CN --locale zh-CN
jindun-agent ask --question "Who lends to whom?" --json
jindun-agent tools
```

Without a model endpoint it answers deterministically and in the requested
locale, and it never touches the network. With `JINDUN_LLM_BASE_URL`,
`JINDUN_LLM_API_KEY` and `JINDUN_LLM_MODEL` set it asks the model instead, with
the published numbers in the prompt and the rule that it may not invent a
number. Either way, every number it prints appears in an artefact.

## 7. Where the data comes from

| directory | content | committed? |
| --- | --- | --- |
| `data/snapshots/` | the raw source payloads, each with its URL, retrieval time and SHA-256 | **no** — the raw series come from redistributors whose redistribution terms this project cannot grant, and `jindun-pipeline fetch` rebuilds the directory |
| `data/cache/` | the bulky reproducible downloads, such as the BIS bulk archive | no |
| `data/runs/` | the published artefacts and the run manifests | yes |
| `data/baseline/` | the vendored regression baselines and their provenance | yes |

The coverage of every external source, and the gaps in it, are in the data
coverage table of the root [README](../../README.md#data-coverage). The short
version: the ECB CISS publishes no Japanese series at all, so the Japanese
index has no official cross-check anchor; the BIS locational statistics serve
the bilateral matrix only through the bulk archive; and the Chinese market
series come from a scraper of public pages rather than from an official API.

## Where to continue

| question | document |
| --- | --- |
| what the numbers mean | [`../methodology/README.md`](../methodology/README.md) |
| what the method cannot do | [`../research/README.md`](../research/README.md) |
| how to add an economy | [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) |
