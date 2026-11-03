# JinDun Sentinel

JinDun Sentinel is an open-source system for monitoring systemic financial risk across
several economies at once. It turns public daily statistical series into a reproducible
stress index for each economy, identifies whether that economy currently sits in a calm
or a stressed regime and with what probability, estimates which sub-market or which
country transmits stress to which, and raises a small number of graded alerts when a
pre-declared threshold is crossed. The problem it solves is that the measurement of
systemic risk is usually split across incompatible pieces: an index without the regime
model that explains it, a regime model without the network that says who is
contaminating whom, and a dashboard that cannot be reproduced because it displays
numbers nobody can trace back to a source. JinDun Sentinel ships the whole chain as
one pipeline, with an explicit quality gate in front of every published number and a
run manifest behind it.

## The daily chain

Every stage below is executed by `jindun-pipeline run`. The quality gate sits *in front*
of the computation, not behind it: a failing gate rejects the series and blocks the
run, so an unusable input can never reach a published index.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 470" width="100%" role="img" aria-labelledby="jd-title jd-desc">
  <title id="jd-title">JinDun Sentinel daily pipeline</title>
  <desc id="jd-desc">External sources are read by the adapters, which feed the quality gates. A failing quality gate rejects the series and blocks the run. Passing series are normalised, reduced by sub-market PCA, combined into the MBSED composite, assigned a stress regime, turned into a spillover network and evaluated for alerts. The resulting artefacts are served by the FastAPI application and rendered by the web front end.</desc>

  <g fill="none" stroke="#57606a" stroke-width="1.6" stroke-linecap="round">
    <path d="M240 67 H262" />
    <path d="M470 67 H492" />
    <path d="M700 67 H722" />
    <path d="M930 67 H952" />
    <path d="M1060 94 V241" />
    <path d="M960 277 H938" />
    <path d="M730 277 H708" />
    <path d="M500 277 H478" />
    <path d="M300 304 V342 H140 V371" />
    <path d="M240 407 H262" />
  </g>
  <g fill="#57606a">
    <polygon points="270,67 261,62 261,72" />
    <polygon points="500,67 491,62 491,72" />
    <polygon points="730,67 721,62 721,72" />
    <polygon points="960,67 951,62 951,72" />
    <polygon points="1060,250 1055,241 1065,241" />
    <polygon points="930,277 939,272 939,282" />
    <polygon points="700,277 709,272 709,282" />
    <polygon points="470,277 479,272 479,282" />
    <polygon points="140,380 135,371 145,371" />
    <polygon points="270,407 261,402 261,412" />
  </g>

  <g fill="none" stroke="#cf222e" stroke-width="1.6" stroke-dasharray="5 4" stroke-linecap="round">
    <path d="M600 94 V141" />
  </g>
  <polygon points="600,150 595,141 605,141" fill="#cf222e" />
  <text x="612" y="128" font-family="sans-serif" font-size="11" fill="#cf222e">gate fails</text>

  <g fill="#f6f8fa" stroke="#57606a" stroke-width="1.4">
    <rect x="40" y="40" width="200" height="54" rx="6" />
    <rect x="270" y="40" width="200" height="54" rx="6" />
    <rect x="500" y="40" width="200" height="54" rx="6" />
    <rect x="730" y="40" width="200" height="54" rx="6" />
    <rect x="960" y="40" width="200" height="54" rx="6" />
    <rect x="960" y="250" width="200" height="54" rx="6" />
    <rect x="730" y="250" width="200" height="54" rx="6" />
    <rect x="500" y="250" width="200" height="54" rx="6" />
    <rect x="270" y="250" width="200" height="54" rx="6" />
    <rect x="40" y="380" width="200" height="54" rx="6" />
    <rect x="270" y="380" width="200" height="54" rx="6" />
  </g>

  <g fill="#fff8c5" stroke="#cf222e" stroke-width="1.4">
    <rect x="460" y="150" width="280" height="54" rx="6" />
  </g>

  <g font-family="sans-serif" font-size="10" font-weight="bold" fill="#57606a">
    <text x="53" y="58">1</text>
    <text x="283" y="58">2</text>
    <text x="513" y="58">3</text>
    <text x="743" y="58">4</text>
    <text x="973" y="58">5</text>
    <text x="973" y="268">6</text>
    <text x="743" y="268">7</text>
    <text x="513" y="268">8</text>
    <text x="283" y="268">9</text>
    <text x="53" y="398">10</text>
    <text x="283" y="398">11</text>
    <text x="473" y="168" fill="#cf222e">&#215;</text>
  </g>

  <g font-family="sans-serif" font-size="13" font-weight="bold" fill="#1f2328" text-anchor="middle">
    <text x="140" y="64">External sources</text>
    <text x="370" y="64">Adapters</text>
    <text x="600" y="64">Quality gates</text>
    <text x="830" y="64">Normalisation</text>
    <text x="1060" y="64">Sub-market PCA</text>
    <text x="1060" y="274">MBSED composite</text>
    <text x="830" y="274">Regime identification</text>
    <text x="600" y="274">Spillover network</text>
    <text x="370" y="274">Alerts</text>
    <text x="140" y="404">FastAPI</text>
    <text x="370" y="404">Web UI</text>
    <text x="600" y="174" fill="#cf222e">Rejected</text>
  </g>

  <g font-family="sans-serif" font-size="10.5" fill="#57606a" text-anchor="middle">
    <text x="140" y="82">ECB, BIS, BOJ, FSB, akshare</text>
    <text x="370" y="82">read-only, snapshot-cached</text>
    <text x="600" y="82">staleness, gaps, bounds</text>
    <text x="830" y="82">cdf_rank by direction</text>
    <text x="1060" y="82">eigh, 80% variance</text>
    <text x="1060" y="292">weighted correlation form</text>
    <text x="830" y="292">MS-AR, filtered posterior</text>
    <text x="600" y="292">paper / Sims / DY / legacy</text>
    <text x="370" y="292">P1 / P2 / P3 rules</text>
    <text x="140" y="422">/api/v1, docs at /api/docs</text>
    <text x="370" y="422">Vue 3, four locales</text>
    <text x="600" y="192" fill="#cf222e">series excluded, run exits 1</text>
  </g>
