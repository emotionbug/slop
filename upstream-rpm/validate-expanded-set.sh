#!/usr/bin/env bash
# One transaction in a disposable EL8 container, followed by focused runtime checks.
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
mkdir -p /results
python3 - <<'PY'
import glob,json,os,pathlib,sys,tarfile
sys.path.insert(0,'/recipe')
from importlib.machinery import SourceFileLoader
elf=SourceFileLoader('elf','/recipe/check-elf-exports.py').load_module()
paths=['libpopt.so.0','libonig.so.5','libXpm.so.4','libpcap.so.1','libtasn1.so.6',
       'libssh.so.4','libmagic.so.1','libjpeg.so.62','libzstd.so.1','libharfbuzz.so.0',
       'libfreetype.so.6','libogg.so.0','libpng16.so.16','liblcms2.so.2','libexpat.so.1','liblzma.so.5',
       'libgcrypt.so.20','libgpg-error.so.0','libopenjp2.so.7']
data={'/usr/lib64/'+p:elf.exports('/usr/lib64/'+p) for p in paths if os.path.exists('/usr/lib64/'+p)}
pathlib.Path('/results/exports-before.json').write_text(json.dumps(data,indent=2))
# Reuse the already-reviewed old-header image round-trip client, without its
# separate DNF transactions or previous symbol-failure policy.
script=pathlib.Path('/recipe/validate-image-libraries.sh').read_text()
code=script.split("cat > /tmp/image-check.c <<'C'\n",1)[1].split('\nC\n',1)[0]
pathlib.Path('/tmp/image-check.c').write_text(code)
with tarfile.open('/recipe/sources/lcms2-2.19.1.tar.gz') as t:
    pathlib.Path('/tmp/lcms2.h').write_bytes(t.extractfile('lcms2-2.19.1/include/lcms2.h').read())
PY
gcc -O2 -I/tmp /tmp/image-check.c -lpng16 -ljpeg -l:liblcms2.so.2 -lm -o /tmp/image-check
/tmp/image-check
cat > /tmp/zstd-old.c <<'C'
#include <zstd.h>
#include <string.h>
#include <stdio.h>
int main(void) {
 char a[4096],b[8192],c[4096]; memset(a,42,sizeof(a));
 size_t n=ZSTD_compress(b,sizeof(b),a,sizeof(a),3);
 if(ZSTD_isError(n))return 1;
 size_t m=ZSTD_decompress(c,sizeof(c),b,n);
 if(m!=sizeof(a)||memcmp(a,c,m))return 2;
 if(!ZSTD_isError(ZSTD_decompress(c,sizeof(c),"bad",3)))return 3;
 printf("OLD_LINKED_ZSTD_ROUNDTRIP_OK %s\n",ZSTD_versionString());return 0;
}
C
gcc -O2 /tmp/zstd-old.c -lzstd -o /tmp/zstd-old
/tmp/zstd-old
gcc -O2 -I/recipe/tests/fixtures /recipe/tests/onig-posix-old-client.c -l:libonig.so.5 -o /tmp/onig-old
/tmp/onig-old
cp /usr/bin/rsync /tmp/rsync-before
printf '\n# local configuration preservation fixture\n' >> /etc/libssh/libssh_client.config
cp /etc/libssh/libssh_client.config /tmp/libssh-client-before
# Only development headers added to this disposable test image are removed.
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=clean_requirements_on_remove=False remove libpng-devel libjpeg-turbo-devel
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' > /results/rpms-before.tsv
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=install_weak_deps=False --setopt=localpkg_gpgcheck=False install /candidates/*.rpm
dnf --disableplugin=subscription-manager --disablerepo='*' check
cmp /etc/libssh/libssh_client.config /tmp/libssh-client-before
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' > /results/rpms-after.tsv
python3 - <<'PY'
import glob,json,pathlib,subprocess,sys
from importlib.machinery import SourceFileLoader
elf=SourceFileLoader('elf','/recipe/check-elf-exports.py').load_module()
before=json.loads(pathlib.Path('/results/exports-before.json').read_text())
review=json.loads(pathlib.Path('/recipe/expected-export-removals.json').read_text())
allowed={r['library']:set(r['symbols']) for r in review['libraries']}
rows=[]
for path,symbols in before.items():
    missing=set(symbols)-set(elf.exports(path))
    rows.append({'library':path,'baseline_exports':len(symbols),'missing':sorted(missing),
                 'unexpected_missing':sorted(missing-allowed.get(path,set()))})
pathlib.Path('/results/exports-after.json').write_text(json.dumps(rows,indent=2))
assert not any(r['unexpected_missing'] for r in rows),rows
expected={subprocess.check_output(['rpm','-qp','--qf','%{NAME}',p]).decode() for p in glob.glob('/candidates/*.rpm') if '.linuxoss.' in p}
actual={line.split('\t')[0] for line in pathlib.Path('/results/rpms-after.tsv').read_text().splitlines() if '.linuxoss.' in line}
assert actual==expected,(expected-actual,actual-expected)
elf_files=set()
for package in sorted(actual):
    for line in subprocess.check_output(['rpm','-ql',package]).decode().splitlines():
        p=pathlib.Path(line)
        if p.is_file():
            with p.open('rb') as stream:header=stream.read(4)
            if header==b'\x7fELF':elf_files.add(str(p.resolve()))
for path in sorted(elf_files):
    dynamic=subprocess.check_output(['readelf','-d',path]).decode()
    paths=[line for line in dynamic.splitlines() if '(RPATH)' in line or '(RUNPATH)' in line]
    assert not any('/opt/linuxoss-' in line or '/tmp/' in line for line in paths),(path,paths)
print('NO_PRIVATE_BUILD_PREFIX_RPATH',len(elf_files))
print('EXACT_CUSTOM_RPM_SET_OK',len(actual))
print('NO_UNEXPECTED_EXPORT_CHANGES; documented removals require target review; not ABI clearance')
PY
/tmp/image-check
/tmp/zstd-old
/tmp/onig-old
python3 /recipe/validate-expanded-runtime.py
echo EXPANDED_SINGLE_TRANSACTION_AND_RUNTIME_OK
