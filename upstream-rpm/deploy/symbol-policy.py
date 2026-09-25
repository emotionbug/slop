"""Conservative transaction-specific interpretation of the raw ELF audit.

Never clears unknown imports, replaced providers, versioned imports, COPY data,
unreadable ELF files or uncovered directories. Static evidence is not a proof of
running-process, environment, dlopen or future-plugin compatibility.
"""
import importlib.util
import os
from pathlib import Path
import stat

SPEC = importlib.util.spec_from_file_location('symbol_details', str(
    Path(__file__).with_name('diagnose-symbol-audit.py')))
DETAILS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DETAILS)


def still_dangling(item):
    if item.get('kind') != 'broken_symlink':
        return False
    try:
        if not stat.S_ISLNK(os.lstat(item['path']).st_mode):
            return False
        os.stat(item['path'])
    except FileNotFoundError:
        # lstat itself must succeed: a missing ordinary file is not a dangling link.
        return os.path.islink(item['path'])
    except OSError:
        return False
    return False


def classify(audit, removals, incoming_files, outgoing_flags, outgoing_owners):
    if audit.get('audit_version') != 3:
        raise ValueError('Unsupported raw audit version')
    changed = set(incoming_files) | set(outgoing_flags)
    changed_real = {os.path.realpath(p) for p in changed}
    retired = {p for p, flags in outgoing_flags.items()
               if p not in incoming_files and not flags & (1 | 64)}  # config or ghost
    symbols = {s for m in audit['direct_import_matches'] for s in m['symbols']}
    cache = None
    inspected = {}

    def inspect(path):
        path = os.path.realpath(path)
        if path not in inspected:
            inspected[path] = DETAILS.elf_details(path, symbols)
        return inspected[path]

    def retired_consumer(match):
        # Record every inode alias so an unowned hard link is not accidentally cleared.
        paths = {os.path.realpath(p) for p in match.get('aliases', [match['path']])}
        if not paths or not paths.issubset(retired):
            return None
        for path in paths:
            info = inspect(path)
            owners = set(info['rpm_owner']['packages'])
            if info.get('inspection_error') or not owners or not owners.issubset(outgoing_owners):
                return None
        return {'reason': 'consumer_file_removed_by_same_transaction', 'paths': sorted(paths)}

    def unaffected_shared_name(match):
        nonlocal cache
        wanted = set(match['symbols'])
        # Only the reviewed, common BSD string helpers removed from libmagic qualify.
        if not wanted or not wanted.issubset({'strlcpy', 'strlcat'}):
            return None
        for symbol in wanted:
            affected = {item['library'] for item in removals['libraries']
                        if symbol in item['scan_symbols']}
            if affected != {'/usr/lib64/libmagic.so.1'}:
                return None
        consumer = inspect(match['path'])
        if consumer.get('inspection_error') or consumer.get('search_paths') or consumer.get('copy_relocations'):
            return None
        imports = [s for s in consumer.get('target_symbols', []) if not s['defined']]
        if not all(any(s['name'] == name and s['binding'] == 'GLOBAL' for s in imports)
                   for name in wanted):
            return None
        if any(os.environ.get(key) for key in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT')):
            return None
        preload = Path('/etc/ld.so.preload')
        if preload.exists() and any(line.split('#', 1)[0].strip()
                                    for line in preload.read_text().splitlines()):
            return None
        if cache is None:
            cache = DETAILS.cached_libraries()
        providers = {}
        for needed in consumer.get('needed', []):
            paths, unresolved = DETAILS.dependency_candidates(consumer, needed, cache)
            if unresolved:
                continue
            candidates = [inspect(p) for p in paths]
            if any(c.get('inspection_error') for c in candidates):
                continue
            candidates = [c for c in candidates if c.get('class') == consumer.get('class')
                          and c.get('machine') == consumer.get('machine')]
            # Ambiguous architecture-compatible paths are not treated as binding proof.
            if len(candidates) != 1:
                continue
            provider = candidates[0]
            if provider['resolved_path'] in changed_real or any(p in changed for p in paths):
                continue
            if provider.get('soname') != needed or not provider['rpm_owner']['packages']:
                continue
            if set(provider['rpm_owner']['packages']) & outgoing_owners:
                continue
            for symbol in provider.get('target_symbols', []):
                if (symbol['name'] in wanted and symbol['defined'] and
                        symbol['binding'] == 'GLOBAL' and symbol['visibility'] == 'DEFAULT'):
                    providers[symbol['name']] = {'needed': needed, 'path': provider['resolved_path'],
                                               'owner': provider['rpm_owner']['packages']}
        if set(providers) != wanted:
            return None
        return {'reason': 'reviewed_shared_name_has_unchanged_direct_provider', 'providers': providers}

    accepted, blocking = [], []
    for match in audit['direct_import_matches']:
        evidence = retired_consumer(match) or unaffected_shared_name(match)
        if evidence:
            accepted.append(dict(match=match, evidence=evidence))
        else:
            blocking.append(match)
    dangling = [item for item in audit['errors'] if still_dangling(item)]
    errors = [item for item in audit['errors'] if item not in dangling]
    outside = audit['directory_symlinks_outside_roots']
    return {'policy_version': 1, 'accepted_matches': accepted, 'blocking_matches': blocking,
            'preexisting_dangling_links': dangling, 'blocking_errors': errors,
            'uncovered_directory_links': outside,
            'allow_transaction': not (blocking or errors or outside),
            'limits': 'Static imports within scanned roots only. Dangling links are existing defects, '
                      'not repaired or declared healthy. Running processes, dlopen, environment, '
                      'future plugins and application compatibility remain outside this check.'}