</svg>

## What this is not

Academic implementations of composite systemic-risk indices are usually research
artefacts: the input series come from a commercial terminal, the code runs on one
author's machine against one workbook, and the published tables cannot be regenerated.
Commercial risk platforms do the opposite: they are reproducible and always on, but
they are closed, paid, and they publish an index without the model that explains it.
Dashboard projects usually start from an already-computed index and can display it in
many languages but cannot reproduce it.

JinDun Sentinel is built to close that gap, and the claim is deliberately narrow: there
is no free, verified, daily-frequency, multi-country system that also ships the
spillover network, the regime probability model and the early-warning loop as one
runnable pipeline.

| | academic replication | commercial terminal pipeline | dashboard project | JinDun Sentinel |
| --- | --- | --- | --- | --- |
| Inputs free and publicly verifiable | no | no | n/a | yes, per-source coverage documented below |
| Daily frequency, multi-country | no | yes | no | yes |
| Contagion / spillover network | usually | sometimes | rarely | yes, four estimators |
| Regime probability model | sometimes | yes | rarely | yes, filtered, estimated |
| Early-warning loop with graded alerts | no | yes | no | yes, declarative rules |
| Quality gate that can block a run | no | no | no | yes, per series |
| Run manifest (code version, vintage, hashes) | no | no | no | yes |
| Same locale catalogue on server and front end | n/a | n/a | usually | yes, four locales |

## The four layers

| layer | what it computes | method | artefact / endpoint |
| --- | --- | --- | --- |
| Country index | one stress index per sub-market (equity, bond, fx, money, derivative) and the MBSED composite, reported on two lenses | `cdf_rank` normalisation by direction, sub-market PCA (`numpy.linalg.eigh`, smallest component count reaching 80 % cumulative explained variance), CRITIC or configured weights, composite `sqrt((W ⊙ s) P (W ⊙ s)' × 2)`, percentile and deviation-from-trend lenses | `data/runs/<CC>/market_indices.csv`, `run.json`; `GET /api/v1/countries/{code}/index` |
| Regime | the stress regime (moderate / high) per observation and the probability of each | Markov-switching autoregression on the log composite (2 states, order 5, switching variance, trend `c`) using **filtered** posterior probabilities, with a deterministic two-cluster fallback; two-component normal mixture whose locations and dispersions are estimated from the fit | `run.json` → `regime` block; `GET /api/v1/countries/{code}/index` |
| Contagion | the directed cross-market spillover network: own risk share, total spill-out, total spill-in, net transmitter | VAR with BIC order selection (max order 5) and one of four generalisations of the forecast error variance decomposition; row-normalised shares | `run.json` → `spillover` block; `GET /api/v1/countries/{code}/spillover` |
| Global | cross-country contagion, the global financial cycle factor, the cross-border banking network and the G-SIB list | the same generalised variance decomposition applied to the country composites (common calendar only), the first principal component of a standardised block of BIS global liquidity, credit-gap and exchange-rate series (with the country-panel principal component published as its cross-check), BIS locational banking statistics, the FSB G-SIB document | `data/runs/global/*.json`; `GET /api/v1/global/spillover`, `/global/cycle`, `/global/banking-network`, `/global/gsib` |

