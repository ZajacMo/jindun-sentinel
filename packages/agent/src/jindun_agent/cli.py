"""The command line interface of the JinDun Sentinel agent.

Two commands, both read-only:

``ask``
    Answer a question about the published run artefacts, in the requested
    locale.  ``--json`` prints the full structured answer instead of the
    rendered text.

``tools``
    List the read-only tools the agent may call.

The output is UTF-8 even on a Windows console, because the answers carry the
locale catalogue and the catalogue is not ASCII.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections.abc import Sequence

from .agent import Agent
from .locale import DEFAULT_LOCALE
from .tools import build_registry

__all__ = ["main", "build_parser"]


def _force_utf8() -> None:
    """Write UTF-8 to stdout and stderr, even on a Windows console."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(AttributeError, ValueError):
                reconfigure(encoding="utf-8")


def _cmd_ask(args: argparse.Namespace) -> int:
    agent = Agent()
    answer = agent.ask(args.question, country=args.country, locale=args.locale)
    if args.as_json:
        print(json.dumps(answer.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(answer.answer)
    return 0


def _cmd_tools(args: argparse.Namespace) -> int:
    registry = build_registry()
    tools = registry.describe()
    if args.as_json:
        print(json.dumps(tools, ensure_ascii=False, indent=2))
        return 0
    for tool in tools:
        print(f"{tool['name']} - {tool['description']}")
        for name, description in tool["parameters"].items():
            print(f"    {name}: {description}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser of the agent."""
    parser = argparse.ArgumentParser(
        prog="jindun-agent", description="JinDun Sentinel analyst agent"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask", help="ask a question about the published artefacts")
    ask.add_argument("--question", required=True, help="the question to answer")
    ask.add_argument("--country", default=None, help="ISO country code, for example CN")
    ask.add_argument("--locale", default=DEFAULT_LOCALE, help="locale of the answer")
    ask.add_argument(
        "--json", dest="as_json", action="store_true", help="print the structured answer"
    )
    ask.set_defaults(func=_cmd_ask)

    tools = subparsers.add_parser("tools", help="list the read-only tools of the agent")
    tools.add_argument(
        "--json", dest="as_json", action="store_true", help="print the registry as JSON"
    )
    tools.set_defaults(func=_cmd_tools)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""
    _force_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
