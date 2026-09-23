#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
rpm -q libarchive
python3 /recipe/check-elf-exports.py snapshot /tmp/archive-elf-before.json /usr/lib64/libarchive.so.13
python3 - <<'PY'
import hashlib,json,pathlib,tarfile
name='libarchive-3.8.9.tar.xz'
source=next(s for s in json.load(open('/recipe/sources.lock.json'))['sources'] if s['name']==name)
path=pathlib.Path('/recipe/sources')/name
assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']
dest=pathlib.Path('/tmp/archive-headers');dest.mkdir()
with tarfile.open(str(path)) as archive:
    for header in ('archive.h','archive_entry.h'):
        (dest/header).write_bytes(archive.extractfile('libarchive-3.8.9/libarchive/'+header).read())
PY
cat > /tmp/archive-check.c <<'C'
#include <archive.h>
#include <archive_entry.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"archive check line %d\n",__LINE__);return 1;} }while(0)
int main(void){
  char buffer[65536], restored[32];size_t used=0;
  const char payload[]="archive roundtrip data";
  struct archive *w=archive_write_new();CHECK(w);
  CHECK(archive_write_set_format_pax_restricted(w)==ARCHIVE_OK);
  CHECK(archive_write_add_filter_gzip(w)==ARCHIVE_OK);
  CHECK(archive_write_open_memory(w,buffer,sizeof(buffer),&used)==ARCHIVE_OK);
  struct archive_entry *entry=archive_entry_new();CHECK(entry);
  archive_entry_set_pathname(entry,"sample.txt");archive_entry_set_filetype(entry,AE_IFREG);
  archive_entry_set_perm(entry,0644);archive_entry_set_size(entry,sizeof(payload)-1);
  CHECK(archive_write_header(w,entry)==ARCHIVE_OK);
  CHECK(archive_write_data(w,payload,sizeof(payload)-1)==sizeof(payload)-1);
  archive_entry_free(entry);CHECK(archive_write_close(w)==ARCHIVE_OK);CHECK(archive_write_free(w)==ARCHIVE_OK);
  struct archive *r=archive_read_new();CHECK(r);
  CHECK(archive_read_support_filter_all(r)==ARCHIVE_OK);CHECK(archive_read_support_format_all(r)==ARCHIVE_OK);
  CHECK(archive_read_open_memory(r,buffer,used)==ARCHIVE_OK);
  CHECK(archive_read_next_header(r,&entry)==ARCHIVE_OK);
  CHECK(strcmp(archive_entry_pathname(entry),"sample.txt")==0);
  CHECK(archive_entry_size(entry)==sizeof(payload)-1);
  CHECK(archive_read_data(r,restored,sizeof(restored))==sizeof(payload)-1);
  CHECK(memcmp(payload,restored,sizeof(payload)-1)==0);
  CHECK(archive_read_next_header(r,&entry)==ARCHIVE_EOF);CHECK(archive_read_free(r)==ARCHIVE_OK);
  printf("LIBARCHIVE_OLD_BINARY_ROUNDTRIP_OK %s\n",archive_version_string());return 0;
}
C
gcc -O2 -I/tmp/archive-headers /tmp/archive-check.c -l:libarchive.so.13 -o /tmp/archive-check
/tmp/archive-check
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False install \
  /rpms/libarchive/libarchive-3.8.9-1.linuxoss.el8.x86_64.rpm \
  /rpms/libarchive/bsdtar-3.8.9-1.linuxoss.el8.x86_64.rpm
dnf --disableplugin=subscription-manager --disablerepo='*' check
abi_status=0
python3 /recipe/check-elf-exports.py compare /tmp/archive-elf-before.json || abi_status=$?
/tmp/archive-check
bsdtar --version
mkdir -p /tmp/archive-fixture/input /tmp/archive-fixture/output
printf 'archive cli payload\n' > /tmp/archive-fixture/input/data
ln /tmp/archive-fixture/input/data /tmp/archive-fixture/input/hardlink
ln -s data /tmp/archive-fixture/input/symlink
for suffix in gz xz zst; do
  archive=/tmp/archive-fixture/sample.tar.$suffix
  bsdtar -a -cf "$archive" -C /tmp/archive-fixture/input .
  mkdir "/tmp/archive-fixture/output/$suffix"
  bsdtar -xf "$archive" -C "/tmp/archive-fixture/output/$suffix"
  cmp /tmp/archive-fixture/input/data "/tmp/archive-fixture/output/$suffix/data"
  [[ $(readlink "/tmp/archive-fixture/output/$suffix/symlink") == data ]]
  [[ $(stat -c %i "/tmp/archive-fixture/output/$suffix/data") == $(stat -c %i "/tmp/archive-fixture/output/$suffix/hardlink") ]]
done
if [[ $abi_status != 0 ]]; then
  echo 'ARCHIVE_FUNCTIONAL_CHECKS_PASSED_BUT_ABI_EXPORTS_FAILED; candidate remains held'
  exit "$abi_status"
fi
echo 'UBI_LIBARCHIVE_UPGRADE_OLD_BINARY_AND_CLI_OK'
