#!/usr/bin/env bash
# Build a sanitizer control from the same pinned original and patched source.
set -euo pipefail
[[ $(id -u) != 0 && -f /sources/bzip2-1.0.8.tar.gz ]] || exit 2
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
work=$(mktemp -d /tmp/bzip2-recovery.XXXXXX)
cd "$work"
tar -xf /sources/bzip2-1.0.8.tar.gz
cd bzip2-1.0.8
cp bzip2recover.c original.c
patch --fuzz=0 -p1 < /sources/bzip2-CVE-2026-42250.patch
patch --fuzz=0 -p1 < /sources/bzip2recover-race-open-output.patch
for variant in original bzip2recover; do
  /usr/bin/gcc -O1 -g -fno-common -fsanitize=address -fno-omit-frame-pointer "$variant.c" -o "$variant-asan"
done
python3.11 - <<'PY'
import os,pathlib,resource,subprocess
root=pathlib.Path.cwd()
fixture=root/'too-many-blocks.bz2'
fixture.write_bytes(bytes.fromhex('314159265359')*100002)
def limits():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_CPU,(15,15))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))
for name,vulnerable in [('original',True),('bzip2recover',False)]:
    with open(name+'.stderr','wb') as error:
        result=subprocess.run([str(root/(name+'-asan')),str(fixture)],stdout=subprocess.DEVNULL,stderr=error,
          timeout=20,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1'),preexec_fn=limits)
    output=pathlib.Path(name+'.stderr').read_bytes()
    if vulnerable:
        assert b'AddressSanitizer: global-buffer-overflow' in output and result.returncode!=0, (result.returncode,output[-2048:])
        print('BZIP2RECOVER_ORIGINAL_GLOBAL_OVERFLOW_REPRODUCED')
    else:
        assert b'AddressSanitizer' not in output and result.returncode==1
        assert b'cannot be handled' in output
        print('BZIP2RECOVER_PATCHED_BOUNDARY_REJECTED_WITHOUT_ASAN_ERROR')
assert not list(root.glob('rec*.bz2')), 'Must reject before writing recovered files'
PY
