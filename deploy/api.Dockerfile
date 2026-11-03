# The JinDun Sentinel API server.
#
# The image carries the pipeline, the API and the locale catalogue, because the
# API resolves the repository root at runtime and the artefact root follows it.
# The artefacts themselves are mounted in, not baked in: they are produced by
# the pipeline and change with every run.

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    JINDUN_ROOT=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "uv==0.11.26"

# The manifests and the lock file first, so the dependency layer is cached
# independently of the source.  The README files are needed as well: every
# package declares one and the build backend refuses to build without it.
COPY pyproject.toml uv.lock README.md ./
COPY packages/pipeline/pyproject.toml packages/pipeline/README.md ./packages/pipeline/
COPY packages/api/pyproject.toml packages/api/README.md ./packages/api/
COPY packages/agent/pyproject.toml packages/agent/README.md ./packages/agent/

# The lock file committed to the repository is the single source of truth for
# the dependency set, so the sync is frozen against it and the image installs
# exactly what that file records.  CI resolves the same lock file with
# `--locked`, which fails the build when a manifest changes without `uv lock`
# being run; that check is what keeps this layer reproducible.
RUN uv sync --frozen --no-dev --no-install-project --no-install-workspace

COPY packages ./packages
# The locale catalogue lives at the repository root and the pipeline reads it
# from there, so the image has to carry it as well.
COPY locales ./locales

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["uvicorn", "jindun_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
