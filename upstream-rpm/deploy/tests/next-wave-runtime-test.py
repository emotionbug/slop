"""Disposable EL8 reference upgrade and export evidence; not production proof."""
import hashlib,importlib.util,json,os,re,subprocess,tempfile
from pathlib import Path
import dnf
assert Path('/run/.containerenv').exists() or Path('/.dockerenv').exists(), 'Disposable container only'
root=Path('/next/install-kit');out=Path('/next/runtime-validation');out.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('exports','/recipe/check-elf-exports.py')
export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)
spec=importlib.util.spec_from_file_location('installer',str(root/'install-rpms.py'))
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
with dnf.Base() as base:
    base.conf.read();base.conf.plugins=False;base.conf.install_weak_deps=False;base.conf.obsoletes=False;base.conf.best=True
    base.fill_sack(load_system_repo=True,load_available_repos=False)
    installed=list(base.sack.query().installed())
    for package in base.add_remote_rpms([str(p) for p in (root/'rpms').glob('*.rpm')],strict=True):
        old=[p for p in installed if installer.same_slot(p,package)]
        if old and all(installer.compare(package,p)>0 for p in old):base.package_upgrade(package)
    base.resolve(allow_erasing=False)
    paths=[p.localPkg() for p in base.transaction.install_set]
    (out/'preliminary-plan.json').write_text(json.dumps([str(p) for p in base.transaction.install_set],indent=2))
    merged=json.loads((root/'expected-export-removals.json').read_text())
    bylib={p['library']:p for p in merged['libraries']};newlibraries=set()
    with tempfile.TemporaryDirectory(prefix='linuxoss-exports-') as folder:
        for path in paths:
            read=subprocess.Popen(['rpm2cpio',path],stdout=subprocess.PIPE)
            subprocess.run(['cpio','-idm','--quiet'],cwd=folder,stdin=read.stdout,check=True)
            read.stdout.close();assert read.wait()==0
        for path in Path(folder).rglob('*'):
            if not path.is_file() or path.is_symlink():continue
            with path.open('rb') as f:
                if f.read(4)!=b'\x7fELF':continue
            result=subprocess.run(['readelf','-d',str(path)],stdout=subprocess.PIPE,universal_newlines=True,check=True)
            match=re.search(r'\(SONAME\).*\[([^]]+)\]',result.stdout)
            if not match:continue
            target='/'+str(path.relative_to(folder));newlibraries.add(target)
            library='/usr/lib64/'+match.group(1)
            if not Path(library).is_file():continue
            removed=set(export.exports(library))-set(export.exports(str(path)))
            if not removed:continue
            markers=removed & {'__bss_start','_edata','_end'}
            row=bylib.setdefault(library,dict(library=library,symbols=[],scan_symbols=[],linker_generated_markers=[],note='Removed exports measured in the EL8 reference upgrade; target consumers are checked before applying.'))
            row['symbols']=sorted(set(row['symbols'])|removed)
            row['scan_symbols']=sorted(set(row['scan_symbols'])|(removed-markers))
            row['linker_generated_markers']=sorted(set(row['linker_generated_markers'])|markers)
    merged['libraries']=sorted(bylib.values(),key=lambda r:r['library'])
    merged['baseline']='Previous 77-RPM audit plus next-wave EL8 reference exports; not full ABI validation'
    (root/'expected-export-removals.json').write_text(json.dumps(merged,indent=2)+'\n')
    (out/'changed-libraries.json').write_text(json.dumps(sorted(newlibraries),indent=2))
print('EXPORT_REVIEW_READY',len(paths),len(newlibraries),flush=True)
subprocess.run(['/usr/libexec/platform-python',str(root/'install-rpms.py'),'apply',str(root),str(out),'/usr/share'],check=True)
subprocess.run(['dnf','--noplugins','--disablerepo=*','check'],check=True)
errors=[]
for path in sorted(newlibraries):
    if not Path(path).is_file():errors.append([path,'missing']);continue
    result=subprocess.run(['ldd','-r',path],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
    if result.returncode or 'undefined symbol:' in result.stdout or 'not found' in result.stdout:errors.append([path,result.stdout])
(out/'loader-errors.json').write_text(json.dumps(errors,indent=2))
if errors:raise RuntimeError('ELF loader errors: '+str(len(errors)))
print('REFERENCE_UPGRADE_DNF_AND_SHARED_LIBRARY_LOADERS_OK',flush=True)
