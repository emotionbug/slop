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
dnf --disableplugin=subscription-manager --disablerepo='*' check
if [[ ${INCLUDE_GNU_UTILITIES:-0} == 1 ]]; then
  echo 'UBI_NINETEEN_TARGET_PACKAGE_CANDIDATES_COMBINED_OK'
else
  echo 'UBI_FIFTEEN_TARGET_PACKAGE_CANDIDATES_COMBINED_OK'
fi