The four spillover estimators are not interchangeable and each carries its own caveat:

| method | what it is | order-dependent | signed | default |
| --- | --- | --- | --- | --- |
| `paper_equation` | equations (6) and (7) of the source specification | no | no | **yes** |
| `sims_structural` | Sims (1980) FEVD, Cholesky orthogonalisation | yes | no | no |
| `dy_generalised` | Diebold-Yilmaz (2009, 2012) generalised FEVD | no | yes | no |
| `legacy_appendix` | literal transcription of the previously shipped code; a residual-correlation weighted index, **not** a variance decomposition | no | no | no |

See `docs/methodology/spillover-legacy-vs-paper.md` for the full comparison.

**All four are published in every artefact**, side by side under
`spillover.estimators`; the default one is also inlined at `spillover` itself
for the consumers that do not need the choice.  An estimator that cannot be
computed for a given network is listed in `spillover.failed_estimators` with
its reason — it never removes the others.  The API takes the choice
explicitly (`?method=…`) and refuses a method the artefact does not publish
with a `400` that lists the ones it does, so a request can never be answered
with a different estimator than the one asked for.

## Economies and languages

Five economies are in scope.  They are **not** measured with the same instrument, and
`docs/methodology/country-profiles.md` states exactly what each one has and what it does
not have.

| economy | code | country index | cross-check anchor | configuration shipped | run published in this tree |
| --- | --- | --- | --- | --- | --- |
| China | `CN` | MBSED composite over five markets | ECB CISS daily composite `SS_CIN` (area `CN`) | yes — `packages/pipeline/configs/countries/cn.yaml` | yes |
| Japan | `JP` | MBSED composite over two markets (BOJ call rates, USD/JPY) | **none** — the ECB CISS publishes no Japanese series at all | yes — `configs/countries/jp.yaml` | yes |
| United States | `US` | official ECB composite stress index | the index itself (`SS_CIN`, area `US`) | yes — `configs/countries/us.yaml` | yes |
| United Kingdom | `GB` | official ECB composite stress index | the index itself (`SS_CIN`, area `GB`) | yes — `configs/countries/gb.yaml` | yes |
| Euro area | `EU` | official ECB composite stress index | the index itself (`SS_CIN`, area `U2`) | yes — `configs/countries/eu.yaml` | yes |

An economy whose index is an official published index has **no** sub-market
decomposition, so no market attribution and no cross-market spillover network: the run
artefact says so explicitly rather than publishing a decomposition that was never
computed.  This is stated as **data**, not as an error: every artefact carries a
`profile` and a `capabilities` map, and the API and the front end read them, so
the absence is rendered as a property of the economy instead of as a failure.
The cross-country network and the global cycle factor work on the country
composites and are therefore available for all five.

The four shipped locales are English (`en-US`), Simplified Chinese (`zh-CN`),
Traditional Chinese (`zh-TW`) and Japanese (`ja-JP`). Simplified and Traditional
Chinese are written by hand rather than converted, because the financial vocabulary
genuinely differs between them. The catalogue files under `locales/` are the single
source of truth: the Python server reads them through `jindun.i18n`, the front end
reads the very same files at build time through a Vite plugin.

## Data coverage

Every coverage statement in this table is the one the corresponding adapter records in
its own docstring, where the verification against the live service was carried out. The
"known gaps" column is the part that matters most: an implementation that hides its
gaps cannot be monitored.

