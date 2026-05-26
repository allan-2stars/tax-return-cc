# Tax Return AI

AI-guided Australian tax preparation workspace for Australian individual taxpayers.

This tool organises your tax documents and prepares a review package for your
registered tax agent. It does not lodge returns, connect to the ATO, or provide
final tax advice.

---

## First-time setup on Raspberry Pi

1. `git clone <repo> && cd tax-return-cc`
2. `make setup-dirs`      ← **required before first run — creates data directories**
3. `make env`             ← then edit `.env` with your values
4. `make dev-build`       ← first build takes ~15–20 min on Pi
5. `make health`          ← confirm everything is running

## Daily development

```bash
make dev          # start all services
make test         # run backend tests
make dev-logs     # tail logs
make dev-down     # stop services
```

## Production routing (same-site proxy)

Normal browser traffic must use the frontend origin only:

- Browser: `https://taxcc.signpega.com`
- Frontend proxies: `/api/*` -> `http://backend:8000/api/*` (internal Docker network)
- Backend cookies: host-only, httpOnly, `SameSite=Strict` (set via the proxied response)
- SSE: `GET /api/v1/documents/{id}/stream` remains on the frontend origin

`https://taxcc-api.signpega.com` should be treated as ops/debug only (not used by the app in normal usage).

## Useful commands

```bash
make shell-be     # bash inside backend container
make db-shell     # SQLite shell (dev)
make migrate-dev  # run pending migrations
make freeze       # freeze pip deps to requirements.lock
```

See `make help` for the full list.
