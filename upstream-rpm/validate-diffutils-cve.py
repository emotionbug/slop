#!/usr/bin/env python3
"""Bounded diff3 rejection checks for CVE-2026-53910 line-number handling."""
import pathlib
import resource
import subprocess
import sys
import tempfile

binary=sys.argv[1] if len(sys.argv)>1 else '/usr/bin/diff3'
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
with tempfile.TemporaryDirectory(prefix='diff3-line-range-') as dirname:
    root=pathlib.Path(dirname)
    for name in ('a','b','c'):(root/name).write_text('ordinary input\n')
    for index,number in enumerate(('18446744073709551616','4611686018427387904','9999999999999999999999999999999999999999')):
        program=root/('diff-program-'+str(index))
        program.write_text('#!/bin/sh\nprintf "%s\\n" "'+number+'a1" "> x"\nexit 1\n')
        program.chmod(0o755)
        result=subprocess.run([binary,'--diff-program='+str(program),str(root/'a'),str(root/'b'),str(root/'c')],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8,preexec_fn=limits,universal_newlines=True)
        if result.returncode!=2 or not any(message in result.stderr for message in ('invalid diff format','diff failed:')):
            raise SystemExit('Unexpected rejection for '+number+': status='+str(result.returncode)+' '+result.stderr[:400])
        print('DIFF3_OVERSIZED_LINE_REJECTED',number)
print('DIFFUTILS_CVE_2026_53910_BOUNDED_REJECTION_CHECKS_PASSED')