| source | endpoint / format | coverage | known gaps and limits |
| --- | --- | --- | --- |
| ECB CISS — daily composite `SS_CIN` | `https://data-api.ecb.europa.eu/service/data/CISS/D.<area>.Z0Z.4F.EC.SS_CIN.IDX?format=csvdata&detail=dataonly` (SDMX 2.1; the key is **one** path segment with dots between the dimensions) | 14 reference areas: `AT BE CN DE ES FI FR GB IE IT NL PT U2 US` | no other reference area exists on the daily frequency, including Japan |
| ECB CISS — monthly composite `SS_CI` | same base path with `M.<area>.…` and `SS_CI` | 2 reference areas: `U2`, `US` | the monthly composite is **not** published for any individual member state |
| ECB CISS — sub-stress components | `…/D.<area>.….<COMPONENT>_CON/CON` | 5 components (`CREDIT`, `EQUITY`, `INTERBANK`, `REAL_ESTATE`, `SOVEREIGN`) for the euro area `U2` only | components exist only as `.CON` contribution series; the `.IDX` variant of a component does not exist and answers 404. Components are not available for `CN`, `GB` or `US` |
| ECB CISS — Japan | any Japanese reference area | **nothing** | every Japanese reference area returns 404 on both the daily and the monthly frequency. Japan therefore has **no CISS cross-check anchor**; the Bank of Japan API is used instead and the methodology states this explicitly |
| BIS statistical API — data | `https://stats.bis.org/api/v1/data/{flow}/{key}?startPeriod=…&endPeriod=…&format=csvfile` | 10 of the 56 published flows are used: `WS_LBS_D_PUB`, `WS_LBS_PUB`, `WS_CBS_PUB`, `WS_GLI`, `WS_CREDIT_GAP`, `WS_DSR`, `WS_EER`, `WS_XRU`, `WS_OTC_DERIV2`, `WS_CPP` | **the key must be part of the URL path.** A request of the form `/api/v1/data/WS_LBS_D_PUB?key=…` silently ignores the key and returns the entire flow — 25 MB for a single quarter of the locational banking statistics, against 358 bytes for the same query in path form |
| BIS statistical API — structure | `https://stats.bis.org/api/v1/dataflow/BIS` (SDMX-ML) | the full flow catalogue | requesting the JSON representation (`Accept: application/vnd.sdmx.structure+json`) answers **406**; the endpoint serves SDMX-ML XML, which is what the adapter parses |
| BIS bulk archive — locational banking statistics | `https://data.bis.org/static/bulk/WS_LBS_D_PUB_csv_flat.zip` (365 MB, ~18 GB uncompressed) | the bilateral reporting-economy × counterparty-country matrix | **the bilateral matrix is only served by the bulk file.** Through the API the reporting-country dimension accepts the aggregate `5A` only, so a request for `L_REP_CTY=US` answers 404 although the data is published. The archive is downloaded once into `data/cache/` (never committed) and streamed into a filtered snapshot of about two megabytes under `data/snapshots/bis/` (fetched, never committed) |
| BIS bulk archive — global liquidity, credit gap and exchange rates | `https://data.bis.org/static/bulk/{WS_GLI,WS_CREDIT_GAP,WS_EER}_csv_flat.zip` (0.2 MB, 0.2 MB and 6.3 MB) | the inputs of the global financial cycle factor | the SDMX API serves the aggregates of these flows but not the dimension combinations the factor needs, so a narrow key answers 404 and the bulk file is the only practical route. `WS_EER` carries a **daily block and a monthly block at the same time**, and the two overlap in calendar time: only the daily block may be read, or a monthly average and a daily observation end up in the same quarter. The last quarter of every flow is half published and is excluded |
| BIS SDMX v2 | `/api/v2/…` | none | the v2 paths answer **404** or **501**; only the v1 API exists |
| Bank of Japan — Time-Series Statistics Search | `https://www.stat-search.boj.or.jp/api/v1/getMetadata`, `/getDataCode`, `/getDataLayer` | 10 databases used by this project: `IR01`, `FM01`, `FM02`, `FM08`, `FM09`, `MD01`, `MD02`, `PR01`, `CO`, `BP01` (the adapter also knows `BIS`, the Japanese slice of the BIS international banking and credit statistics), plus four derived series (the call-rate term spread, the call-rate dispersion, the USD/JPY volatility and the USD/JPY deviation from trend) | `getDataCode` accepts at most 250 series codes per request, `getDataLayer` at most 1 250; pagination is driven by `NEXTPOSITION`, which must be echoed back as `startPosition`; the service asks clients not to hammer it, so the adapter enforces a minimum delay between requests. The BOJ publishes no daily equity index, no daily derivatives market and no daily government bond yield curve, so the Japanese index has two markets rather than five. The Japanese index uses the call-rate **dispersion**, not the term spread: the term call rates of `FM02` only start in 2025, which would have cut the Japanese index down to two years of history |
| FSB — G-SIB list | announcement page → linked PDF | the annual list, parsed into bank names with buckets 1–10 | the bank names are **not** in the announcement page: they live in a PDF linked from the list page, so the adapter resolves the link and parses the document's text layer. The bucket surcharge is the Basel schedule (0.5 % per bucket, 1.0 %–5.0 %) |
| akshare — Chinese market data | `akshare` Python package | 26 registered series (14 direct reads of an upstream table + 12 deterministic derivations): SSE/SZSE/CSI 300 levels and turnover, ChinaBond government yields and curve slopes, SHIBOR fixings, margin balances, CSI 300 index futures, USD/CNY middle rate | `akshare` is an **optional** dependency (`--extra market`). Without it every Chinese indicator is reported as unavailable with a warning — never as a silent zero. Only series whose output shape was verified against the live service are registered |

