"""`msuite` command line. Run `uv run msuite --help`."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import audit
from .catalog import entities, lookup
from .client import ApiError, Client
from .config import DATA_DIR, ConfigError, load_settings
from .export import profile, write_csv


def out_path(kind: str, name: str) -> Path:
    return DATA_DIR / kind / date.today().isoformat() / name


def print_table(rows: list[dict]) -> None:
    if not rows:
        print("(no rows)")
        return
    cols = list(rows[0])
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


def client_from_env(args) -> Client:
    return Client(load_settings(), page_size=args.page_size)


def cmd_entities(args) -> None:
    rows = [
        {"module": e.module, "entity": e.entity, "msql_type": e.type}
        for e in entities().values()
        if not args.module or e.module == args.module
    ]
    print_table(rows)


def cmd_ping(args) -> None:
    with client_from_env(args) as c:
        info = c.association_info()
        print("association info keys:", sorted(info) if isinstance(info, dict) else type(info))
        c.sign_in()
        print("sign-in: ok")
        rows = c.search_page("SELECT ID FROM Individual", 0, "individuals")
        print(f"first page of Individual IDs: {len(rows)} rows (page size {c.page_size})")
        if rows:
            print("row keys:", sorted(rows[0]))


def cmd_describe(args) -> None:
    e = lookup(args.entity)
    with client_from_env(args) as c:
        meta = c.describe(e)
    path = Path(args.out) if args.out else out_path("describe", f"{e.entity}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=1))
    print(f"wrote {path}")


def cmd_query(args) -> None:
    with client_from_env(args) as c:
        rows = list(c.search(args.msql, args.entity, max_rows=args.max))
    path = Path(args.out) if args.out else out_path("queries", "query.csv")
    n = write_csv(rows, path)
    print(f"{n} rows -> {path}")


def cmd_export(args) -> None:
    e = lookup(args.entity)
    msql = f"SELECT {args.fields} FROM {e.type}" + (f" WHERE {args.where}" if args.where else "")
    with client_from_env(args) as c:
        rows = list(c.search(msql, e, max_rows=args.max))
    path = Path(args.out) if args.out else out_path("exports", f"{e.entity}.csv")
    n = write_csv(rows, path)
    print(f"{n} rows -> {path}")


def cmd_profile(args) -> None:
    print_table(profile(Path(args.csv)))


def cmd_inventory(args) -> None:
    modules = args.module or None
    with client_from_env(args) as c:
        rows = audit.inventory(c, modules, cap=args.cap)
    path = out_path("audit", "inventory.csv")
    write_csv(rows, path)
    used = [r for r in rows if r["count"] not in ("", 0)]
    print(f"{len(used)} of {len(rows)} objects have records; full table -> {path}")


def cmd_config(args) -> None:
    out_dir = out_path("audit", "config")
    with client_from_env(args) as c:
        summary = audit.config_dump(c, out_dir)
    print_table(summary)
    print(f"records -> {out_dir}")


def cmd_members(args) -> None:
    fields = ", ".join(audit.MEMBERSHIP_FIELDS)
    with client_from_env(args) as c:
        rows = list(c.search(f"SELECT {fields} FROM Membership", "memberships"))
    write_csv(rows, out_path("exports", "memberships.csv"))
    summary = audit.member_summary(rows)
    path = out_path("audit", "member_count.json")
    path.write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    print(f"-> {path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="msuite", description="MemberSuite API harness")
    p.add_argument("--page-size", type=int, default=500, help="rows per API page (default 500)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("entities", help="list the objects the API exposes (offline)")
    s.add_argument("--module")
    s.set_defaults(func=cmd_entities)

    s = sub.add_parser("ping", help="check credentials: sign in and read one page")
    s.set_defaults(func=cmd_ping)

    s = sub.add_parser("describe", help="save an object's field metadata, incl. custom fields")
    s.add_argument("entity")
    s.add_argument("--out")
    s.set_defaults(func=cmd_describe)

    s = sub.add_parser("query", help="run an MSQL statement, save all pages to CSV")
    s.add_argument("msql")
    s.add_argument("--entity", help="use this entity's module endpoint (default: platform search)")
    s.add_argument("--max", type=int)
    s.add_argument("--out")
    s.set_defaults(func=cmd_query)

    s = sub.add_parser("export", help="export one object's fields to CSV")
    s.add_argument("entity")
    s.add_argument("--fields", default="ID, Name", help='MSQL field list (default "ID, Name")')
    s.add_argument("--where")
    s.add_argument("--max", type=int)
    s.add_argument("--out")
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("profile", help="fill rate and shape per column of a CSV (offline)")
    s.add_argument("csv")
    s.set_defaults(func=cmd_profile)

    s = sub.add_parser("inventory", help="audit: record counts and last activity per object")
    s.add_argument("--module", action="append", help="limit to a module (repeatable)")
    s.add_argument("--cap", type=int, default=50_000, help="stop counting at N (default 50000)")
    s.set_defaults(func=cmd_inventory)

    s = sub.add_parser("config", help="audit: dump custom fields, searches, integrations, setup")
    s.set_defaults(func=cmd_config)

    s = sub.add_parser("members", help="audit: member counts under several definitions")
    s.set_defaults(func=cmd_members)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (ConfigError, ApiError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
