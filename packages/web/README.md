# JinDun Sentinel — web front end

The Vue 3 front end of JinDun Sentinel, the open-source multi-country systemic
financial risk monitoring and early-warning system.  The Python pipeline and the
API live in sibling packages; this package only renders what the API serves.

## Install

The package is self-contained; install it from inside `packages/web` so that no
workspace root is involved:

```bash
cd packages/web
npm install
```

Node 22 and npm 10 are expected.

## Run the development server

```bash
npm run dev
```

Vite serves the application on <http://localhost:5173>.  The dev server is
allowed to read the repository root, because the locale catalogue and the
methodology notes live outside this package.

## Point it at the API

The API base URL is read from `VITE_API_BASE` and defaults to
`http://localhost:8000`:

```bash
VITE_API_BASE=http://localhost:8000 npm run dev
```

Copy `.env.example` to `.env.local` to make the setting permanent.  The client
appends the endpoint paths itself, so the value must be the *base* of the API,
without `/api/v1`.

Every request goes through `src/api/client.ts`, which applies a timeout
(10 s), a bounded retry with exponential backoff (two extra attempts on
network errors, `408`, `429` and `5xx`), and turns every failure into an
`ApiError`.  The pages render that error — a failed request never produces a
silent empty screen.

## Build and preview

```bash
npm run build     # vue-tsc type check + production bundle into dist/
npm run preview   # serve the production bundle
```

## Test

```bash
npm test          # vitest, single run
npm run test:watch
```

The suite covers the locale mapping helpers, the `Intl` based formatting
helpers, the wiring of the shared locale catalogue, the typography rules of the
global stylesheet, every mechanism diagram, and a smoke test that mounts each
of the seven workspace pages.

## How the locale catalogue is wired

The catalogue is the single source of truth for every translatable string in
the application.  It lives in `<repo-root>/locales/<locale>.json` — that is
`../../locales` relative to this package — and the Python server reads the very
same files through `jindun.i18n`.

* `vite-plugin-locale-catalogue.ts` is a small Vite plugin that reads the
  directory at build time and serves it as the virtual module
  `virtual:jindun-locale-catalogue`.
* `src/i18n/catalogue.ts` normalises the catalogues (flat `"a.b": "..."` keys
  and nested objects are both accepted) into the nested shape `vue-i18n`
  expects.
* `src/i18n/index.ts` creates the `vue-i18n` instance in `legacy: false` mode.

`fallbackLocale` is `false` on purpose: a message that is missing from the
catalogue renders as its own key, so a translation gap is loud instead of
silently showing an English string in another language.

The API itself is language neutral — numbers are numbers, dates are ISO-8601
strings and enumerations are stable codes such as `"high"` or `"P1"`.  The
mapping from a code to a catalogue key lives in `src/utils/codes.ts`, and
`src/composables/useLabels.ts` binds it to the active locale.

### Key set the front end expects

The fixed key set is the one described in the project brief:
`app.*`, `nav.*`, `country.*`, `market.*`, `indicator.*`, `index.*`,
`regime.*`, `severity.*`, `metric.*`, `method.*`, `lens.*`, `scope.*`,
`quality.*`, `unit.*`, `time.*`, `common.*` and `alert.*`.

Two diagram stages have no catalogue entry and are therefore rendered with the
technical vocabulary of the methodology rather than with a message: the
pipeline stage **Adapters** and the model names **PCA**, **CRITIC**, **VAR**,
**VMA**, **API** and **UI**.  The ECB CISS anchor and the BIS edges in the
global network are proper nouns and are not translated either.

## Typography

The font stack is declared once, as `--jd-font-stack` in
`src/styles/tokens.css`, and is never repeated in a component.  The line
height follows the script of the active locale and is implemented as a
cascade on the `lang` attribute of the document element in
`src/styles/base.css`:

| locale     | line height |
| ---------- | ----------- |
| Latin      | 1.5         |
| `zh-CN`    | 1.7         |
| `zh-TW`    | 1.7         |
| `ja-JP`    | 1.8         |

Numeric columns use `font-variant-numeric: tabular-nums` so that the tables do
not jitter while they re-render.

## Theming

Element Plus is re-skinned from the same CSS custom properties
(`src/styles/tokens.css`).  The light theme is the default; the dark theme is
activated by the `dark` class on `<html>`, which the theme toggle in the
header sets.  The severity colours P1/P2/P3 are never distinguished by hue
alone — every severity badge carries an icon of a distinct shape and a text
label.

## Mechanism diagrams

Every workspace page carries at least one hand-written inline SVG diagram that
shows how the thing works.  They live in `src/components/diagrams/` and are
plain Vue components with `<svg>` markup — no chart library is involved.  They
are responsive (`viewBox` plus `preserveAspectRatio`), themed through CSS
custom properties and accessible (`role="img"` with a `<title>` and a
`<desc>`).

| component               | shows                                                                     |
| ----------------------- | ------------------------------------------------------------------------- |
| `PipelineDiagram`       | the daily pipeline, with the rejection branch of a failed quality gate     |
| `SpilloverMechanism`    | a shock propagating through the VAR impulse responses over the horizon     |
| `RegimeMechanism`       | the two-component mixture over the log composite and the two states        |
| `AlertLoop`             | detect → attribute → notify → acknowledge → resolve, with the silence window |
| `GlobalNetwork`         | the five economies, their market layers, the ECB CISS anchor, the BIS edges  |
| `MarketIndexMechanism`  | how a market index is built and combined into the composite                 |
| `QualityGateMechanism`  | the quality gate, its checks and the two outcomes                           |
| `EstimatorStack`        | the VAR, the VMA coefficients and the four spillover estimators             |

The chord diagram of the spillover network (`src/components/charts/SpilloverNetwork.vue`)
is also written by hand; only the time series use ECharts.

## Layout

```
src/
├── api/            typed API client, endpoint functions, payload normalisers
├── components/     header, navigation, charts and the mechanism diagrams
├── composables/    labels, formatting and the ECharts binding
├── content/        the methodology notes, read at build time
├── i18n/           the vue-i18n instance and the catalogue normaliser
├── pages/          one component per route
├── router/         the seven routes
├── stores/         Pinia: preferences and fetched data
├── styles/         design tokens and the global stylesheet
└── utils/          code mapping, `Intl` formatting, the Markdown renderer
```

## API endpoints the client expects

| endpoint                                   | used by                       |
| ------------------------------------------ | ----------------------------- |
| `GET /api/v1/health`                       | —                             |
| `GET /api/v1/countries`                    | the country selector          |
| `GET /api/v1/countries/{code}/index`       | overview, countries, detail   |
| `GET /api/v1/countries/{code}/spillover`   | detail, spillover             |
| `GET /api/v1/countries/{code}/alerts`      | alerts                        |
| `GET /api/v1/countries/{code}/data-quality`| data quality                  |
| `GET /api/v1/global/spillover`             | spillover                     |
| `GET /api/v1/global/gsib`                  | spillover                     |

The quality report is served by the API under the country
(`/api/v1/countries/{code}/data-quality`); the client falls back to the flat
path `/api/v1/data-quality/{code}` when the server answers `404`, so it works
against either shape of the contract.

The normalisers in `src/api/types.ts` accept the shapes the pipeline writes
(`{dates, values}`, `[{date, value}]`, `{dates, series}`) as well as the
simplified shapes an API may serve, so the client keeps working when the
server and the front end are developed in parallel.
