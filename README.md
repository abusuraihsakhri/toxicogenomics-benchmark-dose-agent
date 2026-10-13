# Toxicogenomics Benchmark Dose Agent

A Python and browser demonstration of **fixed-threshold sample auditing**. The software evaluates two numeric metrics, an explicit critical flag, and descriptor keywords, then generates a rule-based report. It includes two historical Python implementations: `agents/` (primary CLI/API) and `tox_benchmark/` (alternative CLI/API).

> **Scientific limitation:** Despite the repository name, the current software does **not** fit dose–response models, calculate BMD or BMDL, infer benchmark-response confidence intervals, or perform transcriptomic pathway enrichment. The cutoffs 25 and 12 in `agents/` (25 and 10 in `tox_benchmark/`) are demonstration constants—not scientifically validated toxicity or clinical cutoffs. Outputs must not be used for regulatory, clinical, or toxicological decisions.

## Browser demonstration

The standalone page is `web/index.html`. Open it in a modern browser or serve the file with a local HTTP server. Evaluation uses JavaScript rules matching `agents/workers.py`; it does not require Python, a remote backend, or Pyodide. It supports form validation and JSON report export. No BMD/BMDL is calculated, and no HMAC signatures are fabricated.

If GitHub Pages is enabled for this repository with **GitHub Actions** as its source, `.github/workflows/pages.yml` deploys the browser demonstration from `web/` on updates to `master`. A public URL should only be advertised after verifying a successful deployment.

## Installation and CLI

Requirements: Python 3.10 or newer.

```bash
git clone https://github.com/abusuraihsakhri/toxicogenomics-benchmark-dose-agent.git
cd toxicogenomics-benchmark-dose-agent
python -m pip install -e ".[api,test]"
python cli.py audit --task-id DEMO-001 --target SAMPLE-01 --primary 29.4 --secondary 14.8
python cli.py verify-audit
python cli.py batch --input sample.csv --output results.csv
python -m pytest -q
```

The installed console entry point `toxicogenomics-benchmark-dose-engine` calls the alternative `tox_benchmark.cli` module. Both CLI implementations support `audit`, `batch`, `chat`, and `serve`, but use different historical demo thresholds and return distinct report schemas. The root `cli.py` additionally provides `verify-audit`. CSV input requires `task_id`, `target_identifier`, and `primary_metric` headers; optional fields include `secondary_metric`, `status_descriptor`, and `is_critical_flag` (true/false, 1/0, yes/no). Invalid input aborts before writing the result CSV.

## API and Docker

Start the primary API:

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the standalone browser interface and `http://127.0.0.1:8000/docs` for the primary FastAPI documentation. The backend supports `POST /api/audit`, `POST /api/chat`, `GET /health`, `GET /metrics` and `GET /api/audit/logs`. The `/metrics` response is currently JSON, **not Prometheus text**. `/api/chat` uses a deterministic mock; remote model providers are not implemented.

Docker Compose requires a separately configured audit secret and binds to localhost by default:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
docker compose up --build
```

The audit log is **in-memory**: signatures are HMAC-SHA256 chained and verified against the configured key, but entries are not durably stored and are lost on process restart. A stable key alone does not provide durable audit retention. The demo API has **no authentication**; do not expose it on the public internet without an authentication/reverse-proxy layer.

## Data handling and security

The browser demonstration processes values locally without analytics, cookies, network requests, or browser storage. JSON export happens via a local blob. Do not enter patient-identifiable data. The Python service applies a limited regular-expression identifier screen; **it is not a complete PHI de-identification solution or a HIPAA compliance guarantee**. The API holds reports and audit metadata in memory, and the audit endpoints expose metadata if deployed without access control. Do not submit sensitive data to an unsecured instance.

Dependencies are `pydantic` (core models), optional `fastapi` and `uvicorn` (API), and optional `pytest` and `httpx` (tests). CI exercises Python 3.10–3.12. The browser demonstration is intended for current desktop and mobile browsers supporting standard form APIs, Blob downloads, and modern JavaScript.

## Project layout

- `agents/`, `cli.py`: primary rule engine, HMAC audit, mock assistant, CLI and FastAPI service
- `tox_benchmark/`: alternative historical threshold engine and CLI/API
- `web/index.html`: offline, dependency-free browser demonstration
- `enrichment.py`: independent threshold-based demonstration modules, not biological enrichment analysis
- `tests/`: Python regression tests
- `.github/workflows/`: Python CI and optional GitHub Pages deployment

## License

MIT. See [LICENSE](LICENSE).
