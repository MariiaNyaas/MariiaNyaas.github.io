import hashlib, json, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
FINAL=HERE/'final'
SLUGS=['01-credit-risk','02-financial','03-accounting','04-governance','05-business','06-public-finance','07-art-capital']

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

rows=[]
for slug in SLUGS:
    p=FINAL/f'{slug}.mp4'
    if not p.exists():
        rows.append({'slug':slug,'status':'NOT_READY'}); continue
    raw=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=index,codec_type,width,height,r_frame_rate:format=duration','-of','json',str(p)],text=True)
    probe=json.loads(raw); streams=probe['streams']; duration=float(probe['format']['duration'])
    video=next((s for s in streams if s['codec_type']=='video'),{})
    checks={
      'duration_140':abs(duration-140)<0.02,
      'vertical_1080x1920':video.get('width')==1080 and video.get('height')==1920,
      'fps_30':video.get('r_frame_rate')=='30/1',
      'audio_present':any(s['codec_type']=='audio' for s in streams),
      'no_subtitle_track':not any(s['codec_type']=='subtitle' for s in streams)
    }
    rows.append({'slug':slug,'status':'PASS' if all(checks.values()) else 'FAIL','duration':duration,'checks':checks,'sha256':sha256(p),'bytes':p.stat().st_size})
(HERE/'media_audit.json').write_text(json.dumps({'scope':'Automated container/stream QA; not a substitute for full human listening and motion review.','items':rows},indent=2)+'\n')
print(json.dumps(rows,indent=2))
