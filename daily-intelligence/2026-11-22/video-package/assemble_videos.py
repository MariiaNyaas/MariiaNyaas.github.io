import json, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
AROLL=HERE/'aroll'
VIS=HERE/'visuals'
FINAL=HERE/'final'
FINAL.mkdir(exist_ok=True)

def probe(path):
    out=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],text=True)
    return float(out.strip())

def assemble(slug):
    src=AROLL/f'{slug}.mp4'
    duration=probe(src)
    if duration < 120:
        raise SystemExit(f'{slug}: narration is only {duration:.2f}s; stop for editorial review')
    end=min(duration-10,128)
    inputs=[src,VIS/f'{slug}-evidence.png',VIS/f'{slug}-validation.png',VIS/f'{slug}-mechanism.png']
    cmd=['ffmpeg','-y','-i',str(inputs[0])]
    for p in inputs[1:]: cmd += ['-loop','1','-i',str(p)]
    # Charts and the published mechanism occupy about 60–65% of the running time.
    fc=(
      "[1:v]scale=1080:1920,format=rgba[e];"
      "[2:v]scale=1080:1920,format=rgba[v];"
      "[3:v]scale=1080:1920,format=rgba[m];"
      "[0:v]scale=1080:1920,setsar=1[base];"
      "[base][e]overlay=0:0:enable='between(t,12,34)+between(t,94,112)'[x1];"
      "[x1][v]overlay=0:0:enable='between(t,48,66)+between(t,112,%s)'[x2];"
      "[x2][m]overlay=0:0:enable='between(t,66,80)'[outv]" % f'{end:.3f}'
    )
    core=FINAL/f'{slug}-core.mp4'
    cmd += ['-filter_complex',fc,'-map','[outv]','-map','0:a:0','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-r','30','-c:a','aac','-ar','48000','-b:a','192k','-movflags','+faststart','-shortest',str(core)]
    subprocess.check_call(cmd)
    core_duration=probe(core)
    if core_duration >= 140:
        raise SystemExit(f'{slug}: core is {core_duration:.3f}s and cannot be cut without truncating speech')
    gap=140-core_duration
    out=FINAL/f'{slug}.mp4'
    outro=VIS/f'{slug}-outro.png'
    # The purposeful research-navigation card fills the remaining seconds; a soft sonic mark avoids padded silence.
    cmd2=['ffmpeg','-y','-i',str(core),'-loop','1','-t',f'{gap:.6f}','-i',str(outro),'-f','lavfi','-t',f'{gap:.6f}','-i','sine=frequency=523.25:sample_rate=48000',
          '-filter_complex','[0:v]setpts=PTS-STARTPTS[v0];[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asetpts=PTS-STARTPTS[a0];[1:v]scale=1080:1920,format=yuv420p,setpts=PTS-STARTPTS[v1];[2:a]volume=0.025,afade=t=out:st='+f'{max(0,gap-1.2):.6f}'+':d=1.2,aformat=sample_rates=48000:channel_layouts=stereo,asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]',
          '-map','[outv]','-map','[outa]','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-r','30','-c:a','aac','-ar','48000','-b:a','192k','-movflags','+faststart','-t','140',str(out)]
    subprocess.check_call(cmd2)
    return {'slug':slug,'source_duration':duration,'core_duration':core_duration,'outro_duration':gap,'final_duration':probe(out)}

if __name__=='__main__':
    slugs=sys.argv[1:] or ['01-credit-risk','02-financial','03-accounting','04-governance','05-business','06-public-finance','07-art-capital']
    print(json.dumps([assemble(s) for s in slugs],indent=2))
