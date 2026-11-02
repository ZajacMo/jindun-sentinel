"""Tests for the shared core: models, configuration, i18n and the manifest."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from jindun.config import load_settings
from jindun.i18n import Translator
from jindun.indicators.transforms import apply_transform, first_difference, log_returns, zscore
from jindun.manifest import RunManifest, sha256_json, sha256_file
from jindun.models import Direction, Severity, series_from_mapping


def test_direction_accepts_the_source_vocabulary() -> None:
    assert Direction.parse("同向") is Direction.SAME
    assert Direction.parse("反向") is Direction.OPPOSITE
    assert Direction.parse("双向") is Direction.BIDIRECTIONAL
    assert Direction.parse("same") is Direction.SAME
    with pytest.raises(ValueError):
        Direction.parse("sideways")


def test_series_from_mapping_drops_unparsable_values() -> None:
    series = series_from_mapping(
        "x",
        "CN",
        "equity",
        [
            {"date": "2024-01-02", "value": 1.0},
            {"date": "2024-01-01", "value": 2.0},
            {"date": "2024-01-03", "value": "not-a-number"},
            {"date": "2024-01-04", "value": None},
        ],
    )
    assert len(series.observations) == 2
    assert series.observations[0].date.isoformat() == "2024-01-01"
    assert series.values() == [2.0, 1.0]


def test_severity_values_are_stable_codes() -> None:
    assert Severity.P1.value == "P1"
    assert Severity.P2.value == "P2"
    assert Severity.P3.value == "P3"


def test_settings_load_from_a_directory(tmp_path: Path) -> None:
    (tmp_path / "countries").mkdir()
    (tmp_path / "global.yaml").write_text(
        """
project:
  name: jindun-sentinel
  default_locale: en-US
locales:
  - code: en-US
    label: English
  - code: zh-CN
    label: 简体中文
index:
  pca_variance_threshold: 0.85
composite:
  market_weights:
    equity: 0.3
alert_rules:
  - id: composite.high
    severity: P1
    scope: all
""",
        encoding="utf-8",
    )
    (tmp_path / "countries" / "cn.yaml").write_text(
        """
code: CN
name_en: China
name_local: 中国
currency: CNY
timezone: Asia/Shanghai
locale: zh-CN
ciss_area: CN
markets:
  - code: equity
    label_key: market.equity
    weight: 0.3
    indicators:
      - code: pe
        direction: same
        unit: ratio
""",
        encoding="utf-8",
    )

    settings = load_settings(tmp_path)
    assert settings.project_name == "jindun-sentinel"
    assert settings.locale_codes == ("en-US", "zh-CN")
    assert settings.index.pca_variance_threshold == pytest.approx(0.85)
    assert settings.composite.market_weights["equity"] == pytest.approx(0.3)
    assert len(settings.alert_rules) == 1
    assert settings.alert_rules[0].severity == "P1"

    country = settings.country("CN")
    assert country is not None
    assert country.ciss_area == "CN"
    assert country.market("equity") is not None
    assert country.market("equity").indicator("pe").direction is Direction.SAME


def test_translator_renders_named_parameters() -> None:
    translator = Translator("en-US", {"greeting": "Hello {name}"})
    assert translator.text("greeting", name="world") == "Hello world"


def test_translator_selects_the_plural_branch() -> None:
    translator = Translator("en-US", {"alerts": "no alerts | one alert | {count} alerts"})
    assert translator.text("alerts", count=0) == "no alerts"
    assert translator.text("alerts", count=1) == "one alert"
    assert translator.text("alerts", count=7) == "7 alerts"


def test_translator_falls_back_to_english() -> None:
    translator = Translator("zh-CN", {"only.en": "English only"})
    translator._fallback = {"only.en": "English only"}
    assert translator.text("only.en") == "English only"


def test_missing_key_is_loud() -> None:
    translator = Translator("en-US", {})
    assert translator.text("nope.key").startswith("[i18n-missing]")
    assert not translator.has("nope.key")


def test_transforms() -> None:
    series = pd.Series([1.0, 2.0, 4.0, 8.0])
    assert first_difference(series).tolist() == [1.0, 2.0, 4.0]
    assert log_returns(series).iloc[0] == pytest.approx(np.log(2.0))
    standardised = zscore(pd.Series([1.0, 2.0, 3.0, 4.0]))
    assert standardised.mean() == pytest.approx(0.0, abs=1e-12)


def test_apply_transform_rejects_unknown_names() -> None:
    with pytest.raises(ValueError):
        apply_transform(pd.Series([1.0, 2.0]), "does-not-exist")


def test_manifest_round_trips(tmp_path: Path) -> None:
    manifest = RunManifest(
        run_id="2026-11-03T00-00-00Z",
        started_at="2026-11-03T00:00:00+00:00",
        code_version={"git_commit": "abc123"},
        data_snapshot={"rows": 10},
        outputs={"composite": "sha256:deadbeef"},
    )
    path = manifest.write(tmp_path / "manifest.json")
    restored = RunManifest.read(path)
    assert restored.run_id == manifest.run_id
    assert restored.data_snapshot == {"rows": 10}
    assert restored.outputs == {"composite": "sha256:deadbeef"}


def test_sha256_helpers(tmp_path: Path) -> None:
    target = tmp_path / "file.bin"
    target.write_bytes(b"jindun")
    assert len(sha256_file(target)) == 64
    assert sha256_json({"a": 1, "b": 2}) == sha256_json({"b": 2, "a": 1})


def test_manifest_payload_is_json_serialisable(tmp_path: Path) -> None:
    manifest = RunManifest(run_id="x", started_at="y")
    json.dumps(manifest.to_payload(), ensure_ascii=False)
