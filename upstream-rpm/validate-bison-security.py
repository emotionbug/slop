#!/usr/bin/env python3
"""Local benign regression checks for grammar-controlled program/output paths."""
import os
import pathlib
import subprocess
import sys
import tempfile

if not (pathlib.Path('/run/.containerenv').exists() or pathlib.Path('/.dockerenv').exists()):
    raise SystemExit('Disposable container required')
program=str(pathlib.Path(sys.argv[1]).resolve())
expect_vulnerable='--expect-vulnerable' in sys.argv[2:]
with tempfile.TemporaryDirectory(prefix='bison-security.') as temporary:
    root=pathlib.Path(temporary);marker=root/'unexpected-program-ran'
    helper=root/'benign-transform-helper'
    helper.write_text('#!/bin/sh\nprintf test > "'+str(marker)+'"\n')
    helper.chmod(0o700)
    grammar=root/'program.y'
    grammar.write_text('%define tool.xsltproc "'+str(helper)+'"\n%%\nstart: ;\n%%\n')
    result=subprocess.run([program,'--html',str(grammar)],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    assert marker.exists()==expect_vulnerable, (result.returncode,result.stderr)
    print('BISON_GRAMMAR_PROGRAM', 'reproduced-original' if marker.exists() else 'blocked-patched')
    for directive,suffix in [('output','.c'),('header','.h')]:
        destination=root/('outside-'+directive+suffix);destination.write_bytes(b'KEEP')
        nested=root/directive;nested.mkdir()
        grammar=nested/'input.y'
        grammar.write_text('%'+directive+' "../'+destination.name+'"\n%%\nstart: ;\n%%\n')
        result=subprocess.run([program,str(grammar)],cwd=str(nested),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        changed=destination.read_bytes()!=b'KEEP'
        assert changed==expect_vulnerable,(directive,result.returncode,result.stderr)
        print('BISON_GRAMMAR_'+directive.upper(), 'reproduced-original' if changed else 'blocked-patched')
