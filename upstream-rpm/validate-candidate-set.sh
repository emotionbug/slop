#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
bash /recipe/validate-libraries.sh
bash /recipe/validate-format-libraries.sh xml-xz
bash /recipe/validate-image-libraries.sh png-lcms
bash /recipe/validate-cares.sh
dnf --disableplugin=subscription-manager --disablerepo='*' check
echo 'UBI_FIFTEEN_TARGET_PACKAGE_CANDIDATES_COMBINED_OK'
