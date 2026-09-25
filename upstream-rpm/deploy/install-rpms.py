#!/usr/libexec/platform-python
"""Use EL8 DNF to upgrade installed names only, with local hard dependencies."""
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys

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
    entries = [item for item in manifest['files'] if item['path'].startswith('rpms/')]
    expected = {item['path']: item for item in entries}
    actual = {str(p.relative_to(root)) for p in (root / 'rpms').glob('*.rpm')}
    if len(expected) != 77 or actual != set(expected):
        fail('Expected the exact pinned 77-RPM candidate set.')
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
        # Check only symbol removals belonging to libraries in this transaction.
        changed_files = set()
        for package in incoming:
            changed_files.update(subprocess.check_output(['rpm', '-qpl', package.localPkg()]).decode().splitlines())
        symbols = json.loads((root / 'expected-export-removals.json').read_text())
        symbols['libraries'] = [item for item in symbols['libraries'] if item['library'] in changed_files]
        (report / 'transaction-symbols.json').write_text(json.dumps(symbols))
        audit_file = report / 'symbol-audit.json'
        with audit_file.open('w') as stream:
            result = subprocess.run([sys.executable, str(root / 'check-removed-symbol-users.py'),
                                     '--symbols-file', str(report / 'transaction-symbols.json')] + sys.argv[4:], stdout=stream)
        audit = json.loads(audit_file.read_text())
        ignored = [item for item in audit['errors'] if item.get('kind') == 'broken_symlink' and
                   item.get('path', '').startswith(('/usr/lib/.build-id/', '/usr/lib/debug/.build-id/'))]
        blocking = [item for item in audit['errors'] if item not in ignored]
        (report / 'symbol-audit-policy.json').write_text(json.dumps({
            'ignored_dangling_debug_links': ignored, 'blocking_errors': blocking,
            'reason': 'Dangling build-id debug metadata has no existing ELF target; raw audit is preserved.'}, indent=2))
        if result.returncode not in (0, 1, 2) or audit.get('audit_version') != 3 or blocking or \
                audit['direct_import_matches'] or audit['directory_symlinks_outside_roots']:
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
