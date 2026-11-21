#!/usr/bin/env python3
"""Read the browser-safe, sharded result store as one analysis object."""
from __future__ import annotations

import json
import pathlib


def load_results(shared_dir: pathlib.Path) -> dict:
    shared_dir = pathlib.Path(shared_dir)
    manifest = json.loads((shared_dir / "results.json").read_text())
    studies = {}
    for kind, spec in manifest["studies"].items():
        if "file" in spec:
            studies[kind] = json.loads((shared_dir / spec["file"]).read_text())
            continue
        meta = json.loads((shared_dir / spec["meta"]).read_text())
        rows = []
        for part in spec["row_parts"]:
            rows.extend(json.loads((shared_dir / part).read_text()))
        meta["rows"] = rows
        studies[kind] = meta
    return {
        "status": manifest["status"], "release": manifest["release"],
        "cutoff": manifest["cutoff"], "studies": studies,
    }
