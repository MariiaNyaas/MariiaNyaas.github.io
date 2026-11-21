#!/usr/bin/env python3
"""Static and logic-level pre-publication audit for the 22 November release.

Browser interaction is deliberately recorded separately after the exact GitHub
Pages commit is deployed.  This script does not pretend that source inspection
is a rendered-browser test.
"""
from __future__ import annotations

import json
import math
import pathlib
import subprocess
from html.parser import HTMLParser
from urllib.parse import urlparse
from result_store import load_results

HERE = pathlib.Path(__file__).resolve().parent
RELEASE = HERE.parent
ROOT = RELEASE.parents[1]
SLUGS = [
    "01-credit-risk", "02-financial", "03-accounting",
    "04-governance", "05-business", "06-public-finance",
    "07-art-capital",
]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.config = ""
        self._in_config = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag in {"a", "link", "script"}:
            ref = a.get("href") or a.get("src")
            if ref:
                self.links.append(ref)
        if tag == "script" and a.get("id") == "config":
            self._in_config = True

    def handle_endtag(self, tag):
        if tag == "script" and self._in_config:
            self._in_config = False

    def handle_data(self, data):
        if self._in_config:
            self.config += data


checks: list[dict] = []


def add(name: str, ok: bool | None, detail=""):
    status = "PASS" if ok is True else "FAIL" if ok is False else "NOT VERIFIED"
    checks.append({"name": name, "status": status, "detail": str(detail)})


def finite_tree(value):
    if isinstance(value, dict):
        return all(finite_tree(v) for v in value.values())
    if isinstance(value, list):
        return all(finite_tree(v) for v in value)
    if isinstance(value, float):
        return math.isfinite(value)
    return True


results = load_results(HERE)
studies = json.loads((HERE / "studies.json").read_text())
manifest = json.loads((HERE / "extraction_manifest.json").read_text())
calc = json.loads((HERE / "calculation_audit.json").read_text())
app = (HERE / "app.js").read_text()
css = (HERE / "app.css").read_text()

add("Exactly seven study specifications", len(studies) == 7, len(studies))
add("Exactly seven result blocks", len(results.get("studies", {})) == 7, len(results.get("studies", {})))
add("All numeric research results are finite", finite_tree(results))
add("Calculation audit has no failures", calc.get("fail") == 0, f"{calc.get('pass')} PASS / {calc.get('fail')} FAIL")
manifest_files = manifest if isinstance(manifest, list) else manifest.get("files", [])
add("Source manifest is populated", len(manifest_files) > 0, f"{len(manifest_files)} retained files")

node = subprocess.run(["node", "--check", str(HERE / "app.js")], capture_output=True, text=True)
add("JavaScript parses under Node", node.returncode == 0, (node.stderr or "syntax OK").strip())
for token in ("#0E1929", "#CEB382", "#F4F1EB", "#ACB8C6"):
    add(f"Design token {token}", token.lower() in css.lower())
add("Responsive CSS breakpoint exists", "@media" in css, "responsive layout rule retained")
add("No literal NaN placeholder in app", "NaN" not in app)
add("No literal undefined placeholder in app", "undefined" not in app)

required_ids = {
    "choice", "evidence-note", "chart", "chart2", "table", "csv",
    "playground", "lab-note", "result", "scenario-chart", "reset", "export",
}
all_internal = []
for slug in SLUGS:
    page = RELEASE / slug / "index.html"
    method = RELEASE / slug / "methodology.html"
    parser = PageParser(); parser.feed(page.read_text())
    config = json.loads(parser.config)
    add(f"{slug}: page and methodology exist", page.exists() and method.exists())
    add(f"{slug}: required interactive regions", required_ids <= parser.ids, sorted(required_ids - parser.ids))
    input_ids = {x["id"] for x in config["inputs"]}
    add(f"{slug}: every configured input is rendered", input_ids <= parser.ids, sorted(input_ids - parser.ids))
    bounded = all(x["min"] <= x["value"] <= x["max"] and x["step"] > 0 for x in config["inputs"])
    add(f"{slug}: input defaults and bounds are valid", bounded)
    used = all(app.count(f"v.{input_id}") >= 1 for input_id in input_ids)
    add(f"{slug}: every input enters scenario formula", used, ", ".join(sorted(input_ids)))
    add(f"{slug}: source URL is HTTPS", urlparse(config["source"]).scheme == "https", config["source"])
    add(f"{slug}: methodology is separate", 'href="methodology.html"' in page.read_text())
    for ref in parser.links:
        if ref.startswith(("http://", "https://", "#", "data:", "mailto:")) or ref == "/":
            continue
        all_internal.append((page, ref))

broken = []
for page, ref in all_internal:
    target = (page.parent / ref.split("#", 1)[0].split("?", 1)[0]).resolve()
    if ref.startswith("/"):
        target = ROOT / ref.lstrip("/")
    if ref.endswith("/"):
        target = target / "index.html"
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        broken.append(f"{page.relative_to(ROOT)} -> {ref}")
add("All internal release links resolve", not broken, "0 broken" if not broken else " | ".join(broken))

for label, needle in {
    "Evidence selector event": "addEventListener('change',renderEvidence)",
    "Scenario input event": "addEventListener('input',renderScenario)",
    "Reset handler": "addEventListener('click',reset)",
    "Scenario JSON export": "scenario.json",
    "Evidence CSV export": "evidence.csv",
    "Ready-state marker": "dataset.ready='true'",
}.items():
    add(label, needle in app)

browser_path = HERE / "browser_audit.json"
if browser_path.exists():
    browser = json.loads(browser_path.read_text())
    add("Exact-commit GitHub Actions deployment", browser["deployment"]["conclusion"] == "success", browser["deployment"]["url"])
    for row in browser["dashboards"]:
        ok = all([
            row["ready"], row["charts"] == 3, row["disabled_controls"] == 0,
            row["scenario_changes"], row["reset_roundtrip"],
            row["selector_changes_visible_output"], row["scenario_export"],
            row["csv_export"],
        ])
        add(f"{row['slug']}: public browser interactions", ok, "3 charts; input, reset, selector, JSON and CSV exports")
    add("Latest Research contains all seven", browser["catalogs"]["latest_research_all_seven"])
    add("All seven thematic catalogs contain the new study", browser["catalogs"]["seven_thematic_catalogs"])
else:
    add("Rendered public-browser interaction", None, "NOT VERIFIED; browser_audit.json absent")
add("Physical mobile-device test", None, "NOT VERIFIED; responsive browser viewport test is separate")
add("External human peer review", None, "NOT VERIFIED; automated same-session audit only")

fail = sum(c["status"] == "FAIL" for c in checks)
payload = {
    "status": "FAIL" if fail else "PASS",
    "pass": sum(c["status"] == "PASS" for c in checks),
    "fail": fail,
    "not_verified": sum(c["status"] == "NOT VERIFIED" for c in checks),
    "checks": checks,
}
(HERE / "technical_audit.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({k: payload[k] for k in ("status", "pass", "fail", "not_verified")}, indent=2, ensure_ascii=False))
raise SystemExit(1 if fail else 0)