Chinese indicators whose original source is a commercial terminal or a research
construction are kept in `cn.yaml` with `enabled: false` rather than being replaced by
a proxy, so the gap stays visible: `pe_ratio`, `credit_risk_premium`,
`bond_index_volatility`, `exchange_rate_distortion`.

## Install

The Python side is a [uv](https://docs.astral.sh/uv/) workspace: the root
`pyproject.toml` declares `packages/*` as members and depends on `jindun-pipeline`
and `jindun-api` from the workspace.

```bash
uv sync --extra dev --extra market --all-packages
```

The workspace members are the three Python packages (`packages/pipeline`, `packages/api`,
`packages/agent`); the front end is a separate npm package and is excluded.

Extras available on `jindun-pipeline`: `arch` (GARCH volatility), `market` (akshare),
`ml` (torch), `dev` (pytest, pytest-cov, ruff, mypy). `jindun-api` has a `dev` extra
with pytest, httpx, ruff and mypy.

The front end is a separate npm package and is not part of the uv workspace:

```bash
cd packages/web
npm install
npm run dev      # http://localhost:5173
```

## Quickstart

### 1. List what the adapters can deliver

```bash
jindun-pipeline sources
```

Prints, as JSON: the configured countries with their market and indicator counts,
every registered akshare series, the ECB CISS reference areas, the BIS flows and the
BOJ databases.

### 2. Download the configured sources

```bash
jindun-pipeline fetch                     # every enabled country
jindun-pipeline fetch --country CN        # one country (repeatable)
jindun-pipeline fetch --refresh           # ignore the snapshot cache
```

Each response is written to the snapshot store together with its URL, retrieval
timestamp and SHA-256, so a later run can be replayed from the same bytes. The
command exits 1 if any series came back empty.

### 3. Run the pipeline

```bash
jindun-pipeline run
jindun-pipeline run --country CN --out data/runs
jindun-pipeline run --refresh
```

Writes, per country, into `<out>/<CODE>/`:

| file | content |
| --- | --- |
| `market_indices.csv` | the sub-market stress indices, one column per market |
| `run.json` | composite, percentile and deviation series, the regime block, the spillover network (with the rolling spill-out history behind the surge alert), the alerts, the attribution of the last move, the forecast with its walk-forward score, the source list and the warnings |
| `quality.json` | the quality-gate verdict per series, with the measured value and the threshold of every check |

and one manifest per run, `<out>/manifest-<run_id>.json`, pinning the run id, the
start time, the git commit and dirty flag, the artefact paths, the elapsed time and
the warnings. The command exits 1 if any country's quality report contains a failure.

A full run of the five economies takes about three minutes.  The two parts that would
otherwise dominate it are bounded on purpose: the walk-forward evaluation refits the
model at a bounded number of origins, and the regime model and the forecast use the
most recent 2 500 observations.

### 4. Build the global layer

```bash
jindun-pipeline global
```

Writes `data/runs/global/spillover.json` (the cross-country network),
`cycle.json` (the global financial cycle factor), `banking_network.json` (the BIS
cross-border banking network) and `gsib.json` (the FSB G-SIB list).  The cycle
factor is estimated from the BIS global liquidity, credit-gap and exchange-rate
series; its method and its limits are in `docs/global/global-cycle-factor.md`.
The banking network is read from the BIS snapshot; to create that snapshot see
`docs/global/banking-network.md`.

### 5. Re-check the gates without recomputing

```bash
jindun-pipeline verify
jindun-pipeline verify --country CN
```

Re-evaluates the quality gates against the stored snapshots and prints the report as
JSON. Exits 1 when the report contains a failure.

### 6. Serve the API

The application is two processes — this server and the front end — and they
are easiest to start together:

```bash
python scripts/serve_dev.py
```

The launcher starts both, streams their output with a prefix, and stops them
together when it is interrupted.  The API is then at `http://localhost:8000`
and the front end at `http://localhost:5173/`.

To run the API on its own:

```bash
uvicorn jindun_api.app:app --reload --port 8000
```

The OpenAPI documentation is at `/api/docs` and the schema at `/api/openapi.json`.

| endpoint | returns |
| --- | --- |
| `GET /api/v1` | service name, version, docs location |
| `GET /api/v1/health` | liveness, the countries the store holds, the last run id |
| `GET /api/v1/run-metadata` | artefact root, countries, last run id and start time |
| `GET /api/v1/locales` | the locales the server can render, and the fallback |
| `GET /api/v1/messages?locale=&key=` | one rendered message, or the whole catalogue |
| `GET /api/v1/countries` | one summary per country in the store |
| `GET /api/v1/countries/{code}/index?lens=percentile\|deviation\|composite` | composite, both lenses, the market indices and the regime block |
| `GET /api/v1/countries/{code}/spillover` | the cross-market network: nodes, matrix, spill-out, spill-in, net |
| `GET /api/v1/countries/{code}/alerts` | the alerts the last run raised |
| `GET /api/v1/countries/{code}/data-quality` | the quality verdicts of the last run |
| `GET /api/v1/global/spillover` | the cross-country network |
| `GET /api/v1/global/cycle` | the global financial cycle factor with its loadings and its cross-check |
| `GET /api/v1/global/banking-network` | the cross-border banking network |
| `GET /api/v1/global/gsib` | the G-SIB list with buckets |

The API is a read-only view over the artefacts the pipeline wrote: it never
recomputes an index, so the number on the screen is the number in the manifest.

Three environment variables configure the server:

| variable | default | effect |
| --- | --- | --- |
| `JINDUN_RUNS_DIR` | the repository's `data/runs` | where the artefacts are read from |
| `JINDUN_LOCALE_DIR` | the repository's `locales/` | where the shared locale catalogue is read from |
| `JINDUN_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | the allowed browser origins |

The API exposes the locale catalogue through `jindun.i18n`, which reads the shared
`locales/` directory.  The directory is **discovered**, not guessed: the repository root
is the nearest ancestor that carries both a `pyproject.toml` and a populated `locales`
directory, so the server and the front end always read the same files.  The environment
variable is only needed when the catalogue lives somewhere else.

### 7. Run the front end against the API

```bash
cd packages/web
npm run dev
```

The front end talks to `http://localhost:8000` by default; set `VITE_API_BASE`
to point it somewhere else.

### 7b. Or run both in containers

```bash
docker compose -f deploy/docker-compose.yml up --build
```

The same two services, as images: the API on <http://localhost:8000> and the
front end on <http://localhost:5173/>.  The repository's `data/` directory is
mounted into the API container, so a pipeline run on the host is served without
a rebuild.  `deploy/README.md` has the details.

### 8. Ask the system a question

```bash
jindun-agent ask --question "How stressed is China?" --country CN --locale zh-CN
jindun-agent ask --question "Who lends to whom?" --json
jindun-agent tools
```

The agent reads the same run artefacts as the API.  Without an LLM endpoint it
answers deterministically and in the requested locale; with `JINDUN_LLM_BASE_URL`,
`JINDUN_LLM_API_KEY` and `JINDUN_LLM_MODEL` set it asks the model, with the
published numbers in the prompt and the rule that it may not invent a number.
The offline path never touches the network, and every number it prints is a
number that appears in an artefact.

## Repository layout

```
jindun-sentinel/
├── pyproject.toml            uv workspace root (members: the three Python packages)
├── uv.lock                   resolved dependency lock
├── README.md                 this file
├── LICENSE                   Apache License 2.0
├── CHANGELOG.md              Keep a Changelog format
├── CONTRIBUTING.md           setup, standards, how to add a country
├── CODE_OF_CONDUCT.md        Contributor Covenant v2.1
├── SECURITY.md               vulnerability reporting
├── locales/                  shared message catalogues: en-US, zh-CN, zh-TW, ja-JP
├── deploy/                   the container setup: Dockerfiles, compose file, nginx
├── data/
│   ├── runs/                 published artefacts and run manifests
│   ├── snapshots/            raw source snapshots (fetched, not committed)
│   ├── baseline/             vendored regression baselines and their provenance
│   └── cache/                bulky reproducible downloads (not committed)
├── docs/
│   ├── methodology/          the spillover estimators, the country profiles
│   ├── global/               the global layer, the cycle factor and the banking network
│   └── user-guide/           the quick start
├── packages/
│   ├── pipeline/             jindun-pipeline — the computation core
│   │   ├── configs/          global.yaml and countries/*.yaml
│   │   ├── src/jindun/       indicators, index, regime, contagion, adapters, global_layer
│   │   └── tests/            pytest suite
│   ├── api/                  jindun-api — the FastAPI server
│   │   └── src/jindun_api/   app, store, schemas, routers
│   ├── agent/                jindun-agent — the question answering layer
│   │   └── src/jindun_agent/ context, tools, prompts, agent, cli
│   └── web/                  @jindun/web — the Vue 3 front end
│       └── src/              api client, stores, composables, components, i18n
└── scripts/                  the baseline freeze, the BIS download and extraction,
                             the locale tools and the local dev launcher
```

The Python package is layered so that each stage can be tested and reused in
isolation: `indicators` (transforms), `index` (normalisation, PCA, CRITIC, composite),
`regime` (HP filter, Markov switch, probability model), `contagion` (VAR, generalised
variance decomposition, surge test), `adapters` (read-only source clients),
`global_layer` (cross-country layer, global cycle, banking network).

The package that carries the global layer is called `global_layer` and not
`global`: `global` is a Python keyword, and `from .global import …` does not
parse.

## Known gaps in this tree

Stated plainly, because a monitoring system that hides its gaps is not monitorable.

| area | status |
| --- | --- |
| country configurations | all five economies are shipped and their runs are published in this tree |
| Japanese index | the Bank of Japan publishes no daily equity index, no daily derivatives market and no daily government bond yield curve, so the Japanese index has **two** markets instead of five and the Japanese cross-market spillover network has two nodes. The monthly and quarterly BOJ price databases are not mixed into the daily panel |
| sub-market decomposition of the United States, the United Kingdom and the euro area | these economies are measured with the official ECB composite stress index, so they have **no** sub-market decomposition, no market attribution and no cross-market spillover network. Every run artefact says so |
| global layer artefacts | `jindun-pipeline global` writes the four artefacts into `data/runs/global/`; the `/api/v1/global/*` endpoints answer 404 until that command has been run |
| the BIS archive | the bilateral matrix is only served by the bulk archive, which is downloaded once into `data/cache/` (365 MB, not committed) and streamed into a filtered snapshot of about two megabytes under `data/snapshots/bis/` (not committed) |
| the published table 5-2 of the source specification | it **cannot** be reproduced to the digit: the original input workbook was never published, and an exhaustive search over 4 696 candidate specifications did not find a single one that reproduces it. `docs/methodology/spillover-legacy-vs-paper.md` states the evidence and the regression strategy that replaced it |
| static analysis | `ruff check` is clean for all three Python packages. `mypy` still reports 22 findings in the pipeline — mostly annotation precision in the adapter layer, no known runtime defect among them |
| continuous integration | `.github/workflows/ci.yml` runs the linter, the test suite, the locale-catalogue audit and the front-end build and test on every push and pull request |

## Licence

Apache License 2.0 — see [LICENSE](LICENSE).

## Contributing

Setup, coding standards, commit conventions and the procedure for adding a country are
described in [CONTRIBUTING.md](CONTRIBUTING.md). Every pull request is expected to
keep `pytest` green, to add no new `ruff` or `mypy` findings, and to leave the locale
catalogues in sync with the front end.

## Reporting a problem

- Bugs and feature requests: open an issue in the repository.
- Security vulnerabilities: **do not** open a public issue. Follow the private
  reporting process in [SECURITY.md](SECURITY.md).
- Contributions: read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first; it is binding
  for participation in the project.

## Acknowledgements

The methodology follows the published specification of the source research, including
equations (6) and (7) of the variance decomposition and the MBSED composite
construction. The comparison between the published specification and the previously
shipped implementation is recorded in `docs/methodology/spillover-legacy-vs-paper.md`.
