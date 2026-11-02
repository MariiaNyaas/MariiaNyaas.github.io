#!/usr/bin/env python3
"""Safely stage zipped releases for GitHub Pages. ZIPs remain in repo inbox."""
import json, re, stat, zipfile
from pathlib import Path, PurePosixPath
from datetime import date

DOMAINS={'01-credit-risk':'Credit Risk Intelligence','02-financial':'Financial Intelligence','03-accounting':'Accounting & Audit Intelligence','04-governance':'Risk & Governance Intelligence','05-business':'Business & Economic Intelligence','06-public-finance':'Public Finance Intelligence'}
ALLOWED={'index.html','data.json','README.md','methodology.md','executive-brief.md','project.json'}
MAX_UNCOMPRESSED=30*1024*1024
MAX_FILES=200

def ingest(inbox:Path,site:Path):
    if not inbox.exists():
        print('No inbox yet; keeping existing research.');return
    seen=set()
    for archive in sorted(inbox.glob('*.zip')):
        files={}
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                name=info.filename
                if info.is_dir():continue
                path=PurePosixPath(name)
                parts=path.parts
                if (len(parts)!=4 or parts[0]!='daily-intelligence'
                    or not re.fullmatch(r'20\d{2}-\d{2}-\d{2}(?:-r[2-9][0-9]*)?',parts[1])
                    or parts[2] not in DOMAINS or parts[3] not in ALLOWED
                    or '..' in parts or '\\' in name or name.startswith('/')
                    or (info.external_attr>>16)&0o170000 == stat.S_IFLNK):
                    raise ValueError(f'Invalid archive entry in {archive.name}: {name!r}')
                date.fromisoformat(parts[1][:10])
                if info.file_size>MAX_UNCOMPRESSED: raise ValueError('Single file too large')
                if name in files or name in seen:raise ValueError('Duplicate file across ZIPs: '+name)
                files[name]=info
            if len(files)>MAX_FILES or sum(x.file_size for x in files.values())>MAX_UNCOMPRESSED:raise ValueError('Bundle exceeds limits: '+archive.name)
            groups={}
            for name in files:
                parts=PurePosixPath(name).parts; groups.setdefault(tuple(parts[:3]),set()).add(parts[3])
            for group, filenames in groups.items():
                if filenames != ALLOWED: raise ValueError(f'Incomplete project {group}: missing {sorted(ALLOWED-filenames)}')
                metadata=json.loads(z.read('/'.join(group)+'/project.json'))
                if metadata.get('domain')!=DOMAINS[group[2]] or metadata.get('published')!=group[1][:10][:10]:
                    raise ValueError(f'Metadata mismatch: {group}')
                expected='https://mariianyaas.github.io/'+'/'.join(group)+'/'
                if metadata.get('url')!=expected or metadata.get('status','published')!='published':
                    raise ValueError(f'URL/status mismatch: {group}')
            for name,info in files.items():
                target=site.joinpath(*PurePosixPath(name).parts)
                if target.exists():raise ValueError('Conflict with existing published project: '+name)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(z.read(info))
                seen.add(name)
        print(f'Staged {archive.name}: {len(groups)} research project(s)')
    print('Bundle staging complete:',len(seen),'files')
