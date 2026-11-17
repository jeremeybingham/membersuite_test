# membersuite_test

A small Python harness for pulling data out of a MemberSuite association management system through
its REST API, for a light audit: which features staff use, what has been customized or integrated,
and how many members there really are.

It reads only. Every command runs searches and GETs; nothing creates, updates or deletes records.

## Setup

```sh
uv sync
cp .env.example .env      # fill in tenant id and username; leave the password empty to be prompted
uv run msuite ping        # signs in and reads one page of Individual IDs
```

See [`docs/credentials.md`](docs/credentials.md) for how credentials are handled and what kind of
MemberSuite user to ask for.

## Commands

| Command | What it does | Output |
|---|---|---|
| `msuite entities [--module crm]` | Lists the 299 objects in the API and their MSQL type names (offline) | screen |
| `msuite ping` | Checks sign-in and shows the shape of one search page | screen |
| `msuite describe memberships` | Field metadata for an object, **including custom fields** | `local-data/describe/` |
| `msuite query "SELECT ID, Name FROM Committee"` | Any MSQL statement, all pages | `local-data/queries/` CSV |
| `msuite export individuals --fields "ID, FirstName, LastName, EmailAddress"` | One object to CSV | `local-data/exports/` |
| `msuite profile FILE.csv` | Fill rate, distinct count and value shape per column (offline) | screen |
| `msuite inventory [--module crm]` | **Audit:** record count and newest created/modified date for every object | `local-data/audit/` |
| `msuite config` | **Audit:** dumps custom fields, saved searches, templates, payment and shipping integrations, membership setup | `local-data/audit/config/` |
| `msuite members` | **Audit:** member counts under several definitions, side by side | `local-data/audit/` |

Output folders are dated (`local-data/<kind>/YYYY-MM-DD/`). `local-data/` is git-ignored: it holds
member data and never leaves this machine.

For analysis beyond `profile`, query the CSVs with DuckDB:

```sh
duckdb -c "SELECT status, count(*) FROM 'local-data/exports/2026-11-17/memberships.csv' GROUP BY 1"
```

## The audit

The plan, the order to run things in and the questions it should answer are in
[`docs/audit-plan.md`](docs/audit-plan.md). What we learned about the API is in
[`docs/api-notes.md`](docs/api-notes.md).

## Development

```sh
tools/check.sh                       # ruff + tests
uv run python tools/build_catalog.py # rebuild src/msuite/catalog.json after refreshing docs/api-spec/
```
