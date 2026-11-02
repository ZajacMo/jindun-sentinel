# jindun-agent

The analyst layer of JinDun Sentinel: it answers questions about the systemic
risk state that the pipeline has already published.

The agent is strictly read-only. It reads the run artefacts in
`data/runs/<COUNTRY>/run.json` (and the global layer in `data/runs/global/`)
and never recomputes an index, exactly like the API server. Every number it
reports is a number the pipeline published; when the data is missing it says
so instead of estimating one.

## Install

```bash
uv sync                      # from the repository root
# or, into an existing environment:
pip install -e packages/agent
```

The package needs `jindun-pipeline` (for `jindun.paths` and the shared locale
catalogue) and `pydantic`. The optional `llm` extra adds `httpx`; the agent
falls back to the standard library when `httpx` is not installed.

## Run

```bash
jindun-agent ask --question "How stressed is China?" --country CN --locale zh-CN
jindun-agent ask --question "How does the spillover network look?" --json
jindun-agent tools
```

`--json` prints the whole structured answer: the rendered text, the
language-neutral facts, the tools that were used and the context pack. The
output is UTF-8 on every console, including the Windows one.

## Offline behaviour

Without a configured endpoint the agent answers deterministically, from the
artefacts and from the shared locale catalogue in `locales/*.json`:

* the country is taken from `--country`, or inferred from the question;
* the relevant read-only tools are called and a language-neutral context pack
  is assembled from them (numbers stay numbers, dates stay ISO-8601, the
  enumerations stay the stable codes the pipeline writes);
* the answer is rendered in the requested locale. An unknown locale falls back
  to `en-US`, and a country without a published artefact gets a localised
  "no data" answer instead of an error.

The offline path never opens a socket and never fails: if an endpoint is
configured but unreachable, the agent falls back to the offline answer and
reports the failure in the `llm_error` field of the JSON output.

## Pointing it at an OpenAI-compatible endpoint

Set the environment variables and the agent switches to the model:

| variable                | meaning                                             |
| ----------------------- | --------------------------------------------------- |
| `JINDUN_AGENT_ENDPOINT` | the endpoint, for example `https://host/v1`          |
| `JINDUN_AGENT_MODEL`    | the model name (default `gpt-4o-mini`)               |
| `JINDUN_AGENT_API_KEY`  | the bearer token, when the endpoint needs one        |
| `JINDUN_AGENT_TIMEOUT`  | the request timeout in seconds (default `60`)        |

```bash
export JINDUN_AGENT_ENDPOINT="https://api.example.com/v1"
export JINDUN_AGENT_MODEL="your-model"
export JINDUN_AGENT_API_KEY="your-key"
jindun-agent ask --question "How stressed is China?" --country CN --locale zh-CN
```

The endpoint is called with a standard `POST <endpoint>/chat/completions`. The
prompts are always English, because the instructions address the model; the
*answer* is rendered in the requested locale, and the prompt says so
explicitly. The context pack is the only source of numbers the model may use.

## The tools

`jindun-agent tools` lists the read-only tools the agent may call:
`latest_state`, `composite_history`, `spillover_network`, `alerts`,
`data_quality` and `global_layer`. Each of them takes an explicit country code
and returns a JSON-safe payload.

## Tests

```bash
python -m pytest packages/agent/tests -q
```
