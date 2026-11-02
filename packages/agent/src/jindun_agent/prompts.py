"""The prompt templates of the agent.

The prompts are English on purpose: the *instructions* address the model, and
the *answer* is rendered in the locale the user asked for.  The locale
instruction is therefore stated explicitly in the system prompt, because a
model that is prompted in English tends to answer in English when the
requirement is left implicit.

The context pack is embedded verbatim.  It is the only source of numbers the
model is allowed to use, and the prompt says so.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = [
    "SYSTEM_PROMPT",
    "build_system_prompt",
    "build_user_prompt",
    "render_context",
]

SYSTEM_PROMPT = """You are the analyst assistant of JinDun Sentinel, a multi-country \
systemic financial risk monitoring and early warning system.

You answer questions about the risk state that the computation pipeline has \
already published for a country.  The context pack you receive is the only \
source of facts you may use.

Rules:
- Use only the numbers, dates and codes that appear in the context pack. Never \
invent, extrapolate, round into a new value or guess a number; if a value is \
missing, say that the data is missing.
- Keep the identifiers of the context pack unchanged (country codes, market \
codes, regime codes, severity codes and rule identifiers are stable codes, not \
words to translate).
- Report dates as they are given, in ISO-8601 form.
- If the context pack does not contain what the question asks about, say that \
the published artefacts do not cover it and name what is available.
- Be concise and lead with the conclusion. Do not add a forecast, an opinion or \
a recommendation that the artefacts do not support.
- Write the whole answer in the language of the locale tag that is requested \
below, including the headings. Keep numbers, codes and dates as they are.
"""


def build_system_prompt(locale: str) -> str:
    """Return the system prompt for one locale."""
    return (
        f"{SYSTEM_PROMPT}\n"
        f"Requested locale: {locale}. Write the entire answer in the language of "
        f"the locale tag `{locale}`; the locale tag defines the language of the "
        f"answer, not the language of the instructions."
    )


def render_context(context: dict[str, Any]) -> str:
    """Return the context pack as indented JSON."""
    return json.dumps(context, ensure_ascii=False, indent=2, sort_keys=False)


def build_user_prompt(question: str, context: dict[str, Any], locale: str) -> str:
    """Return the user prompt for one question and one context pack."""
    return (
        f"Question: {question}\n\n"
        f"Context pack (authoritative, JSON):\n"
        f"{render_context(context)}\n\n"
        f"Answer the question in the locale `{locale}`. Quote only numbers that "
        f"appear in the context pack."
    )
