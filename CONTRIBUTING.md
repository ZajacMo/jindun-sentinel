# Contributing to JinDun Sentinel

Thanks for taking the time to contribute. This document covers how to set the project
up, the standards the code is held to, how commits and pull requests are written, and
how a new country is added.

## Contents

- [Setting up](#setting-up)
- [Coding standards](#coding-standards)
- [Tests](#tests)
- [Commit conventions](#commit-conventions)
- [Pull requests](#pull-requests)
- [Adding a country](#adding-a-country)
- [Working with the locale catalogues](#working-with-the-locale-catalogues)
- [Reporting bugs and proposing features](#reporting-bugs-and-proposing-features)

## Setting up

JinDun Sentinel is a [uv](https://docs.astral.sh/uv/) workspace with three Python
packages and one npm package.

```bash
git clone <repository-url>
cd jindun-sentinel
uv sync --extra dev --extra market --all-packages
```

The root `pyproject.toml` declares `packages/pipeline`, `packages/api` and
`packages/agent` as workspace members and depends on `jindun-pipeline` and
`jindun-api` from the workspace, so a single `uv sync` installs everything.

The front end is not part of the uv workspace:

```bash
cd packages/web
npm install
npm run dev
```

Extras on `jindun-pipeline`:

| extra | contents | needed for |
| --- | --- | --- |
| `arch` | `arch>=7.0` | GARCH conditional volatility in `jindun.indicators.transforms` |
| `market` | `akshare>=1.16` | the Chinese market data sources |
| `ml` | `torch>=2.4` | the neural forecast path |
| `dev` | `pytest`, `pytest-cov`, `ruff`, `mypy` | development |

`jindun-api` has a `dev` extra with `pytest`, `httpx`, `ruff` and `mypy`.

The locale catalogue is discovered, not guessed: `jindun.paths` finds the
repository root by looking for the workspace manifest and a populated `locales`
directory, so the server and the front end read the same four files without any
configuration. The environment variable is only needed when the catalogue lives
somewhere else:

```bash
export JINDUN_LOCALE_DIR="$PWD/locales"
```

## Coding standards

### Language

**All comments, docstrings, commit messages and pull-request descriptions are written
in English.** The project's source of truth for *user-facing* strings is the locale
catalogue, not the source code; but the source code itself is written in English
throughout, including the docstrings that document the methodology. A comment that
explains why the variance decomposition normalises row-wise is a comment for
everybody who reads the repository, not only for its author.

### Python

The tooling is configured in the `pyproject.toml` of each package:

| tool | configuration | command |
| --- | --- | --- |
| `ruff` | `line-length = 100`, `target-version = "py311"`, rules `E`, `F`, `I`, `UP`, `B`, `SIM`, `E501` ignored | `ruff check .` |
| `ruff` (format) | same line length | `ruff format --check .` |
| `mypy` | `python_version = "3.11"`, `disallow_untyped_defs = true`, `warn_unused_ignores = true`, `ignore_missing_imports = true` | `mypy packages/pipeline/src packages/api/src` |
| `pytest` | `testpaths = ["tests"]`, `addopts = "-q"` | `pytest packages/pipeline/tests` |

#### The current state of the checks

The tree does **not** pass every one of these checks yet. Measured on 2026-11-03:

| check | result |
| --- | --- |
| `pytest packages/pipeline/tests` | 51 tests, all pass |
| `ruff check packages/pipeline` | 61 findings (46 auto-fixable) |
| `ruff check packages/api` | 14 findings (2 auto-fixable) |
| `ruff format --check packages/pipeline packages/api` | 23 of 53 files would be reformatted |
| `mypy packages/pipeline/src packages/api/src` | 43 errors in 24 of 46 files |
| `npm run build` in `packages/web` | not green — the front end is under active development |

A contribution is expected not to **add** findings, and reducing the existing ones is
welcome: `ruff check --fix` settles 48 of the 75 lint findings mechanically and
`ruff format` settles the formatting. The `mypy` findings are mostly missing library
stubs (`pandas`, `scipy`) and a handful of real narrowing problems; `disallow_untyped_defs`
is on, so the count is expected to fall as the annotations are completed.

The front end is under active development and its build is not green at the time of
writing. `src/router/index.ts` defines seven pages, and the page, chart and diagram
components under `packages/web/src/` are still being added to match it; `vue-tsc`
reports type errors in the in-progress components. `npm run typecheck` and
`npm run build` are the acceptance gates. The root `README.md` lists this under
"Known gaps in this tree".

Conventions that the configuration encodes:

- Every public function and class carries a docstring that says what it computes and,
  where it matters, what it does **not** do. The methodology modules in this project
  document the caveats of their estimators in the docstring itself, because those
  caveats decide how the published numbers may be read.
- Type annotations on every function signature. `mypy` runs with
  `disallow_untyped_defs = true`, so an unannotated `def` is an error, not a warning.
- `from __future__ import annotations` at the top of every module, and `X | None`
  instead of `Optional[X]`.
- Imports are sorted by `ruff`'s isort rules (`I`); run `ruff check --fix` rather
  than sorting them by hand.
- Line length is 100 characters. `E501` is ignored because the formatter owns the
  wrapping, but a line that has to be manually wrapped is usually a line that wants to
  be a function.
- No hard-coded methodology parameters in code. Market weights, PCA thresholds, regime
  parameters, the contagion horizon and the alert rules live in YAML under
  `packages/pipeline/configs/`. If a researcher would want to vary it, it belongs in
  the configuration.
- Adapters never raise on a missing series. They return a `FetchResult` with warnings
  and no observations, so one broken source cannot stop a daily run — and the quality
  gate turns the gap into a visible warning rather than a silent zero.

### TypeScript and Vue

The front end is Vue 3 with the Composition API and TypeScript.

```bash
cd packages/web
npm run typecheck   # vue-tsc --noEmit
npm run build       # typecheck + vite build
npm run test        # vitest
```

- Components use `<script setup lang="ts">`.
- No translatable string is written inline in a template. Every visible string comes
  from the shared catalogue through a `t('...')` call, so the server and the front end
  can never disagree about a label.
- API calls go through the typed client in `src/api/`, never through a bare `fetch`.

## Tests

```bash
pytest packages/pipeline/tests
```

- A new module ships with a test module next to it in
  `packages/pipeline/tests/`.
- Tests pin **behaviour and invariants**, not published numbers. The spillover suite,
  for example, pins the estimator against an independently written transcription and
  pins the reporting invariants (rows sum to one, non-negativity for the non-signed
  methods); it does not assert a matrix from a published table, because that table
  depends on a data vintage that is not recoverable.
- A change that moves a published number must state the old value, the new value and
  the difference in the pull request. Numbers are never silently aligned.

## Commit conventions

Commits follow the Conventional Commits format:

```
<type>(<scope>): <short summary>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
Scopes follow the package or module: `pipeline`, `api`, `web`, `adapters`, `contagion`,
`regime`, `index`, `i18n`, `config`, `docs`.

```
feat(contagion): add the Diebold-Yilmaz generalised decomposition
fix(adapters): keep the BIS key in the request path
docs(pipeline): record the comparability note on the percentile lens
```

- The subject line is imperative, lower case, and does not end with a period.
- The body explains *why* the change was made and what it changes in the published
  numbers, if it changes any. A body is required whenever the change affects a
  methodology parameter, an artefact schema or an API response.
- The footer references an issue (`Closes #42`) and names the co-authors
  (`Co-authored-by: Name <address>`).
- One logical change per commit. A refactor and a behaviour change are two commits.

## Pull requests

1. Branch from the default branch: `feature/<short-topic>`, `fix/<short-topic>` or
   `docs/<short-topic>`.
2. Run the checks before pushing:

   ```bash
   ruff check .
   ruff format --check .
   mypy packages/pipeline/src packages/api/src
   pytest packages/pipeline/tests
   ```

   The test suite passes today; `ruff` and `mypy` still report the findings listed
   under "The current state of the checks" above. A pull request must not increase
   those counts, and should reduce them where it touches the affected files.

3. Open the pull request with:
   - **What changed** — what the change does, in one or two sentences.
   - **Why** — the problem it solves.
   - **Impact on the published numbers** — whether any index, regime label, spillover
     matrix or alert changes, and if so, the old and the new value. Write "no change
     to the published numbers" if there is none.
   - **Verification** — the commands you ran and what they printed.
   - **Anything a reviewer should look at** — the parts you are unsure about.

4. A pull request that changes a methodology parameter, an artefact schema or an API
   response needs a matching entry in `CHANGELOG.md` under `## [Unreleased]`.
5. A pull request that changes an indicator, a market or a country must update the
   locale catalogues in the same change, for all four locales.

## Adding a country

Adding an economy is a configuration change; no compute code has to be touched. The
procedure below is the one to follow.

### 1. Add the country configuration file

Create `packages/pipeline/configs/countries/<code lower-case>.yaml`, for example
`us.yaml`:

```yaml
code: US
name_en: United States
name_local: United States
currency: USD
timezone: America/New_York
locale: en-US
# The ECB composite indicator of systemic stress covers the United States, so
# the US composite has an official cross-check anchor.
ciss_area: US
official_index_ref: ECB_CISS_SS_CIN_US
methodology_ref: default
enabled: true

markets:
  - code: equity
    label_key: market.equity
    weight: 0.30
    indicators:
      - code: return_volatility
        label_key: indicator.return_volatility
        direction: same
        unit: percent
        source_adapter: akshare
        source_series_id: us.equity.return_volatility
        weight: 1.0
```

`load_settings()` reads every `*.yaml` in that directory in sorted order, so the file
is picked up automatically — there is no registry to update.

The fields:

| field | meaning |
| --- | --- |
| `code` | the country code; it becomes the artefact directory name and the API path segment |
| `name_en` | the English name used by the API and the catalogue |
| `currency`, `timezone`, `locale` | presentation metadata |
| `ciss_area` | the ECB CISS reference area used as the external cross-check anchor. Omit it when the source publishes no series for the country — Japan's configuration says so explicitly |
| `official_index_ref` | the identifier of the official index the composite is checked against |
| `markets[].weight` | the weight of the sub-market in the MBSED composite |
| `markets[].indicators[].direction` | `same`, `opposite` or `bidirectional` — how the indicator relates to systemic risk |
| `markets[].indicators[].source_adapter` | `akshare`, `ecb_ciss` or `boj` |
| `markets[].indicators[].source_series_id` | the series identifier the adapter understands |
| `markets[].indicators[].weight` | the weight inside the sub-market index |
| `markets[].indicators[].enabled` | `false` keeps an indicator in the file as a documented gap instead of substituting a proxy |

The market weights in `packages/pipeline/configs/global.yaml` are the Chinese
specification. A country that wants its own weights sets them in its own file.

### 2. Register the indicators

An indicator is only usable once its series exists in an adapter.

- **Chinese market series** are registered in
  `packages/pipeline/src/jindun/adapters/akshare_source.py`, either in `BASE_SERIES`
  (a direct read of one upstream table) or in `DERIVED_SERIES` (a deterministic
  transformation of base series). Register a series **only after verifying its output
  shape against the live service**; an unregistered series is reported as unavailable
  with a warning rather than silently returning zeros.
- **The ECB CISS composite** needs no registration. `EcbCissAdapter.fetch_composite()`
  takes the reference area from `ciss_area` and the daily composite `SS_CIN` covers
  the area. The euro-area components are a separate call, `fetch_components()`, and
  they exist only as `.CON` contribution series for `U2`.
- **The Bank of Japan API** is reached through `BojAdapter.fetch(database, codes)`.
  Use the BOJ series code as `source_series_id` in the form `boj.<DATABASE>.<code>`.

Then run `jindun-pipeline sources` and confirm that the new country appears with the
expected market and indicator counts.

### 3. Add the locale keys

**The locale catalogue is the single source of truth, shared by the server and the
front end.** The Python API never returns a display string: it returns stable codes,
and both the front end and the report generator look the label up in the same JSON
file. A country that is not in the catalogue renders as a missing-key marker in every
locale.

Add the keys to **all four** catalogue files — `locales/en-US.json`, `locales/zh-CN.json`,
`locales/zh-TW.json` and `locales/ja-JP.json`:

```json
"country.US": "United States",
"indicator.return_volatility": "Return Volatility"
```

The keys that a new country needs are:

| key pattern | what it covers |
| --- | --- |
| `country.<CODE>` | the country name, for every country in the catalogue |
| `market.<code>` | the sub-market names; these are shared across countries |
| `indicator.<code>` | the display name of every indicator the configuration references |

The indicator keys already exist for the Chinese indicator set. New indicators need a
key in all four catalogues.

Simplified and Traditional Chinese are written by hand, not converted: the financial
vocabulary genuinely differs between them, and a machine conversion of one into the
other would be wrong.

### 4. Run it

```bash
jindun-pipeline fetch --country US --refresh
jindun-pipeline run --country US
jindun-pipeline verify --country US
```

The run writes `data/runs/US/{market_indices.csv,run.json,quality.json}` and a
manifest next to the other runs. The API picks the country up automatically:
`GET /api/v1/countries` lists it and `GET /api/v1/countries/US/index` serves it.

### 5. Record the gap honestly

If a source does not publish a series for the new country, do not substitute a proxy.
Set `enabled: false` on the indicator, leave the `ciss_area` out when there is no
anchor, and say so in the country's comment block — the coverage table in the root
`README.md` is part of the deliverable and must be updated in the same change.

## Working with the locale catalogues

- The catalogues live at `<repo-root>/locales/<locale>.json`, one flat JSON object of
  dotted keys. The Vite plugin `packages/web/vite-plugin-locale-catalogue.ts` reads
  them at build time; `jindun.i18n` reads the same files at runtime.
- A key that is missing renders as `[i18n-missing]:<key>` rather than as an empty
  string, so a gap is loud.
- The server renders one message or a whole catalogue through
  `GET /api/v1/messages?locale=&key=`. Use it when you need the exact string the
  front end will show, for example in a notification.
- Adding or renaming a key is a breaking change for anything that stores the old key.
  Alert rules reference their message by key (`message_key`), so renaming a key
  requires updating `packages/pipeline/configs/global.yaml` in the same change.

## Reporting bugs and proposing features

Open an issue. For a bug, the useful parts are:

- the command you ran and its full output;
- the version (`jindun-pipeline --help`, and the `code_version` block of the run
  manifest);
- what you expected and what happened;
- the relevant artefact, if there is one: `data/runs/<CODE>/quality.json` is usually
  the first thing worth attaching, because it names the exact series and the exact
  threshold that failed.

Security vulnerabilities must **not** be reported through a public issue. Follow
`SECURITY.md`.
