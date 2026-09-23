#!/usr/bin/env bash
# Runs inside an unprivileged, network-disabled build container.
set -euo pipefail
export LC_ALL=C.UTF-8
[[ $# == 1 && $1 == *.spec ]] || { echo 'Usage: build-rpm.sh /path/package.spec' >&2; exit 2; }
[[ $(id -u) -ne 0 ]] || { echo 'Build as an unprivileged user.' >&2; exit 2; }
spec=$(realpath -- "$1")
top=$(mktemp -d /tmp/rpmbuild.XXXXXX)
preserve_evidence() {
  local code=$?
  mkdir -p /output/test-results
  (cd "$top" && find BUILD -type f \( -name '*.sum' -o -name '*.trs' -o -name '*.log' -o -name '*.test-result' -o -name '*.out' \) \
    -exec cp --parents -t /output/test-results -- {} +) || true
  # OpenSSL's Perl tests keep failure details and generated fixtures here.
  (cd "$top" && find BUILD -type d -path '*/test/test-runs' -exec cp -r --parents -t /output/test-results -- {} +) || true
  printf '%s\n' "$code" > /output/build-exit-code.txt
  return "$code"
}
trap preserve_evidence EXIT
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp -- "$spec" "$top/SPECS/"
rpmspec -P "$spec" > "$top/expanded.spec"
python3.11 - /recipe/sources.lock.json /sources "$top/SOURCES" "$top/expanded.spec" <<'PY'
import hashlib,json,pathlib,re,shutil,sys
locked={r['name']:r for r in json.load(open(sys.argv[1]))['sources']}
expanded=pathlib.Path(sys.argv[4]).read_text()
needed=re.findall(r'^Source\d*:\s*(\S+)',expanded,re.M|re.I)
if not needed: raise SystemExit('No sources declared by SPEC')
for url in needed:
    name=url.rsplit('/',1)[-1]
    if name not in locked: raise SystemExit('Unpinned source: '+name)
    p=pathlib.Path(sys.argv[2])/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=locked[name]['sha256']:
        raise SystemExit('Source hash mismatch: '+name)
    shutil.copyfile(p,pathlib.Path(sys.argv[3])/name)
PY
jobs=${BUILD_JOBS:-4}
[[ $jobs =~ ^[1-9][0-9]*$ ]] || { echo 'Invalid BUILD_JOBS' >&2; exit 2; }
rpmbuild -ba --define "_topdir $top" --define "_smp_mflags -j$jobs" "$top/SPECS/$(basename -- "$spec")"
find "$top/RPMS" "$top/SRPMS" -type f -name '*.rpm' -exec cp -t /output -- {} +
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' | sort > /output/builder-rpms.tsv
for package in /output/*.rpm; do
  rpm -qp --requires "$package" > "$package.requires.txt"
  rpm -qp --provides "$package" > "$package.provides.txt"
  rpm -qp --scripts "$package" > "$package.scripts.txt"
  rpmkeys --checksig "$package"
done
(cd /output && sha256sum -- ./*.rpm > SHA256SUMS)
