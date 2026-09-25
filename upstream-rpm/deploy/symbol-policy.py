"""Conservative transaction-specific interpretation of the raw ELF audit.

Requires exact version bindings for reviewed shared names and actual incoming
ELF payloads for replaced consumers. Never clears unknown imports, COPY data,
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


def classify(audit, removals, incoming_files, outgoing_flags, outgoing_owners, incoming_elf=None):
    if audit.get('audit_version') != 3:
        raise ValueError('Unsupported raw audit version')
    changed = set(incoming_files) | set(outgoing_flags)
    changed_real = {os.path.realpath(p) for p in changed}
    retired = {p for p, flags in outgoing_flags.items()
               if p not in incoming_files and not flags & (1 | 64)}  # config or ghost
    symbols = set(audit.get('symbols_checked', [])) | {s for m in audit['direct_import_matches'] for s in m['symbols']}
    incoming_elf = incoming_elf or {}
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

    def unaffected_shared_name(match, consumer=None):
        nonlocal cache
        wanted = set(match['symbols'])
        if match.get('removed_needed') or not wanted:
            return None
        for symbol in wanted:
            affected = {item['library'] for item in removals['libraries']
                        if symbol in item['scan_symbols']}
            allowed = ((symbol in {'strlcpy', 'strlcat'} and affected == {'/usr/lib64/libmagic.so.1'}) or
                       (symbol in {'malloc', 'calloc', 'realloc', 'free', 'mallinfo', 'memalign'} and affected == {'/usr/lib64/libgvpr.so.2'}) or
                       (symbol.startswith('g_cclosure_marshal_') and affected == {'/usr/lib64/libgtk-x11-2.0.so.0'}))
            if not allowed:
                return None
        consumer = consumer or inspect(match['path'])
        if consumer.get('inspection_error') or consumer.get('copy_relocations'):
            return None
        imports = [s for s in consumer.get('target_symbols', []) if not s['defined']]
        if not all(any(s['name'].split('@')[0] == name and s['binding'] == 'GLOBAL' for s in imports)
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
                name = symbol['name'].split('@')[0]
                required = [s['name'] for s in imports if s['name'].split('@')[0] == name]
                # A versioned import must match that exact export version. An
                # unversioned import accepts only an unversioned/default export.
                binding_matches = all((symbol['name'].replace('@@', '@') == req if '@' in req
                                       else '@' not in symbol['name'] or '@@' in symbol['name']) for req in required)
                if (name in wanted and required and binding_matches and symbol['defined'] and
                        symbol['binding'] in ('GLOBAL', 'WEAK') and symbol['visibility'] == 'DEFAULT'):
                    providers[name] = {'needed': needed, 'path': provider['resolved_path'],
                                               'owner': provider['rpm_owner']['packages']}
        if set(providers) != wanted:
            return None
        return {'reason': 'reviewed_shared_name_has_unchanged_direct_provider', 'providers': providers}

    def replaced_consumer(match):
        paths = {os.path.realpath(p) for p in match.get('aliases', [match['path']])}
        # An unowned hard link could retain the old executable after RPM replaces
        # its owned path. Every alias therefore needs transaction ownership.
        if not paths or not paths.issubset(set(outgoing_flags)):
            return None
        replacements = []
        for path in paths:
            old = inspect(path)
            if old.get('inspection_error') or not old['rpm_owner']['packages'] or not set(old['rpm_owner']['packages']).issubset(outgoing_owners):
                return None
            if path in retired:
                continue
            new = incoming_elf.get(path)
            if not new or new.get('inspection_error') or new.get('copy_relocations'):
                return None
            if set(new.get('needed', [])) & set(removals.get('removed_sonames', [])):
                return None
            remaining = {s['name'].split('@')[0] for s in new.get('target_symbols', []) if not s['defined']}
            bundled_providers = {}
            search_dirs = {'/lib', '/lib64', '/usr/lib', '/usr/lib64'}
            for entry in new.get('search_paths', []):
                for part in entry['value'].split(':'):
                    part = part.replace('${ORIGIN}', os.path.dirname(path)).replace('$ORIGIN', os.path.dirname(path))
                    if '$' in part or not os.path.isabs(part):
                        return None
                    search_dirs.add(os.path.normpath(part))
            for needed in new.get('needed', []):
                providers = [p for p in incoming_elf.values() if p.get('soname') == needed
                             and p.get('class') == new.get('class') and p.get('machine') == new.get('machine')
                             and os.path.dirname(p['resolved_path']) in search_dirs and not p.get('inspection_error')]
                if len(providers) != 1:
                    continue
                provider = providers[0]
                for symbol in provider.get('target_symbols', []):
                    name = symbol['name'].split('@')[0]
                    required = [s['name'] for s in new['target_symbols'] if not s['defined'] and s['name'].split('@')[0] == name]
                    if not required or not symbol['defined'] or symbol['binding'] not in ('GLOBAL', 'WEAK') or symbol['visibility'] != 'DEFAULT':
                        continue
                    if all(symbol['name'].replace('@@', '@') == req if '@' in req
                           else '@' not in symbol['name'] or '@@' in symbol['name'] for req in required):
                        bundled_providers[name] = provider['resolved_path']
            remaining -= set(bundled_providers)
            evidence = None
            if remaining:
                evidence = unaffected_shared_name(dict(match, symbols=sorted(remaining), removed_needed=[]), new)
                if not evidence:
                    return None
            replacements.append({'path': path, 'incoming_direct_providers': bundled_providers,
                                 'remaining_import_evidence': evidence})
        return {'reason': 'owned_consumer_replaced_by_audited_incoming_elf', 'replacements': replacements}

    accepted, blocking = [], []
    for match in audit['direct_import_matches']:
        evidence = retired_consumer(match) or replaced_consumer(match) or unaffected_shared_name(match)
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
