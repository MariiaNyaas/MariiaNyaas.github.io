#!/usr/bin/env python3
"""Package the complete v2 dashboard, normalized evidence and reproducible code.

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
files = [PAGE / name for name in ("dashboard.html", "dashboard.css", "dashboard.js", "methodology-v2.html")]
files += [p for p in MODEL.rglob("*") if p.is_file() and "raw" not in p.relative_to(MODEL).parts
          and "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name not in (".gitignore", "release_manifest.json")]
manifest = {"version": "2.0", "release_date": "2026-11-24", "entry": "dashboard.html",
            "raw_cache_included": False, "files": []}
for p in sorted(files):
    manifest["files"].append({"path": str(p.relative_to(PAGE)), "bytes": p.stat().st_size,
                              "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
(MODEL / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
files += [MODEL / "release_manifest.json"]
dest = PAGE / "eur_nok_research_v2.zip"
with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for p in sorted(files):
        content = p.read_bytes()
        if p.name == "dashboard.html":
            text = content.decode().replace('href="original.html"', f'href="{SITE}original.html"')
            text = text.replace('href="/"', 'href="https://mariianyaas.github.io/"')
            content = text.encode()
        archive.writestr(str(p.relative_to(PAGE)), content)
    archive.writestr("index.html", '<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=dashboard.html"><title>EUR/NOK Research Lab</title><a href="dashboard.html">Open the research dashboard</a></html>')
print(f"Packaged {len(files)} files in {dest} ({dest.stat().st_size:,} bytes)")
