#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
bash /recipe/validate-libraries.sh
bash /recipe/validate-format-libraries.sh xml-xz
bash /recipe/validate-image-libraries.sh png-lcms
bash /recipe/validate-cares.sh
if [[ ${INCLUDE_GNU_UTILITIES:-0} == 1 ]]; then
  bash /recipe/validate-utilities.sh sed diffutils patch gawk
fi
if [[ ${INCLUDE_ARCHIVE_UTILITIES:-0} == 1 ]]; then
  [[ ${INCLUDE_GNU_UTILITIES:-0} == 1 ]] || exit 2
  bash /recipe/validate-utilities.sh bison cpio tar
  bash /recipe/validate-bzip2.sh
  python3 /recipe/validate-bison-security.py /usr/bin/bison
  python3 /recipe/validate-cpio-security.py /usr/bin/cpio
fi
dnf --disableplugin=subscription-manager --disablerepo='*' check
if [[ ${INCLUDE_ARCHIVE_UTILITIES:-0} == 1 ]]; then
  python3 - <<'PY'
import subprocess
expected=set('rsync zlib zlib-devel pcre2 pcre2-devel pcre2-utf16 pcre2-utf32 expat expat-devel xz xz-libs xz-devel c-ares libpng lcms2 sed diffutils patch gawk bison cpio bzip2 bzip2-libs tar'.split())
rows=subprocess.check_output(['rpm','-qa','--qf','%{NAME}\t%{RELEASE}\n']).decode().splitlines()
actual={r.split('\t')[0] for r in rows if '.linuxoss' in r.split('\t')[1]}
assert actual==expected,('unexpected',sorted(actual-expected),'missing',sorted(expected-actual))
print('EXACT_24_CUSTOM_RPM_NAMES_VERIFIED',','.join(sorted(actual)))
PY
  echo 'UBI_TWENTY_FOUR_TARGET_PACKAGE_CANDIDATES_COMBINED_OK'
elif [[ ${INCLUDE_GNU_UTILITIES:-0} == 1 ]]; then
  echo 'UBI_NINETEEN_TARGET_PACKAGE_CANDIDATES_COMBINED_OK'
else
  echo 'UBI_FIFTEEN_TARGET_PACKAGE_CANDIDATES_COMBINED_OK'
fi
