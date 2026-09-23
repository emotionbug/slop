#!/usr/bin/env bash
set -euo pipefail
[[ $(id -u) == 0 && -d /packages/bzip2 ]] || exit 2
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
work=$(mktemp -d /tmp/bzip2-validation.XXXXXX)
python3 /recipe/check-elf-exports.py snapshot "$work/exports.json" /usr/lib64/libbz2.so.1
# Exercise a C executable linked against the old SONAME, then run the exact
# same executable after the library upgrade.
cat > "$work/check.c" <<'C'
#include <string.h>
#include <stdio.h>
extern int BZ2_bzBuffToBuffCompress(char*,unsigned int*,char*,unsigned int,int,int,int);
extern int BZ2_bzBuffToBuffDecompress(char*,unsigned int*,char*,unsigned int,int,int);
int main(void){char in[]="bzip2 existing EL8 consumer";char compressed[256],out[256];
unsigned int clen=sizeof(compressed),olen=sizeof(out);
if(BZ2_bzBuffToBuffCompress(compressed,&clen,in,sizeof(in),9,0,30))return 1;
if(BZ2_bzBuffToBuffDecompress(out,&olen,compressed,clen,0,0))return 2;
if(olen!=sizeof(in)||memcmp(in,out,sizeof(in)))return 3;
puts("BZIP2_OLD_LINKED_C_ROUNDTRIP_OK");return 0;}
C
gcc "$work/check.c" -Wl,-l:libbz2.so.1 -o "$work/check"
"$work/check"
rpms=(/packages/bzip2/bzip2-1.0.8-1.linuxoss.el8.x86_64.rpm
      /packages/bzip2/bzip2-libs-1.0.8-1.linuxoss.el8.x86_64.rpm)
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
 --setopt=localpkg_gpgcheck=False --setopt=install_weak_deps=False install "${rpms[@]}"
dnf --disableplugin=subscription-manager --disablerepo='*' check
python3 /recipe/check-elf-exports.py compare "$work/exports.json"
"$work/check"
python3 - <<'PY'
import bz2,subprocess,tempfile,pathlib
data=bytes(range(256))*4096
for level in (1,9):
 packed=bz2.compress(data,compresslevel=level)
 assert subprocess.check_output(['bzip2','-dc'],input=packed)==data
 packed=subprocess.check_output(['bzip2','-'+str(level),'-c'],input=data)
 assert bz2.decompress(packed)==data
print('BZIP2_PYTHON_CLI_1MIB_CROSS_ROUNDTRIP_OK')
with tempfile.TemporaryDirectory(prefix='bzip2recover-existing.') as name:
 root=pathlib.Path(name);compressed=root/'input.bz2'
 compressed.write_bytes(bz2.compress(data))
 protected=root/'keep.txt';protected.write_bytes(b'KEEP')
 output=root/'rec00001input.bz2';output.symlink_to(protected.name)
 result=subprocess.run(['bzip2recover',str(compressed)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
 assert result.returncode!=0 and protected.read_bytes()==b'KEEP' and output.is_symlink()
 print('BZIP2RECOVER_EXISTING_SYMLINK_TARGET_NOT_OVERWRITTEN')
PY
echo UBI_BZIP2_LIBRARY_AND_TOOLS_VALIDATED
