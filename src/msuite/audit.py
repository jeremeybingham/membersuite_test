"""The light system audit: what is used, what is customized, how many members there are.

All output goes under local-data/ (git-ignored). Console output is counts and object names only.
"""

import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from .catalog import Entity, entities, lookup
from .client import ApiError, Client
from .export import write_csv


def progress(step: int, total: int, label: str) -> None:
    print(f"##progress step={step}/{total} label={label}", flush=True, file=sys.stderr)


def get_ci(row: dict, name: str):
    """Case-insensitive field lookup: responses may use camelCase or PascalCase."""
    key = name.lower()
    for k, v in row.items():
        if k.lower() == key:
            return v
    return None


# --- 1. Feature usage inventory -------------------------------------------------------------


def latest(client: Client, e: Entity, field: str) -> str:
    msql = f"SELECT ID, {field} FROM {e.type} ORDER BY {field} DESC"
    rows = client.search_page(msql, 0, e)
    return str(get_ci(rows[0], field) or "") if rows else ""


def inventory(client: Client, modules: list[str] | None, cap: int | None) -> list[dict]:
    """Per entity: record count, newest CreatedDate and LastModifiedDate, or the error."""
    todo = [e for e in entities().values() if not modules or e.module in modules]
    out = []
    for i, e in enumerate(todo, 1):
        progress(i, len(todo), f"{e.module}/{e.entity}")
        row = {"module": e.module, "entity": e.entity, "type": e.type}
        try:
            n = client.count(e, cap=cap)
            row["count"] = f">={n}" if cap and n >= cap else n
            row["latest_created"] = latest(client, e, "CreatedDate") if n else ""
            row["latest_modified"] = latest(client, e, "LastModifiedDate") if n else ""
            row["error"] = ""
        except (ApiError, ValueError) as exc:
            row.update(count="", latest_created="", latest_modified="", error=str(exc)[:120])
        out.append(row)
    return out


# --- 2. Configuration, customizations and integrations --------------------------------------

# Objects that describe how the system was set up, rather than member activity.
CONFIG_ENTITIES = [
    # Custom fields, objects and screens
    "customfields",
    "customobjects",
    "customfieldconfigurationsettings",
    "portalformconfigurationsettings",
    "lookuptables",
    # Reporting and searches staff built
    "savedsearches",
    "scheduledsearches",
    "customsearchspecifications",
    "searchresultswidgets",
    # Communications
    "emailtemplatecontainers",
    "mailmergetemplates",
    # Payment and shipping integrations
    "authorizenetmerchantaccounts",
    "bluepaymerchantaccounts",
    "paypalmerchantaccounts",
    "payflowpromerchantaccounts",
    "prioritypaymentsmerchantaccounts",
    "fedexshippingcarrieraccounts",
    "upsshippingcarrieraccounts",
    "uspsshippingcarrieraccounts",
    # Membership structure
    "membershiptypes",
    "membershipstatuses",
    "membershiporganizations",
    "chapters",
    "sections",
    "organizationallayers",
]


def config_dump(client: Client, out_dir: Path) -> list[dict]:
    """Save every record of each configuration object as JSON and CSV; return counts."""
    summary = []
    for i, name in enumerate(CONFIG_ENTITIES, 1):
        e = lookup(name)
        progress(i, len(CONFIG_ENTITIES), name)
        try:
            ids = [get_ci(r, "ID") for r in client.search(f"SELECT ID FROM {e.type}", e)]
            records = [client.get(e, rid) for rid in ids]
            (out_dir / "json").mkdir(parents=True, exist_ok=True)
            (out_dir / "json" / f"{name}.json").write_text(json.dumps(records, indent=1))
            write_csv(records, out_dir / f"{name}.csv")
            summary.append({"entity": name, "count": len(records), "error": ""})
        except (ApiError, ValueError) as exc:
            summary.append({"entity": name, "count": "", "error": str(exc)[:120]})
    return summary


# --- 3. Member count ------------------------------------------------------------------------

MEMBERSHIP_FIELDS = [
    "ID",
    "Owner",
    "MembershipOrganization",
    "Type",
    "Status",
    "ReceivesMemberBenefits",
    "JoinDate",
    "ExpirationDate",
    "TerminationDate",
]


def parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def label(value) -> str:
    """A reference field may come back as an id, a name, or an object with a name."""
    if isinstance(value, dict):
        return str(get_ci(value, "name") or get_ci(value, "id") or "")
    return "" if value is None else str(value)


def member_summary(rows: list[dict], today: date | None = None) -> dict:
    """Several honest answers to 'how many members?', side by side.

    The CEO's number depends on the definition; the gaps between these lines are the finding.
    """
    today = today or date.today()

    def current(r):
        exp = parse_date(get_ci(r, "ExpirationDate"))
        term = parse_date(get_ci(r, "TerminationDate"))
        return (exp is None or exp >= today) and (term is None or term > today)

    benefits = [r for r in rows if str(get_ci(r, "ReceivesMemberBenefits")).lower() == "true"]
    unexpired = [r for r in rows if current(r)]
    both = [r for r in benefits if current(r)]
    return {
        "as_of": today.isoformat(),
        "membership_records": len(rows),
        "distinct_owners_all": len({label(get_ci(r, "Owner")) for r in rows}),
        "receives_member_benefits": len(benefits),
        "unexpired_and_not_terminated": len(unexpired),
        "benefits_and_unexpired": len(both),
        "distinct_owners_benefits_and_unexpired": len({label(get_ci(r, "Owner")) for r in both}),
        "by_status": dict(Counter(label(get_ci(r, "Status")) for r in rows).most_common()),
        "by_type": dict(Counter(label(get_ci(r, "Type")) for r in rows).most_common()),
        "by_membership_organization": dict(
            Counter(label(get_ci(r, "MembershipOrganization")) for r in rows).most_common()
        ),
        "benefits_by_status": dict(Counter(label(get_ci(r, "Status")) for r in benefits)),
        "expiring_by_year": dict(
            sorted(
                Counter(
                    str(d.year) if (d := parse_date(get_ci(r, "ExpirationDate"))) else "none"
                    for r in rows
                ).items()
            )
        ),
    }
