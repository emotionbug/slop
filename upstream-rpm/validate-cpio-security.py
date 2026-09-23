#!/usr/bin/env python3
"""Bounded local CVE checks; run inside a disposable unprivileged container."""
import io
import os
import pathlib
import pty
import resource
import select
import subprocess
import sys
import tarfile
import tempfile
import time

if not (pathlib.Path('/run/.containerenv').exists() or pathlib.Path('/.dockerenv').exists()):
    raise SystemExit('Disposable container required')
program=str(pathlib.Path(sys.argv[1]).resolve())
expect_vulnerable='--expect-vulnerable' in sys.argv[2:]
with tempfile.TemporaryDirectory(prefix='cpio-security.') as temporary:
    root=pathlib.Path(temporary); outside=root/'outside.txt';outside.write_bytes(b'unchanged')
    target=root/'extract';target.mkdir()
    data=io.BytesIO()
    with tarfile.open(fileobj=data,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        member=tarfile.TarInfo('escape');member.type=tarfile.LNKTYPE;member.linkname=str(outside)
        archive.addfile(member)
    result=subprocess.run([program,'-idm','--no-absolute-filenames'],input=data.getvalue(),cwd=str(target),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    linked=(target/'escape').exists() and os.path.samefile(str(target/'escape'),str(outside))
    assert linked == expect_vulnerable, ('hard-link escape',result.returncode,result.stderr)
    assert outside.read_bytes()==b'unchanged'
    print('CPIO_HARDLINK_ESCAPE', 'reproduced-original' if linked else 'blocked-patched')

    # Quoting is intentionally applied to terminal listings. Pipes preserve
    # literal file names, so use a PTY and inspect bytes instead of rendering.
    weird='entry\nFORGED\x1b[31m'
    (root/weird).write_bytes(b'fixture')
    archive=subprocess.run([program,'-o','-H','newc','--null'],cwd=str(root),input=weird.encode()+b'\0',stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=10).stdout
    master,slave=pty.openpty()
    process=subprocess.Popen([program,'-it'],stdin=subprocess.PIPE,stdout=slave,stderr=subprocess.PIPE,cwd=str(root))
    os.close(slave);process.stdin.write(archive);process.stdin.close()
    output=bytearray();deadline=time.monotonic()+10
    try:
        while time.monotonic()<deadline:
            ready,_,_=select.select([master],[],[],0.1)
            if ready:
                try:chunk=os.read(master,65536)
                except OSError:break
                if not chunk:break
                output.extend(chunk)
                assert len(output)<65536
            elif process.poll() is not None:break
        process.wait(timeout=2)
    finally:
        if process.poll() is None:process.kill();process.wait()
        os.close(master)
    assert process.returncode==0
    terminal_escape=b'\x1b[31m' in output
    assert terminal_escape==expect_vulnerable, repr(bytes(output))
    print('CPIO_TERMINAL_ESCAPE', 'reproduced-original' if terminal_escape else 'escaped-patched')

    def limits():
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_STACK,(1024*1024,1024*1024))
        resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
    # One overlong component, so this cannot create a deep directory tree.
    # The terminal slash causes make_path to process the archive pathname.
    name=b'x'*(2*1024*1024)+b'/file\0'
    fields=[1,0o100600,os.getuid(),os.getgid(),1,0,0,0,0,0,0,len(name),0]
    entry=b'070701'+b''.join(('%08x'%v).encode() for v in fields)+name
    entry+=b'\0'*((-len(entry))%4)
    longdir=root/'longpath';longdir.mkdir()
    # Diagnostics contain the long name; discard them to keep logs bounded.
    result=subprocess.run([program,'-idm','--no-absolute-filenames'],input=entry,
        cwd=str(longdir),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        timeout=10,preexec_fn=limits)
    crashed=result.returncode<0
    assert crashed==expect_vulnerable,('long-path status',result.returncode)
    if not expect_vulnerable:
        assert result.returncode>0,('expected a clean rejection',result.returncode)
    print('CPIO_LONG_PATH_STACK', 'reproduced-original' if crashed else 'clean-error-patched')
