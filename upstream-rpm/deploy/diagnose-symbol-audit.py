#!/usr/libexec/platform-python
"""Read-only details for an existing installer audit; never approves installation.

Uses readelf, rpm queries and ldconfig -p. Does not run inspected programs, ldd,
package scripts or network requests. Output contains local paths/package names;
keep it private. Python 3.6 compatible.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys


def run(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, errors='replace', timeout=30,
                          env=dict(os.environ, LC_ALL='C'))
    return proc.returncode, proc.stdout, proc.stderr.strip()[:500]


def owners(path):
    code, output, error = run(['rpm', '-qf', '--qf',
                              '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n',
                              '--', str(path)])
    return {'packages': output.splitlines() if code == 0 else [],
            'query_error': error or output.strip() if code else None}


def path_info(path):
    path = str(path)
    result = {'path': path, 'resolved_path': os.path.realpath(path),
              'exists': os.path.exists(path), 'is_symlink': os.path.islink(path),
              'rpm_owner': owners(path)}
    if result['is_symlink']:
        result['link_target'] = os.readlink(path)
    if result['resolved_path'] != path:
        result['resolved_rpm_owner'] = owners(result['resolved_path'])
    return result


def elf_details(path, symbols):
    path = str(path)
    result = path_info(path)
    try:
        if not stat.S_ISREG(os.stat(path).st_mode):
            raise ValueError('Not a regular file')
        with open(path, 'rb') as stream:
            if stream.read(4) != b'\x7fELF':
                raise ValueError('Not an ELF file')
        code, output, error = run(['readelf', '--file-header', '--dynamic',
                                   '--dyn-syms', '--relocs', '--wide', '--', path])
        if code:
            raise ValueError(error or 'readelf failed')
        result.update(needed=[], search_paths=[], target_symbols=[], copy_relocations=[])
        for line in output.splitlines():
            header = re.match(r'\s*(Class|Machine):\s*(.+)', line)
            if header:
                result[header.group(1).lower()] = header.group(2).strip()
            tag = re.search(r'\((NEEDED|SONAME|RPATH|RUNPATH)\).*\[(.*?)\]', line)
            if tag:
                kind, value = tag.groups()
                if kind == 'NEEDED':
                    result['needed'].append(value)
                elif kind == 'SONAME':
                    result['soname'] = value
                else:
                    result['search_paths'].append({'kind': kind, 'value': value})
            parts = line.split()
            if len(parts) >= 8 and parts[0].endswith(':') and parts[0][:-1].isdigit():
                if parts[7].split('@')[0] in symbols:
                    result['target_symbols'].append({'name': parts[7], 'binding': parts[4],
                        'visibility': parts[5], 'index': parts[6],
                        'defined': parts[6] != 'UND'})
            if len(parts) >= 5 and parts[2].endswith('_COPY'):
                if parts[4].split('@')[0] in symbols:
                    result['copy_relocations'].append(parts[4])
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        result['inspection_error'] = str(error)
    return result


def cached_libraries():
    command = shutil.which('ldconfig') or '/sbin/ldconfig'
    code, output, error = run([command, '-p'])
    if code:
        raise RuntimeError('Cannot read ldconfig cache: ' + error)
    libraries = {}
    for line in output.splitlines():
        match = re.match(r'\s*(\S+)\s+\([^)]*\)\s+=>\s+(/.+)', line)
        if match:
            libraries.setdefault(match.group(1), []).append(match.group(2))
    return libraries


def dependency_candidates(consumer, soname, cache):
    # These are inspection candidates, NOT an implementation of loader binding.
    # Do not execute the consumer or trust environment paths as a runtime proof.
    paths = []
    unresolved = []
    if '/' in soname:
        if os.path.isabs(soname):
            paths.append(soname)
        else:
            unresolved.append(soname)
    else:
        origin = os.path.dirname(consumer['resolved_path'])
        for entry in consumer.get('search_paths', []):
            for part in entry['value'].split(':'):
                part = part.replace('${ORIGIN}', origin).replace('$ORIGIN', origin)
                if '$' in part or not os.path.isabs(part):
                    unresolved.append(part)
                else:
                    paths.append(os.path.join(part, soname))
        paths.extend(cache.get(soname, []))
        paths.extend(os.path.join(p, soname) for p in ('/lib64', '/usr/lib64', '/lib', '/usr/lib'))
    unique = {}
    for path in paths:
        if os.path.isfile(path):
            unique.setdefault(os.path.realpath(path), path)
    return list(unique.values()), unresolved


def collect(audit_path):
    audit_path = Path(audit_path).resolve()
    audit = json.loads(audit_path.read_text())
    if audit.get('audit_version') != 3:
        raise ValueError('Expected installer symbol audit version 3')
    matches = audit['direct_import_matches']
    symbols = {symbol for item in matches for symbol in item['symbols']}
    cache = cached_libraries()
    inspected = {}

    def inspect(path):
        key = os.path.realpath(str(path))
        if key not in inspected:
            inspected[key] = elf_details(path, symbols)
        return inspected[key]

    details = []
    for match in matches:
        consumer = dict(inspect(match['path']))
        consumer['audit_path'] = match['path']
        consumer['audit_symbols'] = match['symbols']
        dependencies = []
        for needed in consumer.get('needed', []):
            candidates, unresolved = dependency_candidates(consumer, needed, cache)
            dependencies.append({'needed': needed, 'candidates': [inspect(p) for p in candidates],
                                 'unresolved_search_paths': unresolved})
        consumer['direct_dependency_candidates'] = dependencies
        details.append(consumer)
    debug_prefixes = ('/usr/lib/.build-id/', '/usr/lib/debug/.build-id/')
    errors = audit.get('errors', [])
    debug = [e for e in errors if e.get('kind') == 'broken_symlink'
             and e.get('path', '').startswith(debug_prefixes)]
    other = [dict(original=e, current=path_info(e['path'])) for e in errors if e not in debug]
    outside = [dict(original=e, current=path_info(e['path']))
               for e in audit.get('directory_symlinks_outside_roots', [])]
    context = {}
    removal_definitions = []
    for name in ('transaction.json', 'transaction-symbols.json'):
        path = audit_path.parent / name
        if path.is_file():
            context[name] = json.loads(path.read_text())
    for library in context.get('transaction-symbols.json', {}).get('libraries', []):
        overlap = sorted(symbols.intersection(library.get('scan_symbols', [])))
        if overlap:
            removal_definitions.append({'library': library['library'], 'matching_symbols': overlap,
                                        'current_elf': inspect(library['library'])})
    # Full export lists are unnecessary; retain the actual transaction and matching libraries.
    context.pop('transaction-symbols.json', None)
    return {'diagnostic_version': 1, 'read_only': True, 'audit_source': str(audit_path),
            'original_summary': {'elf_files_scanned': audit.get('elf_files_scanned'),
                'matched_files': len(matches), 'error_kinds': dict(Counter(e.get('kind') for e in errors)),
                'dangling_debug_links': len(debug), 'other_errors': len(other),
                'outside_directory_links': len(outside)},
            'matches': details, 'other_errors': other, 'outside_directory_links': outside,
            'removal_libraries': removal_definitions, 'installer_context': context,
            'limits': 'Static details only. Direct dependency candidates are not resolved runtime bindings. '
                      'Does not model transitive dependencies, preload, dlopen, environment or loaded processes. '
                      'Does not clear or bypass installer checks. No packages/services/configuration are changed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audit', nargs='?', help='Existing symbol-audit.json; defaults to latest installer report')
    args = parser.parse_args()
    for command in ('rpm', 'readelf'):
        if not shutil.which(command):
            parser.error(command + ' is required')
    path = Path(args.audit) if args.audit else None
    if path is None:
        reports = list(Path('/var/log/linuxoss-install').glob('run-*/symbol-audit.json'))
        if not reports:
            parser.error('No installer audit found; provide its path explicitly')
        path = max(reports, key=lambda p: p.stat().st_mtime)
    try:
        result = collect(path)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(2, 'Diagnostic failed: ' + str(error) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
