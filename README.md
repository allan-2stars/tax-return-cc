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

## Useful commands

```bash
make shell-be     # bash inside backend container
make db-shell     # SQLite shell (dev)
make migrate-dev  # run pending migrations
make freeze       # freeze pip deps to requirements.lock
```

See `make help` for the full list.
