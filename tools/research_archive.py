"""Lossless research archives. Build locally; restore after cloning with submodules."""
from pathlib import Path
import argparse, hashlib, json, zipfile, os
ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'research_archive'
SKIP = {'node_modules', '__pycache__', '.git', '.venv', '.ipynb_checkpoints'}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
 return h.hexdigest()
def build():
 ARCHIVE.mkdir(exist_ok=True)
 groups=[]
 for d in sorted((ROOT/'experimental_results').iterdir()):
  if d.is_dir(): groups.append(('experiments-'+d.name,list(d.rglob('*'))))
 b=ROOT/'CNBI-Synthetic-Benchmarks'
 for name in ['data','results','output','outputs']:
  groups.append(('benchmarks-'+name,list((b/name).rglob('*'))))
 groups.append(('benchmarks-scratch-sources',[p for p in (b/'tmp').rglob('*') if p.suffix.lower() in {'.py','.mjs','.docx','.xlsx','.csv','.json','.md','.vbs'}]))
 groups.append(('run-logs',list(ROOT.glob('*.log'))))
 manifest=[]
 for label,paths in groups:
  files=[p for p in sorted(paths) if p.is_file() and not SKIP.intersection(p.relative_to(ROOT).parts) and not p.name.startswith('~$')]
  batches=[]; batch=[]; size=0
  for p in files:
   if batch and size+p.stat().st_size>40*1024**2: batches.append(batch);batch=[];size=0
   batch.append(p);size+=p.stat().st_size
  if batch:batches.append(batch)
  for i,batch in enumerate(batches,1):
   dest=ARCHIVE/f'{label}-{i:03}.zip'; entries=[]
   with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in batch:
     rel=p.relative_to(ROOT).as_posix(); digest=sha(p)
     z.write(p,rel);entries.append({'path':rel,'bytes':p.stat().st_size,'sha256':digest})
   assert dest.stat().st_size<95*1024**2, f'Archive too large: {dest}'
   with zipfile.ZipFile(dest) as z:
    for item in entries:
     assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
   manifest.append({'archive':dest.name,'sha256':sha(dest),'files':entries})
  print(label,len(files),'files',len(batches),'archives',flush=True)
 (ARCHIVE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Verified',sum(len(g['files']) for g in manifest),'files;',sum(p.stat().st_size for p in ARCHIVE.glob('*.zip')),'compressed bytes')
def restore(verify_only=False):
 manifest=json.loads((ARCHIVE/'manifest.json').read_text(encoding='utf-8'))
 for group in manifest:
  archive=ARCHIVE/group['archive'];assert sha(archive)==group['sha256'],archive
  with zipfile.ZipFile(archive) as z:
   for entry in group['files']:
    dest=(ROOT/entry['path']).resolve()
    if not dest.is_relative_to(ROOT.resolve()):raise ValueError('Unsafe archive path')
    data=z.read(entry['path']);assert hashlib.sha256(data).hexdigest()==entry['sha256']
    if verify_only:continue
    if dest.exists():
     if sha(dest)!=entry['sha256']:raise FileExistsError(f'Preserving modified file: {dest}')
     continue
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(data)
 print('Archives verified' if verify_only else 'Research files restored without overwriting changes')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['build','restore','verify']);args=parser.parse_args()
 if args.action=='build':build()
 else:restore(args.action=='verify')
