"""Start the whole application locally: the API and the front end.

Two processes have to run for the application to be usable — the FastAPI
server on port 8000 and the Vite dev server on port 5173 — and they have to
be started with the right working directories and the right API base URL.
This script does that with one command and stops both when it is interrupted.

    python scripts/serve_dev.py

It is a convenience wrapper, not a deployment: the API is started with
``--reload`` so that a change to the pipeline is picked up without a restart,
and the front end is started with Vite's hot module replacement.  Both write
to the terminal, prefixed so that their output can be told apart.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "packages" / "web"

API_PORT = int(os.environ.get("JINDUN_API_PORT", "8000"))
WEB_PORT = int(os.environ.get("JINDUN_WEB_PORT", "5173"))
API_BASE = f"http://localhost:{API_PORT}"


def _pump(stream, prefix: str) -> None:
    """Forward one process's output, line by line, with a prefix."""
    for line in iter(stream.readline, ""):
        try:
            sys.stdout.write(f"[{prefix}] {line}")
        except UnicodeEncodeError:
            # The console cannot represent a character the child printed.  The
            # output is a log, not a result, so it is dropped rather than
            # allowed to end the forwarding thread.
            sys.stdout.write(f"[{prefix}] <unrepresentable output>\n")
    stream.close()


def _start(command: list[str], prefix: str, cwd: Path, env: dict[str, str] | None = None):
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    threading.Thread(target=_pump, args=(process.stdout, prefix), daemon=True).start()
    return process


def _npm() -> list[str]:
    """The npm command for this platform."""
    return ["npm.cmd", "run", "dev"] if sys.platform == "win32" else ["npm", "run", "dev"]


def main() -> int:
    # The output of the two children is forwarded to this process's stdout.
    # When that stdout is a pipe rather than a terminal it is block-buffered,
    # and the operator would see nothing until the buffer filled up.
    #
    # The encoding matters on Windows: the default console code page cannot
    # represent the characters the front end prints, and a thread that fails
    # to write one of them takes the whole log down with it.  The stream is
    # therefore switched to UTF-8 and told to replace what it cannot encode
    # instead of raising.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

    if not WEB_DIR.is_dir():
        print(f"the front end package is missing: {WEB_DIR}", file=sys.stderr)
        return 1

    api = _start(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "jindun_api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(API_PORT),
            "--reload",
        ],
        "api",
        cwd=REPO_ROOT,
    )

    web_env = dict(os.environ)
    web_env["VITE_API_BASE"] = API_BASE
    web = _start(_npm(), "web", cwd=WEB_DIR, env=web_env)

    print()
    print(f"  API      {API_BASE}/api/docs")
    print(f"  Front end http://localhost:{WEB_PORT}/")
    print("  Press Ctrl-C to stop both.")
    print()

    try:
        while api.poll() is None and web.poll() is None:
            threading.Event().wait(0.5)
    except KeyboardInterrupt:
        print("\nstopping…")
    finally:
        for process in (web, api):
            if process.poll() is None:
                process.terminate()
        for process in (web, api):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
