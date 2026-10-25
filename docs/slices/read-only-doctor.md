# Read-only readiness doctor

Run from the repository root after explicitly installing the normal backend environment:

```sh
make doctor
make doctor args="--mode authoring --json"
# Or: backend/.venv/bin/python -B scripts/doctor.py --mode authoring --json
```

`make doctor` refuses a missing backend environment; it does not invoke a package manager,
create a venv or install dependencies. The command does not import the FastAPI application,
start services, create folders, apply migrations, download models or perform inference.

The default `local` mode requires the API, SQLite, Ollama and Qdrant metadata probes. The
`authoring` mode requires API/database and accessible credential storage plus key presence;
unavailable local inference/retrieval services are warnings because manual hosted authoring
can continue without them. Optional warnings produce `degraded`, not total unavailability.

Exit codes: 0 healthy; 1 degraded (warnings); 2 unavailable (required check/configuration fails).
`--timeout` is 0.1–10 seconds, default 2, enforced for each parallel network probe. `--api-url`
can point to another plain loopback API port. Proxies, credentials/queries in URLs, remote
hosts and redirects are refused. Only GET /api/health, /api/tags and /readyz are used.

SQLite is opened using mode=ro with query_only. No normal engine initialization or migration
is run. The check verifies the file and expected application tables, not full integrity or
whether every migration has been applied. SQLite may manage its normal WAL reader sidecars;
the diagnostic cannot change database contents. Key-file contents are never read: only path,
existence, nonempty size, regular-file status and access metadata are inspected. Environment
settings are loaded through the normal Settings class; their values are never rendered.

Directory access is checked for the user running doctor, so run it as the API service user,
not with sudo. A present key is explicitly `present_unverified`: validity, provider account,
quota/billing, authoring preference/budget and particular model availability are not certified.
Doctor cannot guarantee a later write succeeds against disk-full, races or permission changes.
It gives an actionable ownership/access warning instead of trying to repair storage itself.

Healthy/failure tests use temporary databases and HTTP metadata mocks, including complete
timeout, malformed/oversized replies, remote/credential-bearing endpoints, missing database,
missing/corrupt schema, inaccessible key storage, symlinks and secret-free error output.

## Verification — 2026-10-25

Doctor 25 tests passed, including healthy, degraded and unavailable cases. Combined doctor and
preference-kernel suite 29 passed. Live metadata-only local/authoring checks returned healthy;
a deliberately closed API port returned unavailable / exit 2. No paid/model call was made.
Backend Ruff, format and mypy pass. This is readiness evidence, not answer-quality certification.
