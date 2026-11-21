#!/usr/bin/env python3
"""Re-run the analysis from a local source directory and compare the output."""
from __future__ import annotations
import json,pathlib,subprocess,sys,tempfile
from result_store import load_results

HERE=pathlib.Path(__file__).resolve().parent
source=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else HERE/'raw'
if not source.exists():
 raise SystemExit('Source directory missing. Run collect_sources.py in a writable workspace or pass its output directory.')
with tempfile.TemporaryDirectory() as temp:
 out=pathlib.Path(temp)
 subprocess.run([sys.executable,str(HERE/'analyze.py'),str(source),str(out)],check=True)
 expected=load_results(HERE);actual=json.loads((out/'results.json').read_text())
 if expected!=actual: raise SystemExit('Reproduction mismatch')
 print('PASS: results.json reproduced byte-for-byte at the JSON object level.')
