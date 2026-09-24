#!/usr/bin/env bash
# Runs inside an unprivileged, network-disabled build container.
set -euo pipefail
export LC_ALL=C.UTF-8
[[ $# == 1 && $1 == *.spec ]] || { echo 'Usage: build-rpm.sh /path/package.spec' >&2; exit 2; }
[[ $(id -u) -ne 0 ]] || { echo 'Build as an unprivileged user.' >&2; exit 2; }
spec=$(realpath -- "$1")
reuse_args=()
if [[ -n ${REUSE_RPMBUILD_TOPDIR:-} ]]; then
  top=$(realpath -- "$REUSE_RPMBUILD_TOPDIR")
  [[ $top =~ ^/tmp/rpmbuild\.[[:alnum:]]+$ && -d $top/BUILD && $(stat -c %u "$top") == "$(id -u)" ]] || exit 2
  reuse_args=(--define 'reuse_prepared 1')
  if [[ ${REUSE_CONFIGURED_BUILD:-0} == 1 ]]; then
    [[ $(basename -- "$spec") == glibc-evaluation.spec ]] || exit 2
    reuse_args+=(--define 'reuse_configured 1')
  fi
else
  top=$(mktemp -d /tmp/rpmbuild.XXXXXX)
fi
preserve_evidence() {
  local code=$?
  mkdir -p /output/test-results
  # Thousands of glibc result files are prohibitively slow across a Windows
  # bind mount. Preserve all raw evidence in one archive, plus readable sums.
  if [[ $(basename -- "$spec") == glibc-evaluation.spec ]]; then
    (cd "$top" && find BUILD -type f \( -name testlog.txt -o -name testlog.json -o -name testlog -o -name '*.sum' -o -name '*.trs' -o -name '*.log' -o -name '*.test-result' -o -name '*.out' \) -print0 \
      | tar --null -T - -czf "$top/test-results.tar.gz" \
      && cp "$top/test-results.tar.gz" /output/test-results.tar.gz \
      && find BUILD -type f -name '*.sum' -exec cp --parents -t /output/test-results -- {} +) || true
  else
    (cd "$top" && find BUILD -type f \( -name testlog.txt -o -name testlog.json -o -name testlog -o -name '*.sum' -o -name '*.trs' -o -name '*.log' -o -name '*.test-result' -o -name '*.out' \) \
      -exec cp --parents -t /output/test-results -- {} +) || true
  fi
  # OpenSSL's Perl tests keep failure details and generated fixtures here.
  (cd "$top" && find BUILD -type d -path '*/test/test-runs' -exec cp -r --parents -t /output/test-results -- {} +) || true
  printf '%s\n' "$code" > /output/build-exit-code.txt
  return "$code"
}
trap preserve_evidence EXIT
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp -- "$spec" "$top/SPECS/"
rpmspec -P "$spec" > "$top/expanded.spec"
python3.11 - /recipe/sources.lock.json /sources "$top/SOURCES" "$top/expanded.spec" "${REUSE_RPMBUILD_TOPDIR:-}" <<'PY'
import hashlib,json,pathlib,re,shutil,sys,tarfile
locked={r['name']:r for r in json.load(open(sys.argv[1]))['sources']}
expanded=pathlib.Path(sys.argv[4]).read_text()
needed=re.findall(r'^(?:Source|Patch)\d*:\s*(\S+)',expanded,re.M|re.I)
if not needed: raise SystemExit('No sources declared by SPEC')
for url in needed:
    name=url.rsplit('/',1)[-1]
    if name not in locked: raise SystemExit('Unpinned source: '+name)
    p=pathlib.Path(sys.argv[2])/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=locked[name]['sha256']:
        raise SystemExit('Source hash mismatch: '+name)
    shutil.copyfile(p,pathlib.Path(sys.argv[3])/name)
if sys.argv[5]:
    # A cached source tree must still match every regular file in Source0.
    # Configure, make and the complete check phase will run again below.
    archive=pathlib.Path(sys.argv[2])/needed[0].rsplit('/',1)[-1]
    build=(pathlib.Path(sys.argv[5])/'BUILD').resolve()
    checked=0
    with tarfile.open(archive) as source:
        for member in source:
            if not member.isfile(): continue
            original=pathlib.PurePosixPath(member.name)
            if original.is_absolute() or '..' in original.parts:
                raise SystemExit('Unsafe source archive path')
            cached=(build/member.name).resolve()
            if build not in cached.parents or not cached.is_file():
                raise SystemExit('Cached source is missing: '+member.name)
            if hashlib.sha256(source.extractfile(member).read()).digest()!=hashlib.sha256(cached.read_bytes()).digest():
                raise SystemExit('Cached source was modified: '+member.name)
            checked+=1
    print('VERIFIED_CACHED_SOURCE_FILES',checked)
PY
jobs=${BUILD_JOBS:-4}
[[ $jobs =~ ^[1-9][0-9]*$ ]] || { echo 'Invalid BUILD_JOBS' >&2; exit 2; }
rpmbuild -ba "${reuse_args[@]}" --define "_topdir $top" --define "_smp_mflags -j$jobs" "$top/SPECS/$(basename -- "$spec")"
find "$top/RPMS" "$top/SRPMS" -type f -name '*.rpm' -exec cp -t /output -- {} +
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' | sort > /output/builder-rpms.tsv
for package in /output/*.rpm; do
  rpm -qp --requires "$package" > "$package.requires.txt"
  rpm -qp --provides "$package" > "$package.provides.txt"
  rpm -qp --scripts "$package" > "$package.scripts.txt"
  rpmkeys --checksig "$package"
done
(cd /output && sha256sum -- ./*.rpm > SHA256SUMS)
