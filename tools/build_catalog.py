"""Build src/msuite/catalog.json from the saved Swagger specs in docs/api-spec/.

Each entry maps an entity's URL segment (e.g. "individuals") to its module ("crm"), API version
("v1") and MSQL object type ("Individual"). Re-run after refreshing the specs:

    uv run python tools/build_catalog.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = ROOT / "docs" / "api-spec"
OUT = ROOT / "src" / "msuite" / "catalog.json"

PATH_RE = re.compile(r"^/(?P<module>[a-z]+)/(?P<version>v\d+)/(?P<entity>[A-Za-z]+)/\{id\}$")


def build(spec_dir: Path = SPEC_DIR) -> list[dict]:
    entries = {}
    for spec_file in sorted(spec_dir.glob("*.json")):
        spec = json.loads(spec_file.read_text())
        paths = spec.get("paths", {})
        for path, ops in paths.items():
            m = PATH_RE.match(path)
            if not m or "get" not in ops:
                continue
            module, version, entity = m["module"], m["version"], m["entity"]
            # Only entities that have the standard MSQL search and description endpoints.
            search = f"/{module}/{version}/{entity}/{{tenantId}}"
            describe = f"/{module}/{version}/{entity}/description/{{tenantid}}"
            if search not in paths or describe not in paths:
                continue
            ref = ops["get"].get("responses", {}).get("200", {}).get("schema", {}).get("$ref", "")
            type_name = ref.rsplit("/", 1)[-1] if ref else ""
            entries[entity] = {
                "entity": entity,
                "module": module,
                "version": version,
                "type": type_name,
                "summary": ops["get"].get("tags", [""])[0],
            }
    return sorted(entries.values(), key=lambda e: (e["module"], e["entity"]))


def main() -> int:
    catalog = build()
    OUT.write_text(json.dumps(catalog, indent=1) + "\n")
    print(f"wrote {len(catalog)} entities to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
