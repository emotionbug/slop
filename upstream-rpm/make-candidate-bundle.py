#!/usr/bin/env python3
"""Package only reviewed candidate RPMs and corresponding source RPMs.

No server inventory, private analysis, caches, signing keys or logs are included.
"""
import hashlib
import json
import pathlib
import shutil
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent
VERSION = '20260924-3'
TARGETS = {
    'rsync': ('3.5.1', ['rsync']),
    'zlib': ('1.3.2', ['zlib', 'zlib-devel']),
    'pcre2': ('10.48', ['pcre2', 'pcre2-devel', 'pcre2-utf16', 'pcre2-utf32']),
    'expat': ('2.8.5', ['expat', 'expat-devel']),
    'xz': ('5.8.4', ['xz', 'xz-libs', 'xz-devel']),
    'c-ares': ('1.34.8', ['c-ares']),
    'libpng': ('1.6.58', ['libpng']),
    'lcms2': ('2.19.1', ['lcms2']),
    'sed': ('4.10', ['sed']),
    'diffutils': ('3.12', ['diffutils']),
    'patch': ('2.8', ['patch']),
    'gawk': ('5.4.1', ['gawk']),
}


def main():
    validation = json.loads((ROOT/'output/validation.json').read_text())
    if (validation.get('_combined_nineteen', {}).get('runtime_result') != 'passed' or
            validation.get('_combined_nineteen', {}).get('host_capability_result') != 'passed'):
        raise SystemExit('Combined container validation has not passed')
    archive = ROOT/'output'/('el8-rpm-candidates-'+VERSION+'.tar.gz')
    if archive.exists():
        raise SystemExit('Refusing to overwrite an existing release archive: '+str(archive))
    dest = ROOT/'output'/('candidate-bundle-'+VERSION)
    dest.mkdir(exist_ok=True)
    manifest = {'status': 'local-evaluation-candidates', 'custom_rpms_signed': False,
                'all_323_packages_complete': False, 'target_server_install_tested': False,
                'private_host_data_included': False, 'files': []}
    lock = json.loads((ROOT/'sources.lock.json').read_text())
    included_sources = {'rsync-3.5.1.tar.gz', 'xxHash-0.8.4.tar.gz',
                        'zlib-1.3.2.tar.xz', 'pcre2-10.48.tar.bz2',
                        'expat-2.8.5.tar.xz', 'xz-5.8.4.tar.xz',
                        'c-ares-1.34.8.tar.gz', 'googletest-1.18.0.tar.gz',
                        'libpng-1.6.58.tar.xz', 'lcms2-2.19.1.tar.gz',
                        'sed-4.10.tar.xz', 'diffutils-3.12.tar.xz',
                        'diffutils-CVE-2026-53910-1.patch', 'diffutils-CVE-2026-53910-2.patch',
                        'patch-2.8.tar.xz', 'gawk-5.4.1.tar.xz'}
    manifest['upstream_sources'] = [s for s in lock['sources'] if s['name'] in included_sources]
    manifest['validation_scope'] = ['upstream-tests', 'UBI8-DNF-upgrade',
        'Java8-Python-compression', 'PCRE2-JIT', 'rsync-old-peer-over-local-pipe',
        'Python-Expat-XML-and-XZ-roundtrip', 'Expat-XZ-exported-symbol-presence',
        'PNG-LCMS-old-binary-roundtrips-and-exported-symbol-presence',
        'c-ares-1140-offline-tests-and-two-fuzz-suites', 'c-ares-UBI-DNS-parser',
        'c-ares-EL8-reference-60-exports-not-exact-RHEL-baseline',
        'target-RPM-named-capabilities-only', 'sed-ACL-mode-symlink-and-baseline-xattr-behavior',
        'diffutils-merge-and-CVE-2026-53910-bounded-rejection',
        'patch-dry-run-apply-reverse', 'gawk-MPFR-array-and-filefuncs']
    manifest['validation_exceptions'] = [
        'c-ares public DNS tests: 60 passed, 2 ANY-query tests failed because resolver returned RCODE 4 NotImplemented; independent query reproduced.',
        'Zstandard and libjpeg-turbo remain excluded because removed exports need target-consumer review.',
        'File/rich dependencies, full target transaction and applications have not been validated.'
    ]
    for project, (version, names) in TARGETS.items():
        release = '2' if project == 'diffutils' else '1'
        directory = 'diffutils-patched' if project == 'diffutils' else project
        artifacts = [(name+'-'+version+'-'+release+'.linuxoss.el8.x86_64.rpm', 'rpms') for name in names]
        artifacts.append((project+'-'+version+'-'+release+'.linuxoss.el8.src.rpm', 'srpms'))
        for filename, folder in artifacts:
            source = ROOT/'output'/directory/filename
            expected = validation[project]['artifacts'].get(filename)
            if not expected or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise SystemExit('Artifact is not the hash recorded by validation: '+filename)
            destination = dest/folder/filename
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, destination)
            manifest['files'].append({'path':folder+'/'+filename, 'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
    for filename, expected in validation['_official_dependencies']['artifacts'].items():
        if filename != 'cmake-filesystem-3.26.5-2.el8.x86_64.rpm':
            raise SystemExit('Unreviewed official dependency: '+filename)
        source = ROOT/'output/official-dependencies'/filename
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise SystemExit('Official dependency hash mismatch: '+filename)
        destination = dest/'rpms'/filename
        shutil.copyfile(source, destination)
        manifest['files'].append({'path':'rpms/'+filename,'sha256':expected,
            'origin':'Red Hat UBI 8','rpm_signature_verified':True})
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (dest/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in manifest['files']),encoding='ascii')
    (dest/'README.txt').write_text(
        'EL8 candidates: rsync, zlib, PCRE2, Expat, XZ, c-ares, libpng, Little CMS, sed, diffutils, patch, gawk.\n'
        'Nineteen replacement RPMs, twelve source RPMs, one official UBI directory-layout dependency.\n'
        'See manifest.json for exact versions, test scope and external-DNS exceptions.\n'
        'Not a complete 323-package upgrade; not tested on the target server.\n'
        'Custom RPMs are unsigned local builds. Only cmake-filesystem is a signed Red Hat UBI RPM.\n'
        'UBI container tests do not prove target boot or application compatibility.\n'
        'Inspect checksums and DNF transaction before installation. No forced dependencies.\n'
        'Do not use absent Trivy findings for custom RPMs as proof of remediation.\n'
        'Sources and recipes: https://github.com/emotionbug/slop/tree/main/upstream-rpm\n',encoding='utf-8')
    # Explicit allowlist prevents stale or accidental private files in dest
    # from entering the archive on a later run.
    include = [r['path'] for r in manifest['files']]+['manifest.json','SHA256SUMS','README.txt']
    with tarfile.open(archive,'w:gz') as out:
        for relative in include:
            out.add(dest/relative,arcname='el8-rpm-candidates/'+relative,recursive=False)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix+'.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    print(json.dumps({'archive':str(archive),'size':archive.stat().st_size,'sha256':digest}))


if __name__ == '__main__':
    main()
