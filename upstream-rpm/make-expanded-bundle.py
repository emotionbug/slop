#!/usr/bin/env python3
"""Allowlisted expanded evaluation bundle, with source and read-only preflight.

Requires the recorded final transaction/runtime results. Never includes private
inventory, vulnerability rows, host audit output, logs, credentials or caches.
"""
import hashlib,json,pathlib,re,shutil,tarfile
ROOT=pathlib.Path(__file__).resolve().parent
VERSION='20260924-5'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    v=json.loads((ROOT/'output/validation.json').read_text())
    result=v['_combined_expanded']
    if result['runtime_result']!='passed' or result['host_capability_result']!='passed':
        raise SystemExit('Final combined checks have not passed')
    inputs=json.loads((ROOT/'output/expanded-input-manifest.json').read_text())
    previous=ROOT/'output/candidate-bundle-20260924-4'
    old=json.loads((previous/'manifest.json').read_text())
    archive=ROOT/'output'/('el8-rpm-candidates-'+VERSION+'.tar.gz')
    if archive.exists():raise SystemExit('Refusing to overwrite release archive')
    dest=ROOT/'output'/('candidate-bundle-'+VERSION);dest.mkdir(exist_ok=False)
    files=[]
    def add(source,relative,expected=None):
        digest=sha(source)
        if expected and digest!=expected:raise SystemExit('Hash mismatch: '+source.name)
        target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        files.append({'path':relative,'sha256':digest})
    for r in inputs['files']:add(ROOT/r['path'],'rpms/'+pathlib.Path(r['path']).name,r['sha256'])
    for r in old['files']:
        if r['path'].startswith('srpms/'):add(previous/r['path'],r['path'],r['sha256'])
    projects=inputs['new_projects']
    for project,(directory,version,names) in projects.items():
        sources=list((ROOT/'output'/directory).glob('*.src.rpm'))
        if len(sources)!=1:raise SystemExit('Ambiguous source RPM '+project)
        source=sources[0];add(source,'srpms/'+source.name,v[project]['artifacts'][source.name])
    for name in ('check-removed-symbol-users.py','expected-export-removals.json','preflight-candidates.sh'):
        add(ROOT/name,name)
    declared={s['name'] for s in old['upstream_sources']}
    for project in projects:
        declared.update(re.findall(r'^(?:Source|Patch)\d*:\s*(\S+)',(ROOT/'specs'/(project+'.spec')).read_text(),re.M))
    lock=json.loads((ROOT/'sources.lock.json').read_text())
    manifest={'format_version':2,'status':'container-tested-evaluation-candidates',
      'custom_rpms_signed':False,'all_323_packages_complete':False,'all_cves_resolved':False,
      'target_server_install_tested':False,'private_host_data_included':False,
      'target_package_names':result['target_package_names'],
      'conditional_target_package_names':result['conditional_target_package_names'],
      'target_removed_exports_review_complete':False,
      'additional_dependency_packages':['libgpg-error','cmake-filesystem'],
      'official_dependency':'cmake-filesystem: Red Hat UBI RPM, signature verified',
      'upstream_sources':[s for s in lock['sources'] if s['name'] in declared],
      'runtime_checks':result['runtime_checks'],
      'validation_limits':['46 target names and 2 dependency RPMs passed one UBI transaction.',
         '35 target names have no newly identified conditional exported-API review; this is not target installation clearance.',
         '11 target names require target review of documented removed exports. FreeType includes two old publicly declared APIs.',
         '144 unique removed symbol names are included in read-only preflight; linker-generated anchors are excluded.',
         'Full ABI layout/semantics, dynamic lookups, services, boot and actual target applications not proven.',
         'Named target dependencies: 0 missing, 0 downgrades; 1181 file/rich dependencies remain unverified.',
         'FreeType/nano/tmux/libXpm do not provide substantial upstream make-check suites; focused runtime checks recorded.',
         'Custom RPM absence from a vendor vulnerability feed is not remediation evidence.',
         'Libgcrypt custom build is not a Red Hat FIPS-validated module.'],
      'files':files}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (dest/'README.txt').write_text(
       'EL8 evaluation RPMs: 46 target package names plus libgpg-error and official UBI cmake-filesystem.\n'
       '34 matching source RPMs included. Custom packages are unsigned.\n'
       '11 target names require additional removed-symbol consumer review. Not target installation clearance.\n'
       'Run: sudo bash ./preflight-candidates.sh [additional application directories]\n'
       'This creates local reports and a DNF --assumeno preview; it never installs packages.\n'
       'Full 323-package work and actual target boot/services/rescan are incomplete.\n'
       'https://github.com/emotionbug/slop/blob/main/upstream-rpm/CANDIDATES.md\n',encoding='utf-8')
    include=[r['path'] for r in files]+['manifest.json','README.txt']
    (dest/'SHA256SUMS').write_text(''.join(sha(dest/p)+'  '+p+'\n' for p in include),encoding='ascii')
    include.append('SHA256SUMS')
    assert len([p for p in include if p.startswith('rpms/')])==48
    assert len([p for p in include if p.startswith('srpms/')])==34
    with tarfile.open(archive,'w:gz') as out:
        for path in include:
            if not (dest/path).is_file() or (dest/path).is_symlink():raise ValueError(path)
            out.add(dest/path,arcname='el8-rpm-candidates/'+path,recursive=False)
    digest=sha(archive)
    archive.with_suffix(archive.suffix+'.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    print(json.dumps({'file':archive.name,'size':archive.stat().st_size,'sha256':digest,'members':len(include)}))
if __name__=='__main__':main()
