#!/usr/bin/env python3
"""Publishable allowlist bundle, gated by recorded installed-RPM validation."""
import hashlib,json,pathlib,re,shutil,tarfile
ROOT=pathlib.Path(__file__).resolve().parent
VERSION='20260924-6'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 result=json.loads((ROOT/'output/wave6-final-validation/runtime-checks.json').read_text())
 caps=json.loads((ROOT/'output/wave6-final-validation/host-capabilities.json').read_text())
 assert result['status']=='passed' and not caps['missing_named_requirements'] and not caps['downgrade_candidates']
 previous=ROOT/'output/candidate-bundle-20260924-5'
 old=json.loads((previous/'manifest.json').read_text())
 inputs=json.loads((ROOT/'output/wave6-inputs.json').read_text())
 archive=ROOT/'output'/('el8-rpm-candidates-'+VERSION+'.tar.gz')
 if archive.exists():raise SystemExit('Refusing to overwrite an existing release archive')
 dest=ROOT/'output'/('candidate-bundle-'+VERSION);dest.mkdir(exist_ok=False)
 files=[]
 def add(source,name,expected=None):
  digest=sha(source)
  if expected and expected!=digest:raise SystemExit('Hash mismatch: '+source.name)
  target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(source,target);files.append(dict(path=name,sha256=digest))
 for row in inputs['files']:
  source=ROOT/row['path'];add(source,'rpms/'+source.name,row['sha256'])
 for row in old['files']:
  if row['path'].startswith('srpms/'):add(previous/row['path'],row['path'],row['sha256'])
 declared={r['name'] for r in old['upstream_sources']}
 for project,(directory,names) in inputs['projects'].items():
  sources=list((ROOT/'output'/directory).glob('*.src.rpm'));assert len(sources)==1
  add(sources[0],'srpms/'+sources[0].name)
  declared.update(re.findall(r'^(?:Source|Patch)\d*:\s*(\S+)',(ROOT/'specs'/(project+'.spec')).read_text(),re.M))
 for name in ['check-removed-symbol-users.py','expected-export-removals.json','preflight-candidates.sh']:add(ROOT/name,name)
 names=old['target_package_names']+[n for d,ns in inputs['projects'].values() for n in ns]
 assert len(names)==51 and len(set(names))==51
 manifest=dict(old,format_version=3,target_package_names=sorted(names),files=files,
  upstream_sources=[s for s in json.loads((ROOT/'sources.lock.json').read_text())['sources'] if s['name'] in declared],
  validation_stages=[dict(target_names=46,runtime_checks=old['runtime_checks']),
   dict(target_names=51,runtime_checks=result['checks'],transaction='Five added RPMs installed over the previously validated 48 RPM environment; final dnf check passed')])
 manifest.pop('runtime_checks',None)
 manifest['validation_limits']=[
  '51 target names plus 2 dependencies; actual server installation has not been performed.',
  '11 conditional target names and 144 removed symbols retain the previous target review requirement.',
  'No missing named target dependencies or downgrades; '+str(len(caps['unverified_requirements']))+' file/rich dependencies remain unverified.',
  'Coreutils 1094 PASS/270 SKIP on upstream source before packaging corrections. Packaging-only builds did not repeat those suites; added arch and final RPM paths/configuration were checked separately.',
  'MTR omitted: after aligning the test listener sequence, 9 tests passed and one packet-size check failed (532 observed vs 512 requested).',
  'pkgconf 3.0.7 built but omitted because SONAME changes from 3 to 8.',
  'The earlier 15 runtime checks were not repeated; four focused checks cover this added group.',
  'No assertion of all 323 packages completed, all CVEs resolved, full ABI compatibility or Red Hat FIPS validation.']
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 (dest/'README.txt').write_text(
  'EL8 evaluation RPMs: 51 target names plus libgpg-error and official UBI cmake-filesystem.\n'
  '53 binary RPMs and 38 corresponding source RPMs. Custom packages are unsigned.\n'
  '11 target names require removed-symbol consumer review. Not target installation clearance.\n'
  'Run: sudo bash ./preflight-candidates.sh [additional application directories]\n'
  'The tool creates local reports and a DNF --assumeno preview without installing packages.\n'
  'See https://github.com/emotionbug/slop/blob/main/upstream-rpm/CANDIDATES.md\n',encoding='utf-8')
 include=[r['path'] for r in files]+['manifest.json','README.txt']
 (dest/'SHA256SUMS').write_text(''.join(sha(dest/p)+'  '+p+'\n' for p in include),encoding='ascii')
 include.append('SHA256SUMS')
 assert sum(p.startswith('rpms/') for p in include)==53 and sum(p.startswith('srpms/') for p in include)==38
 with tarfile.open(archive,'w:gz') as out:
  for p in include:
   assert (dest/p).is_file() and not (dest/p).is_symlink()
   out.add(dest/p,arcname='el8-rpm-candidates/'+p,recursive=False)
 digest=sha(archive)
 archive.with_suffix(archive.suffix+'.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
 print(json.dumps(dict(file=archive.name,size=archive.stat().st_size,sha256=digest,members=len(include))))
if __name__=='__main__':main()
