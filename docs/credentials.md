# Credentials

## What to ask the organization for

- **A dedicated MemberSuite staff user for this engagement**, not a shared or personal login, so
  its activity is easy to tell apart in audit fields and easy to switch off afterwards.
- **Read-only rights** across the modules (a security role that can view but not edit). The
  harness never writes, but a read-only role makes that a guarantee rather than a promise.
- **The numeric association (tenant) id.** Staff or MemberSuite support can give it.
- An end date: disable the user when the engagement ends.

## How the harness handles them

- Values come from environment variables, normally a `.env` file in the repo root (git-ignored;
  `.env.example` is the committed template): `MS_TENANT_ID`, `MS_USERNAME`, `MS_PASSWORD`,
  `MS_BASE_URL`.
- **Leave `MS_PASSWORD` empty** to be asked for it at each run (`getpass`); then the password is
  never stored on disk. Fill it in only on a machine you control.
- The access token lives in memory for one run and is never written out. When it expires the
  client signs in again.
- `Settings` hides the username and password in its `repr`, so they do not show in tracebacks.
- Never paste credentials into chat, email, issues or commits. Share them through a password
  manager.

## If this grows

For a longer engagement or a scheduled job, move the password into the OS keyring or a password
manager CLI (`op read ...`) and export it into the environment just for the run. Not needed now.
