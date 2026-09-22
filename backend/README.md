# Study Matcher backend

FastAPI API backed by Supabase. Run commands from the repository root.

```sh
uv sync --frozen
uv run uvicorn app.main:app --app-dir backend --reload
```

Configure the variables listed in `backend/.env.example`. Never commit secrets.

## Railway

Use the repository root as the service root and this start command:

```sh
uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT --workers 1
```

Set `CORS_ORIGINS` to the web application's exact origin. `/health` checks process
availability; it does not verify database connectivity. Chat and scheduling use
process-local state, so keep one worker.

## Tests

```sh
uv run python backend/tests/run_integration.py
uv run python backend/tests/live_smoke.py --base-url https://YOUR_BACKEND
```

Local integration tests substitute Supabase and do not establish real database,
RLS, concurrency or deployment correctness. Generated results are ignored.
