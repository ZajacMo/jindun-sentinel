"""Add the locale keys that the product renders but the catalogue lacked.

Simplified and Traditional Chinese are written by hand and separately: the
financial vocabulary genuinely differs between them, so a machine conversion
would be wrong.  The Japanese uses the natural financial terms.
"""

from __future__ import annotations

import json
from pathlib import Path

LOCALES = Path(__file__).resolve().parents[1] / "locales"

ADDITIONS: dict[str, dict[str, str]] = {
    "en-US": {
        "common.regime": "Regime",
        "index.official": "Official Systemic Stress Index",
        "market.systemic": "Systemic",
        "indicator.official_index": "Official stress index",
        "indicator.call_rate_term_spread": "Money Market Term Spread",
        "indicator.usdjpy_volatility": "USD/JPY Volatility",
        "indicator.usdjpy_deviation": "USD/JPY Deviation from Trend",
    },
    "zh-CN": {
        "common.regime": "区制",
        "index.official": "官方系统性压力指数",
        "market.systemic": "系统性",
        "indicator.official_index": "官方压力指数",
        "indicator.call_rate_term_spread": "货币市场期限利差",
        "indicator.usdjpy_volatility": "美元兑日元波动率",
        "indicator.usdjpy_deviation": "美元兑日元趋势偏离",
    },
    "zh-TW": {
        "common.regime": "區制",
        "index.official": "官方系統性壓力指數",
        "market.systemic": "系統性",
        "indicator.official_index": "官方壓力指數",
        "indicator.call_rate_term_spread": "貨幣市場期限利差",
        "indicator.usdjpy_volatility": "美元兌日圓波動率",
        "indicator.usdjpy_deviation": "美元兌日圓趨勢偏離",
    },
    "ja-JP": {
        "common.regime": "レジーム",
        "index.official": "公的システム的ストレス指数",
        "market.systemic": "システム全体",
        "indicator.official_index": "公的ストレス指数",
        "indicator.call_rate_term_spread": "コールレート期間スプレッド",
        "indicator.usdjpy_volatility": "ドル円ボラティリティ",
        "indicator.usdjpy_deviation": "ドル円のトレンド乖離",
    },
}

#: Where every new key is inserted, so that the catalogues keep their shape.
ANCHORS: dict[str, str] = {
    "common.regime": "common.retry",
    "index.official": "index.deviation",
    "market.systemic": "market.derivative",
    "indicator.official_index": "indicator.csi300_futures_volatility",
    "indicator.call_rate_term_spread": "indicator.official_index",
    "indicator.usdjpy_volatility": "indicator.call_rate_term_spread",
    "indicator.usdjpy_deviation": "indicator.usdjpy_volatility",
}


def main() -> int:
    for locale, additions in ADDITIONS.items():
        path = LOCALES / f"{locale}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        updated: dict[str, str] = {}
        for key, value in payload.items():
            updated[key] = value
            for new_key, new_value in additions.items():
                if ANCHORS.get(new_key) == key:
                    updated[new_key] = new_value
        for new_key, new_value in additions.items():
            updated.setdefault(new_key, new_value)
        path.write_text(
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{locale}: {len(updated)} keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
