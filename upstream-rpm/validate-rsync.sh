#!/usr/bin/env bash
# Disposable UBI 8 container only. Never run this test on the target server.
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || { echo 'Container required' >&2; exit 2; }
dnf -y --disableplugin=subscription-manager --setopt=install_weak_deps=False install rsync diffutils
cp /usr/bin/rsync /tmp/rsync-before
dnf -y --disableplugin=subscription-manager --setopt=install_weak_deps=False \
  --setopt=localpkg_gpgcheck=False install /rpms/rsync-3.5.1-1.linuxoss.el8.x86_64.rpm
dnf --disableplugin=subscription-manager check
/usr/bin/rsync --version
/tmp/rsync-before --version
work=$(mktemp -d /tmp/rsync-runtime.XXXXXX)
mkdir -p "$work/source/sub" "$work/local" "$work/pull" "$work/push"
printf 'sample data\n' > "$work/source/sub/file"
ln -s sub/file "$work/source/link"
ln "$work/source/sub/file" "$work/source/hardlink"
cat > "$work/local-shell" <<'EOF'
#!/bin/bash
shift
exec "$@"
EOF
chmod 0755 "$work/local-shell"
# Actual rsync protocol over a local pipe; this does not test SSH/authentication.
rsync -aH "$work/source/" "$work/local/"
rsync -aH -e "$work/local-shell" --rsync-path=/tmp/rsync-before \
  "localhost:$work/source/" "$work/pull/"
rsync -aH -e "$work/local-shell" --rsync-path=/tmp/rsync-before \
  "$work/source/" "localhost:$work/push/"
for mode in local pull push; do
  diff -r "$work/source" "$work/$mode"
  [[ $(readlink "$work/$mode/link") == sub/file ]]
  [[ $(stat -c %i "$work/$mode/sub/file") == "$(stat -c %i "$work/$mode/hardlink")" ]]
  echo "PASS: $mode content/symlink/hardlink"
done
rpm -q rsync
echo 'UBI_INSTALL_DNF_CHECK_AND_OLD_PEER_PROTOCOL_OK'
