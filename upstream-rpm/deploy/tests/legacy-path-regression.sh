#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
trap 'cp -a /var/log/linuxoss-install/. /results/ 2>/dev/null || true' EXIT
# Show the old candidate fails for the same exact /bin/sed dependency.
if dnf --noplugins --disablerepo='*' --setopt=localpkg_gpgcheck=False \
    --setopt=tsflags=test -y install /old/rpms/sed-4.10-1.linuxoss.el8.x86_64.rpm \
    > /results/old-sed-dependency-error.txt 2>&1; then
    echo 'Old sed unexpectedly resolved' >&2; exit 2
fi
grep -q '/bin/sed' /results/old-sed-dependency-error.txt
echo OLD_SED_PATH_FAILURE_REPRODUCED
bash /kit/install.sh apply
rpm -q linuxoss-test-legacy-consumer
rpm -q --whatprovides /bin/sed /bin/chmod /bin/awk /bin/gawk /bin/cpio /bin/tar /bin/gtar
[[ $(/bin/sed --version | head -n 1) == *4.10* ]]
[[ $(/bin/awk 'BEGIN { print 2+3 }') == 5 ]]
[[ $(readlink -f /bin/gtar) == /usr/bin/tar ]]
dnf --noplugins --disablerepo='*' check
python3.11 /recipe/validate-cpio-security.py /usr/bin/cpio
[[ $(gawk -M 'BEGIN{printf "%.0f\n",2^100}') == 1267650600228229401496703205376 ]]
gawk -l filefuncs 'BEGIN{if(stat(".",s)!=0 || s["type"]!="directory")exit 1}'
work=$(mktemp -d)
printf 'alpha\n' > "$work/file"
chmod 0640 "$work/file"
ln -s file "$work/link"
sed -i --follow-symlinks 's/alpha/beta/' "$work/link"
[[ -L $work/link && $(stat -c %a "$work/file") == 640 ]]
grep -qx beta "$work/file"
tar -cf "$work/archive.tar" -C "$work" file link
mkdir "$work/restore"
tar -xf "$work/archive.tar" -C "$work/restore"
cmp "$work/file" "$work/restore/file"
[[ $(readlink "$work/restore/link") == file ]]
echo LEGACY_PATH_INSTALL_AND_RUNTIME_PASSED
