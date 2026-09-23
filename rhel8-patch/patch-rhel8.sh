#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash patch-rhel8.sh [--proxy URL|direct] MODE [RPM_DIRECTORY]
  ubi-check                 Preview upgrades from public UBI repositories.
  ubi-apply                 Upgrade from UBI; DNF asks before installation.
  rpm-check RPM_DIRECTORY   Check local RPMs and preview with UBI dependencies.
  rpm-apply RPM_DIRECTORY   Install local RPMs with UBI dependencies; DNF asks.
Default: ubi-check; proxy: direct
The check modes do not install packages. DNF may exit 1 after "Operation aborted."
EOF
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }
proxy='direct'
if [[ ${1:-} == --proxy ]]; then
  [[ $# -ge 2 && -n $2 ]] || die '--proxy needs URL or direct'
  proxy=$2
  shift 2
fi
mode=${1:-ubi-check}
[[ $# == 0 ]] || shift
case "$mode" in
  -h|--help) usage; exit 0 ;;
  ubi-check|ubi-apply) [[ $# == 0 ]] || die 'Unexpected argument' ;;
  rpm-check|rpm-apply) [[ $# == 1 ]] || die 'Specify one RPM directory' ;;
  *) usage; exit 2 ;;
esac
[[ $EUID == 0 ]] || die 'Run with sudo bash patch-rhel8.sh ...'
[[ $(uname -m) == x86_64 ]] || die 'Only x86_64 is supported'
# shellcheck disable=SC1091
source /etc/os-release
[[ ${ID:-} == rhel && ${VERSION_ID:-} == 8.* ]] || die 'RHEL 8 is required'
for program in dnf rpm rpmkeys realpath tee; do
  command -v "$program" >/dev/null || die "Missing command: $program"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ -r "$script_dir/ubi8-public.repo" ]] || die 'Keep ubi8-public.repo beside this script'
[[ -r /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release ]] || die 'RHEL signing key file is missing'
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY
export no_proxy='' NO_PROXY='' LC_ALL=C
if [[ $proxy == direct ]]; then
  proxy=''
elif [[ $proxy != http://* && $proxy != https://* ]]; then
  die 'Use an http:// or https:// proxy URL, or direct'
fi

dnf_options=(
  --refresh --best --color=never
  "--setopt=reposdir=$script_dir"
  '--disablerepo=*' '--enablerepo=ubi8-patch-*'
  --disableplugin=subscription-manager
  "--setopt=proxy=$proxy" "--setopt=ubi8-patch-*.proxy=$proxy"
  --setopt=gpgcheck=1 --setopt=localpkg_gpgcheck=1
  --setopt=install_weak_deps=False --setopt=installonly_limit=0
  --setopt=assumeyes=False --setopt=defaultyes=False
)
action=(upgrade)
if [[ $mode == rpm-* ]]; then
  rpm_dir=$(realpath -e -- "$1")
  [[ -d $rpm_dir ]] || die 'Not a directory'
  shopt -s nullglob
  rpms=("$rpm_dir"/*.rpm)
  [[ ${#rpms[@]} -gt 0 ]] || die 'No .rpm files found'
  [[ -x /usr/libexec/platform-python ]] || die 'RHEL platform-python is missing'
  /usr/libexec/platform-python - "${rpms[@]}" <<'PY'
import os
import rpm
import sys

ts = rpm.TransactionSet()
packages = {}
errors = []
def evr(h):
    return (str(h['epoch'] or 0), h['version'], h['release'])
for path in sys.argv[1:]:
    with open(path, 'rb') as stream:
        h = ts.hdrFromFdno(stream.fileno())
    name, arch = h['name'], h['arch']
    label = evr(h)
    if arch not in ('x86_64', 'noarch', 'i686') or 'el8' not in h['release']:
        errors.append('Not a RHEL 8 x86_64/noarch/i686 RPM: ' + os.path.basename(path))
    pair = (name, arch)
    if pair in packages:
        errors.append('Duplicate package name/architecture: %s.%s' % pair)
    packages[pair] = label
    module = (h['modularitylabel'] or '').split(':')[:2]
    same_stream = not any(module)
    for installed in ts.dbMatch('name', name):
        if installed['arch'] == arch and rpm.labelCompare(label, evr(installed)) < 0:
            errors.append('Downgrade refused: ' + os.path.basename(path))
        if installed['arch'] == arch:
            old_module = (installed['modularitylabel'] or '').split(':')[:2]
            if old_module == module:
                same_stream = True
            elif any(old_module):
                errors.append('Module stream change refused: ' + os.path.basename(path))
    if not same_stream:
        errors.append('No installed matching module stream: ' + os.path.basename(path))
    print('RPM: %s-%s:%s-%s.%s' % (name, label[0], label[1], label[2], arch))
boot_names = ('kernel', 'kernel-core', 'kernel-modules', 'kernel-modules-extra')
boot = {n: v for (n, a), v in packages.items() if n in boot_names}
if boot:
    required = ['kernel', 'kernel-core', 'kernel-modules']
    for extra in ('kernel-modules-extra', 'kernel-devel'):
        if list(ts.dbMatch('name', extra)):
            required.append(extra)
    for name in required:
        if (name, 'x86_64') not in packages:
            errors.append('Kernel bundle is missing: ' + name + '.x86_64')
    labels = {v for (n, a), v in packages.items()
              if n in required or n in boot_names or n == 'kernel-devel'}
    if len(labels) != 1:
        errors.append('Kernel bundle versions/releases must match')
if errors:
    sys.exit('\n'.join(errors))
PY
  rpmkeys --checksig "${rpms[@]}"
  action=(install "${rpms[@]}")
fi
if [[ $mode == *-check ]]; then
  dnf_options+=(--assumeno --setopt=assumeno=True)
  printf 'Preview only. No RPM transaction will be run.\n'
else
  dnf_options+=(--setopt=assumeno=False)
  printf 'DNF will display the transaction and ask before installation.\n'
fi
run_dir="$script_dir/logs/$(date -u +%Y%m%dT%H%M%SZ)-$$-$mode"
mkdir -p -- "$run_dir"
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' > "$run_dir/installed-before.tsv"
uname -r > "$run_dir/running-kernel.txt"
printf 'Log: %s\n' "$run_dir/dnf.log"
dnf "${dnf_options[@]}" "${action[@]}" 2>&1 | tee "$run_dir/dnf.log"
if [[ $mode == *-apply ]]; then
  rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' > "$run_dir/installed-after.tsv"
  printf 'DNF completed. Review service restarts; a new kernel requires a planned reboot.\n'
fi
