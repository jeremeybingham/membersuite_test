# AGENTS.md

Guidance for AI coding agents and people working in this repository (tool-neutral).

A small, read-only Python harness for the MemberSuite association management system's REST API:
sign in, run MSQL searches, export to CSV, profile the results, and run a light audit (feature
usage, customizations, integrations, member count). It is for an outside consultant working for
an incoming CEO. It is not a sync tool and never writes to MemberSuite.

## Finding things

| You want | Go to |
|---|---|
| What it does and how to use it | `README.md` |
| All documentation by topic | `docs/README.md` |
| The audit plan and open questions | `docs/audit-plan.md` |
| Current state and next step (local, git-ignored) | `local-data/SESSION.md` |

## Build and test

```sh
tools/check.sh                        # the whole local gate (ruff, format, pytest); run before finishing
uv run msuite --help                  # the CLI
uv run python tools/build_catalog.py  # after refreshing docs/api-spec/*.json
```

## Rules that must hold

- **Read-only.** The client only sends GET requests and the search POST
  (`/platform/v2/search/executeSearch`) plus sign-in. Never add POST/PUT/DELETE/PATCH calls.
- **Credentials** come only from the environment or `.env` (git-ignored). Never log, print or
  write the password or the token.
- **Member data stays in `local-data/`** (git-ignored). Console output is counts, object names
  and value shapes, never rows.
- Tests use `httpx.MockTransport`; they never call the live API.
- Every bug fixed gets a regression test.
- Docs change in the same commit as the behavior they describe (`docs/README.md` lists what to check).

## Where things are

```
src/msuite/   config.py (settings), client.py (HTTP + paging), catalog.py/.json (object -> module),
              export.py (CSV, profile), audit.py (inventory, config dump, member count), cli.py
tests/        unit tests with a fake API
tools/        check.sh, build_catalog.py
docs/         audit plan, API notes, credentials; api-spec/ holds the saved Swagger specs
local-data/   git-ignored: exports, audit output, SESSION.md
```
