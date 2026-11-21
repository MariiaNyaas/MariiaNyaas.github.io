#!/usr/bin/env python3
"""Split a full analysis result into GitHub Pages/browser-safe shards."""
from __future__ import annotations

import json
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
shared = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else source.parent
payload = json.loads(source.read_text())
target = shared / "results"
target.mkdir(exist_ok=True)
manifest = {
    "status": payload["status"], "release": payload["release"],
    "cutoff": payload["cutoff"], "format": "sharded-v1", "studies": {}
}

for kind, study in payload["studies"].items():
    if kind != "governance":
        path = target / f"{kind}.json"
        path.write_text(json.dumps(study, separators=(",", ":"), ensure_ascii=False) + "\n")
        manifest["studies"][kind] = {"file": f"results/{path.name}"}
        continue
    meta = dict(study)
    rows = meta.pop("rows")
    meta_path = target / "governance-meta.json"
    meta_path.write_text(json.dumps(meta, separators=(",", ":"), ensure_ascii=False) + "\n")
    parts = []
    for i in range(0, len(rows), 1500):
        part = target / f"governance-rows-{i // 1500 + 1:02d}.json"
        part.write_text(json.dumps(rows[i:i + 1500], separators=(",", ":"), ensure_ascii=False) + "\n")
        parts.append(f"results/{part.name}")
    manifest["studies"][kind] = {"meta": "results/governance-meta.json", "row_parts": parts}

(shared / "results.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"studies": len(manifest["studies"]), "governance_parts": len(parts)}))
