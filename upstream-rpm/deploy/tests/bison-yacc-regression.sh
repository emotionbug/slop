#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
trap 'cp -a /var/log/linuxoss-install/. /work/validation/ 2>/dev/null || true' EXIT
rpm -q bison byacc | tee /work/validation/reference-versions.txt
rpm -qf /usr/bin/yacc /usr/share/man/man1/yacc.1.gz
sha256sum /usr/bin/yacc /usr/share/man/man1/yacc.1.gz > /work/validation/yacc-before.sha256
rpm -qa | sort > /work/validation/packages-before.txt
if dnf --noplugins --disablerepo='*' --setopt=localpkg_gpgcheck=False \
    --setopt=tsflags=test -y install /old/rpms/bison-3.8.2-3.linuxoss.el8.x86_64.rpm \
    > /work/validation/old-bison-conflict.log 2>&1; then
    echo 'Old Bison unexpectedly passed the conflict test' >&2; exit 2
fi
grep -q '/usr/bin/yacc.*conflicts' /work/validation/old-bison-conflict.log
grep -q '/usr/share/man/man1/yacc.1.gz.*conflicts' /work/validation/old-bison-conflict.log
rpm -qa | sort > /work/validation/packages-after-conflict.txt
cmp /work/validation/packages-before.txt /work/validation/packages-after-conflict.txt
bash /work/install-kit/install.sh apply > /work/validation/apply.log 2>&1
sha256sum -c /work/validation/yacc-before.sha256
[[ $(rpm -qf --qf '%{NAME}' /usr/bin/yacc) == byacc ]]
[[ $(rpm -q --qf '%{RELEASE}' bison) == 4.linuxoss.el8 ]]
dnf --noplugins --disablerepo='*' check
python3.11 /recipe/validate-bison-security.py /usr/bin/bison
testdir=$(mktemp -d)
printf '%%%%\nstart: ;\n%%%%\n' > "$testdir/test.y"
(cd "$testdir"; bison -y test.y; test -s y.tab.c)
(cd "$testdir"; yacc -b byacc test.y; test -s byacc.tab.c)
[[ -f /usr/lib64/liby.a ]]
rpm -q bison byacc linuxoss-test-legacy-consumer
echo OLD_CONFLICT_REPRODUCED_NEW_BISON_AND_BYACC_COEXIST
