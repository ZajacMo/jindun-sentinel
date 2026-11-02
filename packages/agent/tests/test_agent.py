"""Tests for the JinDun Sentinel agent.

The tests run against the artefacts that are published in the repository, so
they check the behaviour that a user actually gets: the numbers in an answer
are the numbers the pipeline published, the answer is rendered in the
requested locale and nothing reaches out to the network.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from jindun import paths

from jindun_agent import Agent, AgentConfig, AgentLocale, build_context_pack, select_tools
from jindun_agent.cli import main as cli_main
from jindun_agent.prompts import build_system_prompt, build_user_prompt
from jindun_agent.tools import build_registry

RUNS_DIR = paths.runs_dir()
CN_ARTEFACT = RUNS_DIR / "CN" / "run.json"

_ISO_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}(?:T[\d:.+-]+)?")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def run_payload() -> dict[str, Any]:
    """The published run artefact of China, read once for the whole session."""
    if not CN_ARTEFACT.is_file():
        pytest.skip(f"the published artefact {CN_ARTEFACT} is not available")
    return _load(CN_ARTEFACT)


@pytest.fixture(scope="session")
def quality_payload() -> dict[str, Any]:
    """The published data quality report of China."""
    path = RUNS_DIR / "CN" / "quality.json"
    if not path.is_file():
        pytest.skip(f"the published artefact {path} is not available")
    return _load(path)


@pytest.fixture(scope="session")
def global_payload() -> dict[str, Any]:
    """The published global artefacts, when the global layer has been built."""
    payload: dict[str, Any] = {}
    for name in ("cycle.json", "spillover.json"):
        path = RUNS_DIR / "global" / name
        if path.is_file():
            payload[name] = _load(path)
    return payload


def _numbers(payload: Any) -> set[str]:
    """Return every number of a JSON payload, rendered as it would be printed."""
    found: set[str] = set()
    if isinstance(payload, dict):
        for value in payload.values():
            found |= _numbers(value)
    elif isinstance(payload, list):
        for value in payload:
            found |= _numbers(value)
    elif isinstance(payload, bool):
        pass
    elif isinstance(payload, int):
        found.add(str(payload))
    elif isinstance(payload, float):
        found.add(repr(payload))
    return found


# ----------------------------------------------------------------------
# The context pack
# ----------------------------------------------------------------------


def test_context_pack_reads_the_published_artefact(run_payload: dict[str, Any]) -> None:
    pack = build_context_pack("CN")

    assert pack.available is True
    assert pack.country == "CN"
    assert pack.as_of == run_payload["as_of"]
    assert pack.composite == run_payload["composite"][-1]
    assert pack.percentile == run_payload["percentile"][-1]
    assert pack.deviation == run_payload["deviation"][-1]
    assert pack.regime is not None
    assert pack.regime["label"] == run_payload["regime"]["labels"][-1]
    assert pack.market_indices
    assert pack.spillover
    assert pack.composite_series


def test_context_pack_history_tail_is_bounded(run_payload: dict[str, Any]) -> None:
    pack = build_context_pack("CN", tail=5)

    assert len(pack.composite_series) == 5
    assert pack.composite_series[-1]["value"] == run_payload["composite"][-1]["value"]


def test_context_pack_is_language_neutral(run_payload: dict[str, Any]) -> None:
    """The pack must carry codes and numbers, never an English sentence."""
    pack = build_context_pack("CN")
    payload = json.dumps(pack.to_dict(), ensure_ascii=False)

    assert "Composite Stress Index" not in payload
    assert "As of" not in payload
    for sentence in ("the series", "risk regime", "no data"):
        assert sentence not in payload.lower()


def test_context_pack_reports_the_missing_global_layer(run_payload: dict[str, Any]) -> None:
    pack = build_context_pack("CN")

    if (RUNS_DIR / "global").is_dir():
        assert pack.global_cycle is not None or pack.global_spillover
    else:
        assert pack.global_cycle is None
        assert pack.global_spillover == []


# ----------------------------------------------------------------------
# The offline answer
# ----------------------------------------------------------------------


def test_offline_answer_contains_the_published_numbers(
    run_payload: dict[str, Any],
    quality_payload: dict[str, Any],
    global_payload: dict[str, Any],
) -> None:
    agent = Agent(config=AgentConfig(endpoint=None))
    answer = agent.ask("How stressed is the system?", country="CN", locale="en-US")

    assert answer.mode == "offline"
    assert answer.country == "CN"

    published = _numbers(run_payload) | _numbers(quality_payload) | _numbers(global_payload)
    printed = set(_NUMBER.findall(_ISO_DATETIME.sub(" ", answer.answer)))
    assert printed, "the offline answer should report at least one number"
    assert printed <= published, f"the answer reports numbers that were not published: {printed - published}"


def test_offline_answer_never_invents_a_number(
    run_payload: dict[str, Any],
    quality_payload: dict[str, Any],
    global_payload: dict[str, Any],
) -> None:
    agent = Agent(config=AgentConfig(endpoint=None))
    answer = agent.ask("What is the risk state right now?", country="CN", locale="en-US")

    published = _numbers(run_payload) | _numbers(quality_payload) | _numbers(global_payload)
    printed = set(_NUMBER.findall(_ISO_DATETIME.sub(" ", answer.answer)))
    assert not (printed - published)


def test_offline_answer_is_rendered_in_the_requested_locale() -> None:
    agent = Agent(config=AgentConfig(endpoint=None))
    answer = agent.ask("How stressed is the system?", country="CN", locale="zh-CN")

    zh = AgentLocale("zh-CN")
    assert zh.text("index.composite") in answer.answer
    assert zh.text("app.name") in answer.answer
    assert answer.locale == "zh-CN"


def test_unknown_locale_falls_back_to_english(run_payload: dict[str, Any]) -> None:
    agent = Agent(config=AgentConfig(endpoint=None))
    answer = agent.ask("How stressed is the system?", country="CN", locale="xx-XX")
    reference = agent.ask("How stressed is the system?", country="CN", locale="en-US")

    assert AgentLocale("xx-XX").resolved == "en-US"
    assert answer.locale == "en-US"
    assert answer.answer == reference.answer


def test_unknown_country_returns_a_localised_no_data_answer() -> None:
    agent = Agent(config=AgentConfig(endpoint=None))
    answer = agent.ask("How stressed is it?", country="ZZ", locale="zh-CN")

    zh = AgentLocale("zh-CN")
    assert answer.facts["available"] is False
    assert zh.text("common.empty") in answer.answer
    assert answer.country == "ZZ"


# ----------------------------------------------------------------------
# The tool registry
# ----------------------------------------------------------------------


def test_tool_registry_is_not_empty_and_returns_json_payloads() -> None:
    registry = build_registry()

    assert registry.names()
    for tool in registry.describe():
        kwargs = {"country": "CN"} if "country" in tool["parameters"] else {}
        payload = registry.call(tool["name"], **kwargs)
        assert isinstance(payload, dict)
        json.dumps(payload)  # must not raise


def test_tools_do_not_touch_the_artefacts(run_payload: dict[str, Any]) -> None:
    directory = CN_ARTEFACT.parent
    before = {path.name: (path.stat().st_mtime_ns, path.stat().st_size) for path in directory.iterdir()}

    registry = build_registry()
    for tool in registry.describe():
        kwargs = {"country": "CN"} if "country" in tool["parameters"] else {}
        registry.call(tool["name"], **kwargs)

    after = {path.name: (path.stat().st_mtime_ns, path.stat().st_size) for path in directory.iterdir()}
    assert before == after


def test_unknown_tool_is_rejected() -> None:
    registry = build_registry()

    with pytest.raises(KeyError):
        registry.call("does_not_exist")


def test_tool_selection_follows_the_question() -> None:
    assert "spillover_network" in select_tools("How does the spillover network look?")
    assert "alerts" in select_tools("Are there any active alerts?")
    assert select_tools("How stressed is the system?") == [
        "alerts",
        "composite_history",
        "data_quality",
        "global_layer",
        "latest_state",
        "spillover_network",
    ]


# ----------------------------------------------------------------------
# The prompts and the endpoint
# ----------------------------------------------------------------------


def test_prompt_asks_the_model_to_answer_in_the_requested_locale() -> None:
    system = build_system_prompt("zh-CN")
    user = build_user_prompt("How stressed is China?", {"country": "CN"}, "zh-CN")
    prompt = f"{system}\n{user}"

    assert "zh-CN" in prompt
    assert "locale" in prompt.lower()
    assert "never" in prompt.lower()


def test_configured_endpoint_is_used_and_its_failure_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        captured["url"] = url
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "a model answer"}}]}

    monkeypatch.setattr("jindun_agent.agent._post_json", fake_post)
    agent = Agent(config=AgentConfig(endpoint="https://example.invalid/v1", model="m"))
    answer = agent.ask("How stressed is China?", country="CN", locale="zh-CN")

    assert answer.mode == "llm"
    assert answer.answer == "a model answer"
    assert captured["url"] == "https://example.invalid/v1/chat/completions"
    assert "zh-CN" in captured["payload"]["messages"][0]["content"]


def test_failing_endpoint_falls_back_to_the_offline_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(url: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        raise OSError("no route to host")

    monkeypatch.setattr("jindun_agent.agent._post_json", boom)
    agent = Agent(config=AgentConfig(endpoint="https://example.invalid/v1"))
    answer = agent.ask("How stressed is China?", country="CN", locale="en-US")

    assert answer.mode == "offline"
    assert answer.llm_error
    assert answer.answer


def test_offline_path_never_touches_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the offline path must not reach out to the network")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setattr("httpx.post", boom, raising=False)

    agent = Agent(config=AgentConfig(endpoint=None))
    answer = agent.ask("How stressed is China?", country="CN", locale="en-US")

    assert answer.mode == "offline"
    assert answer.answer


# ----------------------------------------------------------------------
# The command line interface
# ----------------------------------------------------------------------


def test_cli_json_output_parses(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli_main(
        [
            "ask",
            "--question",
            "How stressed is China?",
            "--country",
            "CN",
            "--locale",
            "zh-CN",
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["country"] == "CN"
    assert payload["locale"] == "zh-CN"
    assert payload["answer"]
    assert payload["facts"]["available"] is True


def test_cli_tools_lists_the_registry(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli_main(["tools", "--json"])
    captured = capsys.readouterr()

    assert code == 0
    tools = json.loads(captured.out)
    assert tools
    assert {tool["name"] for tool in tools} >= {"latest_state", "spillover_network"}
