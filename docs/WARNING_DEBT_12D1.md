# WARNING_DEBT_12D1.md

## Scope

Milestone 12D-1 warning debt cleanup across backend + frontend tests.

## Warning Sources, Root Cause, Fix

## 1) Backend: `coroutine 'sleep' was never awaited`
- **Source:** `backend/tests/test_events.py`
- **Root cause:** tests patched async `recalculate()` and assigned `mock_recalc.return_value = asyncio.sleep(0)`, which creates a coroutine object that was never awaited.
- **Fix:** replaced all `mock_recalc.return_value = asyncio.sleep(0)` with `mock_recalc.return_value = None` (for async mock this is awaitable-safe return data), and removed now-unused per-test `import asyncio` statements.

## 2) Frontend: React `act(...)` warnings in AskClaudeDrawer tests
- **Source:** `frontend/__tests__/AskClaudeDrawer.test.tsx`
- **Root cause:** tests used `fireEvent` with async state transitions triggered by promises (`askClaude`), without awaiting interaction sequencing.
- **Fix:** moved to `userEvent` with `await` for typing/clicking and async assertions via `waitFor`.

## 3) Frontend: noisy console output from login error-path tests
- **Source:** `frontend/__tests__/login.test.tsx`
- **Root cause:** component intentionally calls `console.error` in rejected login paths, producing noisy expected error logs during tests.
- **Fix:** added scoped `console.error` spy in tests (`beforeEach`/`afterEach`) to keep output clean while preserving behavior assertions.

## 4) Backend: Pydantic v2 deprecation warning
- **Source:** `backend/app/config.py`
- **Root cause:** legacy class-based `Config` on `BaseSettings` under Pydantic v2 emits `PydanticDeprecatedSince20`.
- **Fix:** migrated to `SettingsConfigDict` via `model_config`.

## Verification

- `make test-fe` passes.
- `make test` passes.
- Backend run now completes with no warning summary entries.

