#!/usr/libexec/platform-python
"""Use EL8 DNF to upgrade installed names only, with local hard dependencies."""
import hashlib
import importlib.util
import json
import logging
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile

import dnf
import rpm


def fail(message):
    raise RuntimeError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def compare(left, right):
    return rpm.labelCompare((str(left.epoch or 0), left.version, left.release),
                            (str(right.epoch or 0), right.version, right.release))


def same_slot(left, right):
    return left.name == right.name and (left.arch == right.arch or
                                        {left.arch, right.arch} == {'x86_64', 'noarch'})


def inventory():
    return sorted(subprocess.check_output(
        ['rpm', '-qa', '--qf', '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n']
    ).decode().splitlines())


def main():
    mode, folder, output = sys.argv[1:4]
    if mode not in ('check', 'apply') or os.geteuid() != 0:
        fail('Use sudo bash install.sh [check|apply].')
    root, report = Path(folder).resolve(), Path(output).resolve()
    manifest = json.loads((root / 'candidate-manifest.json').read_text())
    if manifest.get('requires_non_fips', False):
        fips = Path('/proc/sys/crypto/fips_enabled')
        if fips.exists() and fips.read_text().strip() != '0':
            fail('This locally built crypto/glibc bundle is not FIPS validated. No RPMs installed.')
    entries = [item for item in manifest['files'] if item['path'].startswith('rpms/')]
    expected = {item['path']: item for item in entries}
    actual = {str(p.relative_to(root)) for p in (root / 'rpms').glob('*.rpm')}
    count = manifest.get('rpm_count', 77)  # Older signed-off bundles used 77.
    if type(count) is not int or count < 1 or len(entries) != count or len(expected) != count or actual != set(expected):
        fail('Expected the exact RPM set and count pinned in candidate-manifest.json.')
    for name, item in expected.items():
        path = root / name
        if path.is_symlink() or path.stat().st_size != item['size'] or digest(path) != item['sha256']:
            fail('RPM checksum mismatch: ' + name)
    before = inventory()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    with dnf.Base() as base:
        base.conf.read()
        base.conf.plugins = False
        base.conf.install_weak_deps = False
        base.conf.clean_requirements_on_remove = False
        base.conf.localpkg_gpgcheck = False  # Locally built unsigned RPMs, pinned hashes above.
        base.conf.best = True
        base.conf.obsoletes = False
        base.conf.keepcache = True
        base.conf.cachedir = str(report / 'dnf-cache')
        base.conf.logdir = str(report)
        base.conf.tsflags = []
        # Do not load any configured repository or subscription plugin.
        base.fill_sack(load_system_repo=True, load_available_repos=False)
        candidates = base.add_remote_rpms([str(root / name) for name in sorted(expected)], strict=True)
        installed = list(base.sack.query().installed())
        skipped, selected = [], []
        for package in candidates:
            old = [p for p in installed if same_slot(p, package)]
            if not old:
                skipped.append({'package': str(package), 'reason': 'not installed; dependency only'})
            elif any(compare(package, p) <= 0 for p in old):
                skipped.append({'package': str(package), 'reason': 'same or newer version installed'})
            else:
                base.package_upgrade(package)
                selected.append(str(package))
        changed = base.resolve(allow_erasing=False)
        incoming = sorted(base.transaction.install_set, key=str) if changed else []
        outgoing = sorted(base.transaction.remove_set, key=str) if changed else []
        plan = {'requested_upgrades': selected, 'install_or_upgrade': [str(p) for p in incoming],
                'replaced_old_versions': [str(p) for p in outgoing], 'skipped': skipped}
        (report / 'transaction.json').write_text(json.dumps(plan, indent=2) + '\n')
        for package in incoming:
            old = [p for p in installed if same_slot(p, package)]
            if any(compare(package, p) < 0 for p in old):
                fail('Downgrade refused: ' + str(package))
            if str(Path(package.localPkg()).resolve()) not in {str(root / n) for n in expected}:
                fail('Non-bundle package refused: ' + str(package))
        for package in outgoing:
            if not any(same_slot(p, package) and compare(p, package) > 0
                       for p in incoming):
                fail('Removal or cross-name replacement refused: ' + str(package))
        print('Upgrade targets: {}; total incoming including dependencies: {}'.format(len(selected), len(incoming)), flush=True)
        for package in incoming:
            action = 'UPGRADE' if any(same_slot(p, package) for p in installed) else 'DEPENDENCY'
            print('{} {}'.format(action, package), flush=True)
        if not changed:
            print('Nothing to do: no applicable upgrades in this candidate subset.', flush=True)
            return
        # Include old paths: a library removed entirely is absent from incoming files.
        changed_files = set()
        incoming_paths = {}
        for package in incoming:
            paths = subprocess.check_output(['rpm', '-qpl', package.localPkg()]).decode().splitlines()
            changed_files.update(paths)
            for path in paths:
                incoming_paths[path] = package.localPkg()
        outgoing_flags, outgoing_owners = {}, set()
        ts = rpm.TransactionSet()
        for package in outgoing:
            headers = [h for h in ts.dbMatch('name', package.name)
                       if h['arch'] == package.arch and h['version'] == package.version
                       and h['release'] == package.release
                       and int(h['epoch'] or 0) == int(package.epoch or 0)]
            if len(headers) != 1:
                fail('Cannot identify outgoing RPM header: ' + str(package))
            header = headers[0]
            outgoing_owners.add('{}\t{}:{}-{}\t{}'.format(package.name, package.epoch or 0,
                package.version, package.release, package.arch))
            for name, flags in zip(header['filenames'], header['fileflags']):
                outgoing_flags[name] = outgoing_flags.get(name, 0) | int(flags)
        symbols = json.loads((root / 'expected-export-removals.json').read_text())
        outgoing_ids = {str(p) for p in outgoing}
        surviving_provides = {str(cap) for p in installed if str(p) not in outgoing_ids for cap in p.provides}
        surviving_provides.update(str(cap) for p in incoming for cap in p.provides)
        removed_caps = {str(cap) for p in outgoing for cap in p.provides} - surviving_provides
        symbols['removed_sonames'] = sorted({m.group(1) for cap in removed_caps
            for m in [re.fullmatch(r'(lib[^/() ]+\.so[^/() ]*)\(\)(?:\(64bit\))?', cap)] if m})
        symbols['libraries'] = [item for item in symbols['libraries']
                               if item['library'] in changed_files or item['library'] in outgoing_flags]
        (report / 'transaction-symbols.json').write_text(json.dumps(symbols))
        audit_file = report / 'symbol-audit.json'
        audit_options = ['--no-default-symbols'] if manifest.get('transaction_symbols_only', False) else []
        extra_roots = sys.argv[4:]
        for directory in ('/usr/src', '/usr/share'):
            if Path(directory).is_dir():
                extra_roots = [directory] + extra_roots
        with audit_file.open('w') as stream:
            result = subprocess.run([sys.executable, str(root / 'check-removed-symbol-users.py'),
                                     '--symbols-file', str(report / 'transaction-symbols.json')] + audit_options + extra_roots, stdout=stream)
        audit = json.loads(audit_file.read_text())
        spec = importlib.util.spec_from_file_location('symbol_policy', str(root / 'symbol-policy.py'))
        policy_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy_module)
        # Inspect actual replacement ELF payloads. The old executable may use a
        # removed interface while its incoming replacement no longer does.
        aliases = {os.path.realpath(p) for match in audit['direct_import_matches']
                   for p in match.get('aliases', [match['path']])}
        replacements = aliases & set(incoming_paths)
        incoming_elf = {}
        with tempfile.TemporaryDirectory(prefix='linuxoss-incoming-elf-') as folder:
            for package_path in sorted({p.localPkg() for p in incoming}):
                child = subprocess.Popen(['rpm2cpio', package_path], stdout=subprocess.PIPE)
                subprocess.run(['cpio', '-idmu', '--quiet', '--no-absolute-filenames'],
                               cwd=folder, stdin=child.stdout, check=True)
                child.stdout.close()
                if child.wait():
                    fail('Cannot extract incoming ELF payload')
            for path in incoming_paths:
                extracted = Path(folder) / path.lstrip('/')
                if extracted.is_file() and not extracted.is_symlink():
                    with extracted.open('rb') as payload:
                        if payload.read(4) != b'\x7fELF':
                            continue
                    incoming_elf[path] = policy_module.DETAILS.elf_details(str(extracted), set(audit['symbols_checked']))
                    # Resolve $ORIGIN as it will be after installation, not in
                    # the temporary extraction directory.
                    incoming_elf[path]['resolved_path'] = path
            policy = policy_module.classify(audit, symbols, changed_files, outgoing_flags, outgoing_owners, incoming_elf)
        (report / 'symbol-audit-policy.json').write_text(json.dumps(policy, indent=2) + '\n')
        print('Symbol review: {} accounted for; {} blocking; {} pre-existing dangling links (not repaired).'.format(
            len(policy['accepted_matches']), len(policy['blocking_matches']), len(policy['preexisting_dangling_links'])), flush=True)
        if result.returncode not in (0, 1, 2) or not policy['allow_transaction']:
            fail('Symbol imports or incomplete audit found; see symbol-audit.json. No RPMs installed.')
        if mode == 'check':
            # DNF's actual RPM transaction test, including file conflicts, without installing.
            base.conf.tsflags = ['test']
            base.do_transaction()
            return
        print('Saving /etc and package inventory; this is not a full system rollback image.', flush=True)
        subprocess.check_call(['tar', '--acls', '--xattrs', '--selinux', '-czf', str(report / 'etc-before.tar.gz'), '-C', '/', 'etc'])
        if inventory() != before:
            fail('RPM inventory changed during planning; rerun after the other package operation finishes.')
        (report / 'status.txt').write_text('RPM_TRANSACTION_STARTED\n')
        transaction_id = base.do_transaction()
        (report / 'dnf-transaction-id.txt').write_text(str(transaction_id) + '\n')
        (report / 'status.txt').write_text('RPM_TRANSACTION_COMPLETED\n')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(2)
