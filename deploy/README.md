# The JinDun Sentinel application, in containers

Two services: the API, which serves the artefacts the pipeline produced, and
the web front end, which is a static bundle behind nginx.

## Run it

```powershell
docker compose -f deploy/docker-compose.yml up --build
```

Then open:

| Service | URL |
| --- | --- |
| the web front end | <http://localhost:5173/> |
| the API | <http://localhost:8000/api/v1> |
| the interactive API documentation | <http://localhost:8000/api/docs> |

The front end calls the API on its own origin and nginx proxies the `/api/`
prefix, so the browser makes no cross-origin request.

## What the containers need from the host

The `data/` directory of the repository is mounted into the API container, so
the artefacts a pipeline run produced are served without a rebuild.  The API
never recomputes an index: it reads what the pipeline wrote.

The raw source snapshots are **not** in the repository — they are fetched:

```powershell
.venv\Scripts\python.exe -m jindun.cli fetch
.venv\Scripts\python.exe -m jindun.cli run
.venv\Scripts\python.exe -m jindun.cli global
```

A container that has to fetch for itself needs network access to the
publishers; see the data-source table in the root `README.md`.

## What is inside the images

| Image | Content |
| --- | --- |
| `jindun-sentinel/api` | the pipeline, the API and the locale catalogue, installed from the workspace lock file with `uv sync --frozen` |
| `jindun-sentinel/web` | the front end built with Vite, served by nginx |

The web build reads three directories from the repository — the front end, the
locale catalogue and the methodology documents — and all three are read at
build time.  The documentation shown in the browser is therefore the
documentation that is in the repository, with no second copy to keep in step.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `JINDUN_ROOT` | `/app` | the directory the API resolves the artefact root from |
| `JINDUN_RUNS_DIR` | unset | overrides the artefact directory outright |
| `JINDUN_CORS_ORIGINS` | `http://localhost:5173,…` | the origins allowed to call the API directly |

## Note on the daily run

There is deliberately **no scheduled GitHub Actions workflow** here: the daily
refresh stays a local operation, and this directory only carries the
containers.  A scheduled workflow can be added on top of the same command
(`python -m jindun.cli run && python -m jindun.cli global`) without changing
anything in these files.
