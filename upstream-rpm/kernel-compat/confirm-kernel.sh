#!/usr/bin/env bash
# Confirm the trial kernel after signed module, SSH, network, Java and Tomcat checks.
set -Eeuo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
manifest=$here/server-profile-module-manifest-final.json
target=$(/usr/libexec/platform-python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["release"])' "$manifest")
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
[[ $(uname -r) == "$target" ]] || { echo "Not running $target" >&2; exit 2; }
systemctl is-active --quiet sshd.service
systemctl is-active --quiet network-online.target
ip route show default | grep -q .
if [[ -s /var/lib/linuxoss-kernel-compat/local-module-profile.json ]]; then
  /usr/libexec/platform-python "$here/stage-reviewed-modules.py" --local-profile-check >/dev/null
else
  /usr/libexec/platform-python "$here/stage-reviewed-modules.py" check >/dev/null
fi

java_pattern=${LINUXOSS_JAVA_PATTERN:-'[j]ava'}
tomcat_pattern=${LINUXOSS_TOMCAT_PATTERN:-'[o]rg.apache.catalina.startup.Bootstrap|[c]atalina'}
pgrep -af -- "$java_pattern" >/dev/null
pgrep -af -- "$tomcat_pattern" >/dev/null

install -d -m 0755 /run/linuxoss-kernel-compat
printf 'healthy\n' > /run/linuxoss-kernel-compat/agent-health.ok
bash "$here/server-profile-ssh-deploy.sh" --commit
