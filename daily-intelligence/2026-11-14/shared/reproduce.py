"""Verify retained source bytes, rerun analysis and independent audit."""
import hashlib,json,pathlib,subprocess,sys
O=pathlib.Path(__file__).parent; S=O/'sources'
manifest=json.loads((O/'source_manifest.json').read_text())
for r in manifest:
 p=S/r['file']
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:
  raise SystemExit('SOURCE CHECK FAILED: '+r['file'])
subprocess.run([sys.executable,str(O/'analyze.py'),str(S)],check=True)
subprocess.run([sys.executable,str(O/'audit_research.py'),str(S)],check=True)
print('REPRODUCTION PASS')
