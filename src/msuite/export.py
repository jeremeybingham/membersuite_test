"""Write rows to CSV, and profile a CSV by column (counts and shapes only, never values)."""

import csv
import json
import re
from collections.abc import Iterable
from pathlib import Path


def flatten(row: dict, prefix: str = "") -> dict:
    """Flatten nested objects to dotted keys; lists become JSON strings."""
    out = {}
    for key, value in row.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, f"{name}."))
        elif isinstance(value, list):
            out[name] = json.dumps(value, default=str)
        else:
            out[name] = value
    return out


def write_csv(rows: Iterable[dict], path: Path) -> int:
    """Write rows to `path`, with the union of all keys as columns. Returns the row count."""
    flat = [flatten(r) for r in rows]
    columns: list[str] = []
    seen = set()
    for r in flat:
        for k in r:
            if k not in seen:
                seen.add(k)
                columns.append(k)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(flat)
    return len(flat)


def shape(value: str) -> str:
    """Letters to a, digits to 9, so a value's form shows without the value."""
    return re.sub(r"[0-9]", "9", re.sub(r"[A-Za-z]", "a", value))[:30]


def profile(path: Path) -> list[dict]:
    """Per column: rows, filled, fill %, distinct values, the most common value shape."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        filled = dict.fromkeys(columns, 0)
        distinct: dict[str, set] = {c: set() for c in columns}
        shapes: dict[str, dict[str, int]] = {c: {} for c in columns}
        total = 0
        for row in reader:
            total += 1
            for c in columns:
                v = (row.get(c) or "").strip()
                if v:
                    filled[c] += 1
                    if len(distinct[c]) <= 10_000:
                        distinct[c].add(v)
                    s = shape(v)
                    shapes[c][s] = shapes[c].get(s, 0) + 1
    out = []
    for c in columns:
        top = max(shapes[c].items(), key=lambda kv: kv[1])[0] if shapes[c] else ""
        out.append(
            {
                "column": c,
                "rows": total,
                "filled": filled[c],
                "fill_pct": round(100 * filled[c] / total, 1) if total else 0.0,
                "distinct": len(distinct[c]) if len(distinct[c]) <= 10_000 else ">10000",
                "top_shape": top,
            }
        )
    return out
