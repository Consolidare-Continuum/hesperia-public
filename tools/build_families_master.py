#!/usr/bin/env python3
# HESPERIA — Build families_master.txt from tfp_families.txt (LEVEL 2 T2.1).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Parse source tfp_families.txt (Area N — ... sections, one family name per block).
Output families_master.txt: area_id, family_id, family_name, family_definition.
Canonical order: A1..A10 (area_index 0..9), family_001..family_240.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Area number in file → area_id (canonical order 0..9)
AREA_NUM_TO_ID = {
    1: "A1",
    2: "A2",
    3: "A3",
    4: "A4",
    5: "A5",
    6: "A6",
    7: "A7",
    8: "A8",
    9: "A9",
    10: "A10",
}


def parse_tfp_families(path: Path) -> dict[str, list[str]]:
    """Parse file; return dict area_id -> list of family names (in file order)."""
    text = path.read_text(encoding="utf-8")
    # Split by "Area N —" and collect non-empty lines in each block
    blocks = re.split(r"\nArea (\d+)\s*[—\-]", text, flags=re.IGNORECASE)
    by_area: dict[int, list[str]] = {}
    for i, block in enumerate(blocks):
        if i == 0:
            # Before first Area: may have header; skip
            continue
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        area_num = int(lines[0].split()[0]) if lines[0][0].isdigit() else None
        # Actually blocks after split: first line of block might be "1 — Влечения..." so area number is in the first line
        # Re-check split: "Area 1 —" gives blocks; first block is preamble, second block starts with "Влечения..." and we lost the number
        # So we need to capture area number from the regex. Use finditer or split with capture.
    # Simpler: find all "Area N —" and then take lines until next "Area" or end
    by_area = {}
    current_area: int | None = None
    current_list: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^Area\s+(\d+)\s*[—\-]", line.strip(), re.IGNORECASE)
        if m:
            if current_area is not None and current_list:
                aid = AREA_NUM_TO_ID[current_area]
                by_area[aid] = current_list
            current_area = int(m.group(1))
            current_list = []
            continue
        stripped = line.strip()
        if stripped and current_area is not None and not re.match(r"^[IVXIV]+\.\s", stripped):
            current_list.append(stripped)
    if current_area is not None and current_list:
        aid = AREA_NUM_TO_ID[current_area]
        by_area[aid] = current_list
    return by_area


def build_canonical_order(by_area: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    """Return list of (area_id, family_name) in order A1..A10, then by name order within area."""
    out: list[tuple[str, str, str]] = []
    for area_id in ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10"]:
        names = by_area.get(area_id, [])
        for name in names:
            out.append((area_id, name, name))  # definition = name as placeholder
    return out


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/igareosh/tfp_families.txt")
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / "spec" / "families_master.txt"
    if not src.exists():
        print(f"Source not found: {src}", file=sys.stderr)
        sys.exit(1)
    by_area = parse_tfp_families(src)
    ordered = build_canonical_order(by_area)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for idx, (area_id, family_name, family_definition) in enumerate(ordered, start=1):
            family_id = f"family_{idx:03d}"
            f.write(f"area_id\t{area_id}\n")
            f.write(f"family_id\t{family_id}\n")
            f.write(f"family_name\t{family_name}\n")
            f.write(f"family_definition\t{family_definition}\n")
            f.write("\n")
    print(f"Wrote {len(ordered)} families to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
