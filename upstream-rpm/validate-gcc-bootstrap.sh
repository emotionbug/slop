#!/usr/bin/env bash
# Run in the retained disposable compiler-build image, never on the target.
set -euo pipefail
[[ $(id -u) -ne 0 && $# == 1 && -d $1/gcc ]] || exit 2
build=$(realpath -- "$1")
[[ $build == /tmp/rpmbuild.*/BUILD/gcc-16.2.0/build ]] || exit 2
export PATH=/opt/rh/gcc-toolset-14/root/usr/bin:$PATH
export LC_ALL=C.UTF-8
jobs=${BUILD_JOBS:-8}
[[ $jobs =~ ^[1-9][0-9]*$ ]] || exit 2
mkdir -p /output
set +e
make -C "$build" -j"$jobs" -k check
status=$?
set -e
(cd "$build" && find . -type f \( -name '*.sum' -o -name '*.log' \) \
  -exec cp --parents -t /output -- {} +)
printf '%s\n' "$status" > /output/make-check-exit-code.txt
python3.11 - /output <<'PY'
import collections,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); suites=[]
for p in sorted(root.rglob('*.sum')):
    counts=collections.Counter()
    for line in p.read_text(errors='replace').splitlines():
        tag=line.split(':',1)[0]
        if tag in ('PASS','FAIL','XPASS','XFAIL','UNSUPPORTED','ERROR','UNRESOLVED'):
            counts[tag]+=1
    if counts:suites.append({'file':str(p.relative_to(root)),'counts':dict(counts)})
result={'scope':'Private bootstrap compiler only; not native replacement RPMs',
        'make_exit':int((root/'make-check-exit-code.txt').read_text()),'suites':suites}
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not suites or result['make_exit'] or any(any(s['counts'].get(k,0) for k in ('FAIL','ERROR','UNRESOLVED')) for s in suites):
    raise SystemExit(1)
PY
