#!/bin/bash
set -euo pipefail
mkdir -p /tmp/linuxoss-soname-fixture
cd /tmp/linuxoss-soname-fixture
printf 'extern unsigned bfd_init(void); int main(void){return bfd_init()==0;}\n' > consumer.c
old=$(find /usr/lib64 -maxdepth 1 -name 'libbfd-*.so' -type f | head -n1)
test -n "$old"
gcc consumer.c "$old" -o consumer
python=/usr/libexec/platform-python
"$python" - "$old" <<'PY'
import json,sys,os
json.dump(dict(libraries=[],removed_sonames=[os.path.basename(sys.argv[1])]),open('removed.json','w'))
PY
rc=0
"$python" /recipe/check-removed-symbol-users.py --only-roots /tmp/linuxoss-soname-fixture --symbols-file removed.json > /next/runtime-validation/soname-fixture.json || rc=$?
test "$rc" == 1
"$python" - <<'PY'
import json
x=json.load(open('/next/runtime-validation/soname-fixture.json'))
assert len(x['direct_import_matches'])==1,x
assert x['direct_import_matches'][0]['removed_needed'],x
assert not x['errors'],x
print('UNOWNED_REMOVED_SONAME_CONSUMER_DETECTED')
PY
"$python" /recipe/deploy/tests/test_symbol_policy.py
