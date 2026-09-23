#!/usr/bin/env bash
# Runs inside an unprivileged, network-disabled build container.
set -euo pipefail
export LC_ALL=C.UTF-8
[[ $# == 1 && $1 == *.spec ]] || { echo 'Usage: build-rpm.sh /path/package.spec' >&2; exit 2; }
[[ $(id -u) -ne 0 ]] || { echo 'Build as an unprivileged user.' >&2; exit 2; }
spec=$(realpath -- "$1")
top=$(mktemp -d /tmp/rpmbuild.XXXXXX)
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp -- /sources/* "$top/SOURCES/"
cp -- "$spec" "$top/SPECS/"
python3.11 - /recipe/sources.lock.json "$top/SOURCES" <<'PY'
import hashlib,json,pathlib,sys
for source in json.load(open(sys.argv[1]))['sources']:
    p=pathlib.Path(sys.argv[2])/source['name']
    if hashlib.sha256(p.read_bytes()).hexdigest()!=source['sha256']:
        raise SystemExit('Source hash mismatch: '+source['name'])
PY
rpmbuild -ba --define "_topdir $top" --define '_smp_mflags -j8' "$top/SPECS/$(basename -- "$spec")"
find "$top/RPMS" "$top/SRPMS" -type f -name '*.rpm' -exec cp -t /output -- {} +
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' | sort > /output/builder-rpms.tsv
for package in /output/*.rpm; do
  rpm -qp --requires "$package" > "$package.requires.txt"
  rpm -qp --provides "$package" > "$package.provides.txt"
  rpm -qp --scripts "$package" > "$package.scripts.txt"
  rpmkeys --checksig "$package"
done
(cd /output && sha256sum -- ./*.rpm > SHA256SUMS)
