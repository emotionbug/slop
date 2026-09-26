#!/usr/libexec/platform-python
"""Read-only driver metadata for kernel migration; JSON on stdout, no uploads."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

MODULES = ('gc_enforcement', 'dsa_filter', 'dsa_filter_hook')
PACKAGES = ('gc-guest-agent', 'ds_agent')
FIELDS = {'filename', 'name', 'version', 'srcversion', 'vermagic', 'license',
          'description', 'depends', 'intree', 'signer'}


def query(args):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=30)
        return {'exit_code': p.returncode, 'stdout': p.stdout[:65536],
                'stderr': p.stderr[:2048], 'truncated': len(p.stdout) > 65536}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'exit_code': None, 'stdout': '', 'stderr': str(exc), 'truncated': False}


def metadata(result):
    out = {}
    for line in result['stdout'].splitlines():
        key, sep, value = line.partition(':')
        if sep and key in FIELDS:
            out[key] = value.strip()
    return out


def module_name(path):
    return re.sub(r'\.ko(?:\.(?:xz|gz|zst))?$', '', Path(path).name).replace('-', '_')


def collect(extra_roots=()):
    running = os.uname().release
    report = {'schema_version': 1, 'running_kernel': running,
              'target_kernel': '7.2.7-linuxoss+', 'read_only': True,
              'packages': {}, 'modules': {}, 'source_file_candidates': [],
              'search_roots': [], 'search_errors': [], 'search_truncated': False,
              'limitations': ['File metadata does not prove vendor support or runtime compatibility.',
                             'A loaded module may differ from the file currently on disk.',
                             'GPL metadata does not establish that matching source is available.',
                             'Source candidates are names only, not verified complete build sources.']}
    report['kernel_packages'] = query(['rpm', '-q', '--qf',
        '%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\t%{VENDOR}\n',
        'kernel', 'kernel-core', 'kernel-modules', 'kernel-devel'])
    package_files = []
    for package in PACKAGES:
        report['packages'][package] = query(['rpm', '-q', '--qf',
            '%{NAME}\t%{VERSION}-%{RELEASE}\t%{VENDOR}\t%{LICENSE}\t%{SOURCERPM}\n', package])
        files = query(['rpm', '-ql', package])
        # Do not include arbitrary package config contents or full package listings.
        package_files.extend(p for p in files['stdout'].splitlines() if p.startswith('/'))
        if files['exit_code'] or files['truncated']:
            report['search_errors'].append({'package_file_list': package,
                'exit_code': files['exit_code'], 'stderr': files['stderr'],
                'truncated': files['truncated']})

    candidates = {name: set() for name in MODULES}
    for name in MODULES:
        sysdir = Path('/sys/module') / name
        current = {'loaded': sysdir.is_dir(), 'loaded_metadata': {}, 'files': []}
        for field in ('version', 'srcversion', 'taint'):
            try:
                current['loaded_metadata'][field] = (sysdir / field).read_text().strip()
            except OSError:
                pass
        named = query(['modinfo', name])
        current['modinfo_by_name'] = {'exit_code': named['exit_code'],
                                    'metadata': metadata(named), 'stderr': named['stderr']}
        filename = metadata(named).get('filename')
        if filename and filename.startswith('/'):
            candidates[name].add(filename)
        report['modules'][name] = current

    roots = [Path('/lib/modules') / running, Path('/opt/ds_agent'),
             Path('/var/opt/ds_agent'), Path('/usr/lib/guardicore'),
             Path('/opt/guardicore'), Path('/var/lib/dkms')] + [Path(p) for p in extra_roots]
    # Use RPM file locations to discover product directories without reading service configs.
    for path in package_files:
        parts = Path(path).parts
        if len(parts) > 2 and parts[1] == 'opt':
            roots.append(Path('/', 'opt', parts[2]))
    seen_files = set()
    source_names = set()

    def consider(path):
        name = module_name(path)
        if name in candidates and re.search(r'\.ko(?:\.(?:xz|gz|zst))?$', str(path)):
            candidates[name].add(str(path))
        elif Path(path).suffix in ('.c', '.h') or Path(path).name in ('Makefile', 'Kbuild', 'dkms.conf'):
            if len(source_names) < 200:
                source_names.add(str(path))
            else:
                report['search_truncated'] = True

    for path in package_files:
        consider(path)
    for root in sorted(set(roots), key=str):
        if not root.is_dir():
            continue
        report['search_roots'].append(str(root))
        for directory, dirs, files in os.walk(str(root), followlinks=False,
                onerror=lambda exc: report['search_errors'].append(str(exc))):
            if len(Path(directory).relative_to(root).parts) >= 8:
                if dirs:
                    report['search_truncated'] = True
                dirs[:] = []
            # Only names are examined. Key/config/log contents are never opened.
            for filename in files:
                path = str(Path(directory) / filename)
                if path in seen_files:
                    continue
                seen_files.add(path)
                consider(path)
            if len(seen_files) > 100000:
                report['search_truncated'] = True
                break
        if len(seen_files) > 100000:
            break
    report['source_file_candidates'] = sorted(source_names)

    for name, paths in candidates.items():
        current = report['modules'][name]
        current['candidate_paths'] = sorted(paths)
        distinct = set()
        for path in sorted(paths, key=lambda p: (running not in p, p)):
            actual = os.path.realpath(path)
            if actual in distinct:
                continue
            distinct.add(actual)
            if len(distinct) > 12:
                report['search_truncated'] = True
                break
            info = query(['modinfo', path])
            item = {'path': path, 'resolved_path': actual, 'metadata': metadata(info),
                    'modinfo_exit_code': info['exit_code'], 'modinfo_error': info['stderr']}
            try:
                digest = hashlib.sha256()
                with open(path, 'rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
                item['sha256'] = digest.hexdigest()
            except OSError as exc:
                item['read_error'] = str(exc)
            # This query dumps imported CRCs and exits; it never loads/unloads a module.
            item['imported_symbol_versions'] = query(['modprobe', '--show-modversions', path])
            disk_src = item['metadata'].get('srcversion')
            loaded_src = current['loaded_metadata'].get('srcversion')
            item['loaded_srcversion_matches'] = disk_src == loaded_src if disk_src and loaded_src else None
            current['files'].append(item)
    return report


if __name__ == '__main__':
    if any(not os.path.isabs(p) or not os.path.isdir(p) for p in sys.argv[1:]):
        sys.exit('Optional arguments must be existing absolute product directories.')
    print(json.dumps(collect(sys.argv[1:]), indent=2, ensure_ascii=True))
