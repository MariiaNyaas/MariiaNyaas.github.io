"""python reproduce.py; installs nothing. Requires numpy,pandas,scipy,openpyxl."""
import pathlib,gzip,json,hashlib,subprocess,sys,tempfile
p=pathlib.Path(__file__).parent
with tempfile.TemporaryDirectory() as tmp:
 for item in json.loads((p/'source_manifest.json').read_text()):
  raw=gzip.decompress((p/'sources'/item['download']).read_bytes())
  assert hashlib.sha256(raw).hexdigest()==item['sha256']
  (pathlib.Path(tmp)/item['file']).write_bytes(raw)
 subprocess.run([sys.executable,str(p/'analyze.py'),tmp],check=True)
 subprocess.run([sys.executable,str(p/'audit_screening.py'),tmp],check=True)
print('Recomputed screening.json and screening_audit.json; compare study payload against results.json. UI publication gate is separate.')
