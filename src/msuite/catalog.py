"""Which module serves which entity, built from the saved Swagger specs (tools/build_catalog.py)."""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

CATALOG_FILE = Path(__file__).with_name("catalog.json")


@dataclass(frozen=True)
class Entity:
    entity: str  # URL segment, e.g. "individuals"
    module: str  # e.g. "crm"
    version: str  # e.g. "v1"
    type: str  # MSQL object type, e.g. "Individual"
    summary: str = ""

    @property
    def search_path(self) -> str:
        return f"/{self.module}/{self.version}/{self.entity}/{{tenant}}"

    @property
    def describe_path(self) -> str:
        return f"/{self.module}/{self.version}/{self.entity}/description/{{tenant}}"


@cache
def entities() -> dict[str, Entity]:
    rows = json.loads(CATALOG_FILE.read_text())
    return {r["entity"].lower(): Entity(**r) for r in rows}


def lookup(name: str) -> Entity:
    """Find an entity by URL segment ("memberships") or MSQL type ("Membership"), any case."""
    key = name.lower()
    table = entities()
    if key in table:
        return table[key]
    for e in table.values():
        if e.type.lower() == key:
            return e
    raise KeyError(f"unknown entity {name!r}; run `msuite entities` to list them")
