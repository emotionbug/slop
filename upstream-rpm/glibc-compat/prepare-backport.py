#!/usr/bin/env python3
"""Port official 2026 glibc fixes onto the fully patched EL8 .40 source tree."""
import argparse
import difflib
from pathlib import Path
import subprocess


WORDEXP_FILES = ['posix/wordexp.c', 'posix/Makefile', 'posix/tst-wordexp-append.c',
                 'posix/tst-wordexp-tilde.c', 'posix/tst-wordexp-tilde.root/etc/group',
                 'posix/tst-wordexp-tilde.root/etc/passwd',
                 'posix/tst-wordexp-tilde.root/etc/nsswitch.conf']


def register_tests(path, text):
    original = path.read_text()
    anchor = 'include ../Rules\n'
    if original.count(anchor) != 1:
        raise ValueError('Expected a single Rules inclusion: ' + str(path))
    path.write_text(original.replace(anchor, text + '\n' + anchor))


def wordexp_fixes(source, patches):
    for commit in ('07c24f35392b727e6100d33edfdf811a6c68c218',
                   'e2cefe16c37a617df9f11407cb00a272a6098823'):
        text = (patches / (commit + '.patch')).read_text(encoding='utf-8-sig')
        text = ''.join('diff --git ' + chunk for chunk in text.split('diff --git ')[1:]
                       if chunk.splitlines()[0].split()[0] != 'a/posix/Makefile')
        subprocess.run(['patch', '--batch', '-p1'], input=text, universal_newlines=True,
                       cwd=source, check=True)
    register_tests(source / 'posix/Makefile', '# Official CVE-2026-6368/6791 regression tests.\n'
                   'tests += tst-wordexp-append\ntests-container += tst-wordexp-tilde\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--references', type=Path, required=True)
    p.add_argument('--patches', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--wordexp-only', action='store_true',
                   help='Prepare the supplemental patch in a separate source copy')
    a = p.parse_args()
    names = ['libio/fileops.c', 'libio/Makefile', 'libio/tst-fopen-ccs-empty.c',
             'misc/tsearch.c', 'iconvdata/shift_jisx0213.c', 'iconvdata/euc-jisx0213.c',
             'resolv/resolv_conf.c', 'resolv/tst-resolv-res_init-skeleton.c',
             'elf/dl-load.c', 'elf/dl-path-normalize.h', 'elf/tst-dl-path-normalize.c', 'elf/Makefile',
             'support/next_to_fault.c', 'support/next_to_fault.h']
    names = WORDEXP_FILES if a.wordexp_only else names + WORDEXP_FILES
    original = {n: (a.source / n).read_text() if (a.source / n).exists() else '' for n in names}
    if a.wordexp_only:
        wordexp_fixes(a.source, a.patches)
        write_diff(a.output, a.source, original)
        return
    def patch(commit, selected=None):
        text = (a.patches / (commit + '.patch')).read_text()
        if selected:
            text = ''.join('diff --git ' + chunk for chunk in text.split('diff --git ')[1:]
                           if chunk.splitlines()[0].split()[0][2:] in selected)
        subprocess.run(['patch', '--batch', '-p1'], input=text, universal_newlines=True, cwd=a.source, check=True)
    for commit in ('9765a538ebf8661a6e5578e01e35a3dd30db7eb4', 'e2789c46e3bfdcd67a82bea9946b315c179e83d3',
                   '68d94bbe50b7577d48998107d632ef3a0df050e3', '4dafa087ff5fe7df45bd37dc727e988da6b8c935'):
        patch(commit)
    patch('cca93e5d88d3d4ed073c03100467696f652269e7', {'libio/tst-fopen-ccs-empty.c'})
    register_tests(a.source / 'libio/Makefile', '# CVE-2026-18374 upstream regression.\ntests += tst-fopen-ccs-empty\n')
    patch('506ea57086bfb9ce3daff1c14246a1cb532aba0a', {'resolv/resolv_conf.c'})
    dns_patch = (a.patches / '506ea57086bfb9ce3daff1c14246a1cb532aba0a.patch').read_text().split('diff --git a/resolv/tst-resolv-res_init-skeleton.c')[1]
    additions = '\n'.join(l[1:] for l in dns_patch.splitlines() if l.startswith('+') and not l.startswith('+++')) + '\n'
    path = a.source / 'resolv/tst-resolv-res_init-skeleton.c'
    text = path.read_text()
    marker = 'struct test_case test_cases[] =\n  {\n'
    if text.count(marker) != 1:
        raise ValueError('DNS test table anchor changed')
    path.write_text(text.replace(marker, marker + additions))

    # Port the exact upstream normalization/check, adjusting only the old
    # include location and the absence of dl_scratch_buffer in EL8.
    path = a.source / 'elf/dl-load.c'
    text = path.read_text()
    before = text.index('static bool\nis_trusted_path_normalize')
    end = text.index('\n}\n', before) + 3
    newer = (a.references / 'elf/dl-load.c').read_text()
    start2 = newer.index('static bool\npath_is_trusted')
    end2 = newer.index('\n}\n', start2) + 3
    text = text[:before] + newer[start2:end2] + text[end:]
    text = text.replace('#include <dl-load.h>', '#include <dl-load.h>\n#include <dl-path-normalize.h>')
    path.write_text(text)
    raw = (a.patches / 'ed0c137b97eb940b4b64981e84ed806d3276edd9.patch').read_text()
    dl_chunk = raw.split('diff --git a/elf/dl-load.c b/elf/dl-load.c\n')[1].split('diff --git ')[0]
    hunk = dl_chunk[dl_chunk.index('@@ -335,'):]
    subprocess.run(['patch', '--batch', '-p1'], cwd=a.source, universal_newlines=True, check=True,
                   input='--- a/elf/dl-load.c\n+++ b/elf/dl-load.c\n' + hunk)
    for name in ('elf/dl-path-normalize.h', 'elf/tst-dl-path-normalize.c',
                 'support/next_to_fault.c', 'support/next_to_fault.h'):
        (a.source / name).write_bytes((a.references / name).read_bytes())
    register_tests(a.source / 'elf/Makefile', '# CVE-2026-86805/95818 in-place normalization boundary tests.\ntests-internal += tst-dl-path-normalize\n')
    wordexp_fixes(a.source, a.patches)
    write_diff(a.output, a.source, original)


def write_diff(output, source, original):
    diff = ''.join(''.join(difflib.unified_diff(original[n].splitlines(True), (source / n).read_text().splitlines(True),
                                              fromfile='a/' + n if original[n] else '/dev/null', tofile='b/' + n)) for n in original)
    output.write_text(diff)
    print('Backport written:', output)


if __name__ == '__main__':
    main()
