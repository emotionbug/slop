#!/usr/bin/env bash
# Install, stage exact server modules, build initramfs and arm one-shot boot.
set -Eeuo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
bash "$here/stage-kernel.sh" apply
/usr/libexec/platform-python "$here/stage-reviewed-modules.py" apply
bash "$here/prepare-ssh-boot.sh" apply
echo 'Installation and one-shot boot preparation completed. The server was not rebooted.'
