# Quick start

## What this is

JinDun Sentinel is a multi-country systemic financial risk monitoring and early
warning system.  It downloads the stress indicators of five economies, builds
a stress index for each of them, identifies the stress regime, estimates the
contagion inside each economy and between them, forecasts the index, and
publishes everything through a read-only API and a web front end.

The numbers the front end shows are the numbers the pipeline wrote: the API
reads the run artefacts and never recomputes an index.

## Install

```powershell
git clone https://github.com/ZajacMo/jindun-sentinel.git
cd jindun-sentinel
uv sync --all-packages
```

`uv` is the only build tool the project uses.  A plain `pip install -e
packages/pipeline` works as well, but the workspace lock file is the
reproducible path.

The Chinese market data comes from `akshare`, which is an optional extra:

```powershell
uv sync --all-packages --extra market
```

Without it the Chinese tertiary indicators are reported as unavailable rather
than failing the run.

## Run the pipeline

```powershell
python -m jindun.cli sources                  # what is configured and available
python -m jindun.cli fetch --country CN       # download the sources
python -m jindun.cli run                      # run every enabled economy
python -m jindun.cli global                   # build the global layer
python -m jindun.cli verify --country CN      # re-check the quality gates
```

A run writes `data/runs/<COUNTRY>/run.json`, `market_indices.csv` and
`quality.json`, plus a manifest that pins the code version, the configuration
and the hashes of the artefacts.  The global layer writes
`data/runs/global/*.json`.

A full run of the five economies takes about three minutes on a laptop.

## Serve the API

```powershell
uvicorn jindun_api.app:app --port 8000
```

The endpoints:

| Endpoint | Content |
| --- | --- |
| `GET /api/v1/health` | service status |
| `GET /api/v1/countries` | the economies with a published run |
| `GET /api/v1/countries/{code}/index` | the composite and its two lenses |
| `GET /api/v1/countries/{code}/spillover` | the cross-market network |
| `GET /api/v1/countries/{code}/alerts` | the alerts that fired |
| `GET /api/v1/countries/{code}/data-quality` | the quality gate results |
| `GET /api/v1/global/spillover` | the cross-country network |
| `GET /api/v1/global/cycle` | the global cycle factor |
| `GET /api/v1/global/banking-network` | the BIS cross-border banking network |
| `GET /api/v1/global/gsib` | the FSB G-SIB list |
| `GET /api/v1/locales` | the available locales |

Every response is language neutral: numbers are numbers, dates are ISO-8601
strings and enumerations are stable codes.  The client renders the codes with
the shared locale catalogue.

## Serve the front end

```powershell
cd packages/web
npm install
npm run dev        # http://localhost:5173
npm run build
npm test
```

The front end reads the API at `VITE_API_BASE` (default
`http://localhost:8000`).

## Ask a question instead of reading a chart

```powershell
python -m jindun_agent.cli ask --question "How stressed is China?" --country CN --locale zh-CN
python -m jindun_agent.cli ask --question "Who lends to whom?" --json
python -m jindun_agent.cli tools
```

The agent answers from the same run artefacts.  Without an LLM endpoint
configured it produces a deterministic, fully localised structured answer;
with `JINDUN_LLM_BASE_URL`, `JINDUN_LLM_API_KEY` and `JINDUN_LLM_MODEL` set it
asks the model, with the same numbers in the prompt and the same rule that the
model may not invent a number.

## The cross-border banking network

The network is built from the BIS bulk archive, which is downloaded once and
cached outside the repository:

```powershell
python scripts/download_bis_bulk.py
python scripts/extract_bis_network.py
python -m jindun.cli global
```

The archive is 365 MB and expands to about 18 GB of text; the script streams
it and writes a filtered snapshot of about two megabytes.

## What to read next

* `docs/methodology/country-profiles.md` — what each economy is measured with,
  and what it is not measured with.
* `docs/methodology/spillover-legacy-vs-paper.md` — the four spillover
  estimators, and why the published table cannot be reproduced to the digit.
* `docs/global/global-layer.md` — the cross-country network, the cycle factor
  and the banking network.
* `docs/global/banking-network.md` — how the BIS data is read and what its
  limitations are.
