#!/usr/bin/env python3
"""Package the current decision dashboard, observed data and research evidence.

Original raw provider caches are deliberately excluded. Their exact retrieval
URLs and hashes remain in the source manifests. See README for source refresh.
"""
from pathlib import Path
import hashlib
import json
import zipfile

MODEL = Path(__file__).resolve().parents[1]
PAGE = MODEL.parent
SITE = "https://mariianyaas.github.io/daily-intelligence/2026-11-22/02-financial/"
files = [PAGE / name for name in ("index.html", "dashboard.css", "decision-app.js", "decision-engine.js", "decision-data.json", "methodology.html", "project.json")]
files += [p for p in MODEL.rglob("*") if p.is_file() and "raw" not in p.relative_to(MODEL).parts
          and "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name not in (".gitignore", "release_manifest.json")]
manifest = {"version": "3.0", "release_date": "2026-11-24", "entry": "index.html",
            "raw_cache_included": False, "files": []}
for p in sorted(files):
    manifest["files"].append({"path": str(p.relative_to(PAGE)), "bytes": p.stat().st_size,
                              "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
(MODEL / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
files += [MODEL / "release_manifest.json"]
dest = PAGE / "currency-risk-decisions.zip"
with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for p in sorted(files):
        content = p.read_bytes()
        archive.writestr(str(p.relative_to(PAGE)), content)
print(f"Packaged {len(files)} files in {dest} ({dest.stat().st_size:,} bytes)")
