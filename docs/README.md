# Documentation

## Pages by topic

| Topic | Page |
|---|---|
| The audit: phases, commands, open questions | [`audit-plan.md`](audit-plan.md) |
| What we know about the API, and what is unverified | [`api-notes.md`](api-notes.md) |
| Credentials: what to ask for, how they are handled | [`credentials.md`](credentials.md) |
| Saved Swagger specs (one per module) | [`api-spec/`](api-spec/) |

## When you change something, check these

| You change | Check |
|---|---|
| A CLI command, flag or output | README; `audit-plan.md` if the audit uses it; `AGENTS.md` |
| Something learned from the live API | `api-notes.md` (move it out of "unverified"); a test |
| The specs in `api-spec/` | rerun `tools/build_catalog.py`; `api-notes.md` |
| Credential handling | `credentials.md`; `.env.example`; README |
| Build commands, layout | `AGENTS.md`; `CLAUDE.md`; this index |
| A page added, renamed or removed | this index |
