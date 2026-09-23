#!/usr/bin/env bash
# Disposable UBI 8 validation container; local RPMs only, no repositories.
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || { echo 'Container required' >&2; exit 2; }
declare -a rpms=(
  /rpms/rsync/rsync-3.5.1-1.linuxoss.el8.x86_64.rpm
  /rpms/zlib/zlib-1.3.2-1.linuxoss.el8.x86_64.rpm
  /rpms/zlib/zlib-devel-1.3.2-1.linuxoss.el8.x86_64.rpm
  /rpms/pcre2/pcre2-10.48-1.linuxoss.el8.x86_64.rpm
  /rpms/pcre2/pcre2-utf16-10.48-1.linuxoss.el8.x86_64.rpm
  /rpms/pcre2/pcre2-utf32-10.48-1.linuxoss.el8.x86_64.rpm
  /rpms/pcre2/pcre2-devel-10.48-1.linuxoss.el8.x86_64.rpm
  /rpms/pcre2/pcre2-tools-10.48-1.linuxoss.el8.x86_64.rpm
)
cp /usr/bin/rsync /tmp/rsync-before
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False install "${rpms[@]}"
dnf --disableplugin=subscription-manager --disablerepo='*' check
rpm -q zlib zlib-devel pcre2 pcre2-utf16 pcre2-utf32 pcre2-devel
python3 - <<'PY'
import zlib
data=bytes(range(256))*4096
assert zlib.decompress(zlib.compress(data)) == data
assert zlib.ZLIB_RUNTIME_VERSION == '1.3.2', zlib.ZLIB_RUNTIME_VERSION
print('PYTHON_ZLIB_ROUNDTRIP_OK', zlib.ZLIB_RUNTIME_VERSION)
PY
cat > ZlibCheck.java <<'JAVA'
import java.io.*;
import java.util.*;
import java.util.zip.*;
class ZlibCheck {
    public static void main(String[] args) throws Exception {
        byte[] data=new byte[1048576]; new Random(7).nextBytes(data);
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        try(GZIPOutputStream gz=new GZIPOutputStream(out)){gz.write(data);}
        ByteArrayOutputStream restored=new ByteArrayOutputStream();
        try(GZIPInputStream in=new GZIPInputStream(new ByteArrayInputStream(out.toByteArray()))){
            byte[] buffer=new byte[8192]; int n;
            while((n=in.read(buffer))!=-1)restored.write(buffer,0,n);
        }
        if(!Arrays.equals(data,restored.toByteArray()))throw new AssertionError("gzip round trip");
        System.out.println("JAVA8_GZIP_ROUNDTRIP_OK");
    }
}
JAVA
javac ZlibCheck.java
java ZlibCheck
cat > check-pcre.c <<'C'
#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>
#include <string.h>
#include <stdio.h>
int main(void) {
  int error; PCRE2_SIZE offset;
  pcre2_code *code=pcre2_compile((PCRE2_SPTR)"^(?<key>[a-z]+)=(?<value>[0-9]+)$", PCRE2_ZERO_TERMINATED, 0, &error, &offset, NULL);
  if(!code || pcre2_jit_compile(code, PCRE2_JIT_COMPLETE))return 1;
  pcre2_match_data *data=pcre2_match_data_create_from_pattern(code,NULL);
  int rc=pcre2_match(code,(PCRE2_SPTR)"count=123",9,0,0,data,NULL);
  if(rc!=3)return 2;
  if(pcre2_match(code,(PCRE2_SPTR)"count=bad",9,0,0,data,NULL)!=PCRE2_ERROR_NOMATCH)return 3;
  pcre2_match_data_free(data); pcre2_code_free(code); puts("PCRE2_JIT_MATCH_OK"); return 0;
}
C
gcc -O2 check-pcre.c -lpcre2-8 -o check-pcre
./check-pcre
printf 'server=123\ninvalid\n' | pcre2grep '^server=[0-9]+$'
ldd ./check-pcre
work=$(mktemp -d /tmp/rsync-combined.XXXXXX)
mkdir -p "$work/source/sub" "$work/local" "$work/pull" "$work/push"
printf 'combined-library-test\n' > "$work/source/sub/file"
ln -s sub/file "$work/source/link"
ln "$work/source/sub/file" "$work/source/hardlink"
cat > "$work/local-shell" <<'EOF'
#!/bin/bash
shift
exec "$@"
EOF
chmod 0755 "$work/local-shell"
rsync -aH "$work/source/" "$work/local/"
rsync -aH -e "$work/local-shell" --rsync-path=/tmp/rsync-before "localhost:$work/source/" "$work/pull/"
rsync -aH -e "$work/local-shell" --rsync-path=/tmp/rsync-before "$work/source/" "localhost:$work/push/"
for mode in local pull push; do
  diff -r "$work/source" "$work/$mode"
  [[ $(readlink "$work/$mode/link") == sub/file ]]
  [[ $(stat -c %i "$work/$mode/sub/file") == "$(stat -c %i "$work/$mode/hardlink")" ]]
  echo "PASS: combined rsync $mode content/symlink/hardlink"
done
echo 'UBI_LIBRARY_UPGRADE_DNF_PYTHON_JAVA_PCRE2_OK'
