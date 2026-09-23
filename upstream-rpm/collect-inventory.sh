#!/usr/bin/env bash
# Read-only package/ABI inventory. Does not collect configuration contents or keys.
set -euo pipefail
export LC_ALL=C
umask 077
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || {
  echo 'Linux x86_64 host required.' >&2; exit 2;
}
for cmd in rpm sort tar sha256sum mktemp; do
  command -v "$cmd" >/dev/null || { echo "Missing command: $cmd" >&2; exit 2; }
done
parent=${1:-$PWD}
mkdir -p -- "$parent"
parent=$(cd -- "$parent" && pwd -P)
out=$(mktemp -d "$parent/rpm-inventory-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
printf 'name\tepoch\tversion\trelease\tarch\tsource_rpm\tvendor\tmodule\n' > "$out/packages.tsv"
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\t%{SOURCERPM}\t%{VENDOR}\t%{MODULARITYLABEL}\n' |
  sort >> "$out/packages.tsv"
for relation in REQUIRE PROVIDE CONFLICT OBSOLETE; do
  # =NAME and =ARCH repeat the scalar package fields for every dependency row.
  printf 'name\tarch\tcapability\tflags\tversion\n' > "$out/${relation,,}s.tsv"
  rpm -qa --qf "[%{=NAME}\t%{=ARCH}\t%{${relation}NAME}\t%{${relation}FLAGS:depflags}\t%{${relation}VERSION}\n]" |
    sort >> "$out/${relation,,}s.tsv"
done
{
  printf 'running_kernel='; uname -r
  printf 'machine='; uname -m
  [[ ! -r /etc/os-release ]] || cat /etc/os-release
  printf '\nRPM version: '; rpm --version
} > "$out/platform.txt"
if command -v ldconfig >/dev/null; then ldconfig -p > "$out/ldconfig.txt" 2>&1; fi
if command -v systemctl >/dev/null; then
  systemctl list-unit-files --type=service --no-pager > "$out/service-states.txt" 2>&1 || true
fi
if command -v lspci >/dev/null; then lspci -nnk > "$out/pci-drivers.txt" 2>&1 || true; fi
if command -v lsmod >/dev/null; then lsmod > "$out/loaded-modules.txt" 2>&1 || true; fi
if command -v mokutil >/dev/null; then mokutil --sb-state > "$out/secure-boot.txt" 2>&1 || true; fi
if [[ -d /sys/firmware/efi ]]; then echo UEFI > "$out/boot-mode.txt"; else echo BIOS > "$out/boot-mode.txt"; fi
for config in /boot/config-*; do
  [[ -f $config && -r $config ]] && cp -- "$config" "$out/"
done
cat > "$out/README.txt" <<'EOF'
Private target-server metadata: do not commit or publish this archive.
Includes RPM headers (source RPM, Requires/Provides/Conflicts/Obsoletes),
library cache, service enablement, kernel build configuration and driver IDs.
Does not copy application JAR/WAR files, application source, configuration
contents, environment variables, passwords, private keys or certificates.
This inventory does not identify every library loaded by a running application.
EOF
(cd -- "$out" && sha256sum -- ./* > SHA256SUMS)
archive="$out.tar.gz"
tar -C "$parent" -czf "$archive" -- "$(basename -- "$out")"
printf 'Created: %s\n' "$archive"
sha256sum -- "$archive"
