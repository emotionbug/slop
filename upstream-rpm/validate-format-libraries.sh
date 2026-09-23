#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || { echo 'Container required' >&2; exit 2; }
profile=${1:-all}
[[ $profile == all || $profile == xml-xz ]] || exit 2
libraries=(/usr/lib64/libexpat.so.1 /usr/lib64/liblzma.so.5)
rpms=(
  /rpms/expat/expat-2.8.5-1.linuxoss.el8.x86_64.rpm
  /rpms/expat/expat-devel-2.8.5-1.linuxoss.el8.x86_64.rpm
  /rpms/xz/xz-5.8.4-1.linuxoss.el8.x86_64.rpm
  /rpms/xz/xz-libs-5.8.4-1.linuxoss.el8.x86_64.rpm
  /rpms/xz/xz-devel-5.8.4-1.linuxoss.el8.x86_64.rpm
)
if [[ $profile == all ]]; then
  libraries+=(/usr/lib64/libzstd.so.1)
  if [[ -e /usr/lib64/libcares.so.2 ]]; then
    libraries+=(/usr/lib64/libcares.so.2)
  else
    echo 'CARES_BASELINE_ABI_NOT_AVAILABLE_IN_UBI; new-install runtime check only'
  fi
  rpms+=(
    /rpms/zstd/zstd-1.5.7-1.linuxoss.el8.x86_64.rpm
    /rpms/zstd/libzstd-1.5.7-1.linuxoss.el8.x86_64.rpm
    /rpms/zstd/libzstd-devel-1.5.7-1.linuxoss.el8.x86_64.rpm
    /rpms/c-ares/c-ares-1.34.8-1.linuxoss.el8.x86_64.rpm
    /rpms/c-ares/c-ares-devel-1.34.8-1.linuxoss.el8.x86_64.rpm
  )
fi
python3 /recipe/check-elf-exports.py snapshot /tmp/elf-before.json "${libraries[@]}"
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False install "${rpms[@]}"
dnf --disableplugin=subscription-manager --disablerepo='*' check
python3 /recipe/check-elf-exports.py compare /tmp/elf-before.json
python3 - <<'PY'
import lzma, pyexpat, xml.etree.ElementTree as ET
data = bytes(range(256)) * 4096
for fmt in (lzma.FORMAT_XZ, lzma.FORMAT_ALONE):
    assert lzma.decompress(lzma.compress(data, format=fmt)) == data
assert pyexpat.EXPAT_VERSION == 'expat_2.8.5', pyexpat.EXPAT_VERSION
doc = ET.fromstring('<root><item key="v">한글 &amp; XML</item></root>')
assert doc[0].text == '한글 & XML' and doc[0].attrib['key'] == 'v'
try:
    ET.fromstring('<root><broken></root>')
except ET.ParseError:
    pass
else:
    raise AssertionError('Malformed XML accepted')
open('/tmp/input.bin', 'wb').write(data)
print('PYTHON_LZMA_AND_EXPAT_OK', pyexpat.EXPAT_VERSION)
PY
xz -c /tmp/input.bin | xz -dc | cmp /tmp/input.bin -
if [[ $profile == xml-xz ]]; then
  echo 'UBI_XML_XZ_UPGRADE_AND_RUNTIME_OK'
  exit 0
fi
zstd -q -c /tmp/input.bin | zstd -q -dc | cmp /tmp/input.bin -
cat > /tmp/library-check.c <<'C'
#include <zstd.h>
#include <ares.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <string.h>
int main(void) {
  char source[4096], compressed[8192], restored[4096];
  memset(source, 'A', sizeof(source));
  size_t n=ZSTD_compress(compressed,sizeof(compressed),source,sizeof(source),3);
  if(ZSTD_isError(n))return 1;
  size_t out=ZSTD_decompress(restored,sizeof(restored),compressed,n);
  if(out!=sizeof(source) || memcmp(source,restored,out))return 2;
  if(strcmp(ZSTD_versionString(),"1.5.7"))return 3;
  if(ares_library_init(ARES_LIB_INIT_ALL))return 4;
  if(strcmp(ares_version(NULL),"1.34.8"))return 5;
  /* One A question and compressed-name answer, 192.0.2.123. */
  const unsigned char reply[]={0x12,0x34,0x81,0x80,0,1,0,1,0,0,0,0,
    7,'e','x','a','m','p','l','e',3,'c','o','m',0,0,1,0,1,
    0xc0,0x0c,0,1,0,1,0,0,0,60,0,4,192,0,2,123};
  struct hostent *host=NULL;
  if(ares_parse_a_reply(reply,sizeof(reply),&host,NULL,NULL))return 6;
  if(!host || host->h_length!=4 || memcmp(host->h_addr_list[0],reply+sizeof(reply)-4,4))return 7;
  ares_free_hostent(host);host=NULL;
  if(ares_parse_a_reply(reply,8,&host,NULL,NULL)==ARES_SUCCESS)return 8;
  ares_library_cleanup();
  puts("ZSTD_C_ROUNDTRIP_CARES_DNS_PARSER_OK");return 0;
}
C
gcc -O2 /tmp/library-check.c -lzstd -lcares -o /tmp/library-check
/tmp/library-check
ldd /tmp/library-check
echo 'UBI_FORMAT_LIBRARY_UPGRADE_AND_RUNTIME_OK'
