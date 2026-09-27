#!/usr/bin/env python3
"""Combine Linux CNA source evidence with Red Hat VEX for one EL8 kernel.

Every input CVE receives a terminal disposition. Exact source evidence,
validated reviewed backports, an excluded build input, or an applicable Red
Hat RHEL 8.10 statement can produce ``fixed`` or ``not_affected``. Everything
else is conservatively reported as ``affected`` instead of being left under
investigation.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import rpm


KERNEL_NEVRA = re.compile(
    r':kernel(?:-core)?-(?P<epoch>\d+):(?P<version>[^-:]+)-'
    r'(?P<release>.+)\.(?P<arch>x86_64|src)$')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_product(product):
    if (product.startswith(('BaseOS-8.', 'AppStream-8.'))
            and ':kernel' in product):
        return True
    return product in {
        'red_hat_enterprise_linux_8:kernel',
        'red_hat_enterprise_linux_8:kernel-core',
        'red_hat_enterprise_linux_8:kernel.src',
    }


def parse_evr(product):
    match = KERNEL_NEVRA.search(product)
    if not match:
        return None
    return (match.group('epoch'), match.group('version'), match.group('release'))


def redhat_status(vex_root, cve, base_evr):
    year = cve.split('-')[1]
    path = vex_root / year / (cve.lower() + '.json')
    if not path.is_file():
        return {'status': 'missing-redhat-vex', 'path': None, 'products': []}
    document = load(path)
    vulnerabilities = [item for item in document.get('vulnerabilities', [])
                       if item.get('cve') == cve]
    if len(vulnerabilities) != 1:
        return {'status': 'malformed-redhat-vex', 'path': str(path),
                'products': []}
    product_status = vulnerabilities[0].get('product_status', {})
    selected = {status: sorted(product for product in products
                               if target_product(product))
                for status, products in product_status.items()}
    selected = {status: products for status, products in selected.items()
                if products}
    fixed = []
    later = []
    for product in selected.get('fixed', []):
        evr = parse_evr(product)
        if not evr:
            continue
        (fixed if rpm.labelCompare(evr, base_evr) <= 0 else later).append(product)
    if fixed:
        status = 'redhat-fixed-in-base'
        products = fixed
    elif selected.get('known_not_affected'):
        status = 'redhat-known-not-affected'
        products = selected['known_not_affected']
    elif selected.get('known_affected'):
        status = 'redhat-known-affected'
        products = selected['known_affected']
    elif selected.get('under_investigation'):
        status = 'redhat-under-investigation'
        products = selected['under_investigation']
    elif later:
        status = 'redhat-fixed-after-base'
        products = later
    else:
        status = 'redhat-no-rhel8-kernel-statement'
        products = []
    return {'status': status, 'path': str(path), 'products': products,
            'document_tracking_id': document.get('document', {}).get(
                'tracking', {}).get('id')}


def decide(item, build, patch, hunk, semantic, redhat, reviewed):
    crosswalk = item['status']
    if crosswalk == 'not-introduced-in-candidate':
        return ('not_affected', 'vulnerable_code_not_present',
                'Linux CNA affected range does not include the EL8 base source')
    if crosswalk == 'unaffected-by-cna-default':
        return ('not_affected', 'vulnerable_code_not_present',
                'Linux CNA explicitly defaults comparable versions to unaffected')
    if build == 'not-built-in-config':
        return ('not_affected', 'component_not_present',
                'Named vulnerable source files are not inputs to this exact build')
    if patch == 'fix-present-exact-reverse-apply':
        return ('fixed', None,
                'Official Linux stable fix is present by exact reverse-apply check')
    if hunk == 'already-present-by-hunks':
        return ('fixed', None,
                'Every official Linux stable fix hunk is present with zero fuzz')
    if reviewed == 'applied':
        return ('fixed', None,
                'Reviewed Linux stable fix was backported and passed the full kernel build and QEMU validation')
    if reviewed == 'already-effective-threeway':
        return ('fixed', None,
                'Reviewed Linux stable fix is already effective in the exact source by three-way source comparison')
    # Distinctive lines are useful review hints, but can also occur in partial
    # or unrelated downstream edits.  Keep them in the report without using
    # them as resolved OpenVEX evidence.
    if redhat['status'] == 'redhat-fixed-in-base':
        return ('fixed', None,
                'Red Hat VEX lists a RHEL 8.10 kernel build at or below the base EVR as fixed')
    if redhat['status'] == 'redhat-known-not-affected':
        return ('not_affected', 'vulnerable_code_not_present',
                'Red Hat VEX marks the RHEL 8.10 kernel product not affected')
    return ('affected', None,
            'No validated fixed or not-affected evidence exists for this exact build; conservatively treated as affected')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crosswalk', type=Path, required=True)
    parser.add_argument('--build-reachability', type=Path, required=True)
    parser.add_argument('--post-backport', type=Path, action='append', required=True,
                        help='Exact patch check JSON; may be repeated')
    parser.add_argument('--hunk-evidence', type=Path, action='append', default=[],
                        help='Zero-fuzz hunk check JSON; may be repeated')
    parser.add_argument('--semantic', type=Path, required=True)
    parser.add_argument('--validated-backports', type=Path, action='append', default=[],
                        help='Reviewed backport evidence JSON; may be repeated')
    parser.add_argument('--redhat-vex-root', type=Path, required=True)
    parser.add_argument('--redhat-vex-manifest', type=Path, action='append', default=[],
                        help='Hash manifest or archive metadata used to build the VEX root')
    parser.add_argument('--base-evr', default='0:4.18.0-553.168.1.el8_10')
    parser.add_argument('--purl', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--openvex-output', type=Path, required=True)
    args = parser.parse_args()

    epoch, value = args.base_evr.split(':', 1)
    version, release = value.split('-', 1)
    base_evr = (epoch, version, release)
    crosswalk = load(args.crosswalk)
    build_doc = load(args.build_reachability)
    semantic_doc = load(args.semantic)
    build = {item['cve']: item['build_status'] for item in build_doc['items']}
    patch = {}
    for path in args.post_backport:
        for evidence in load(path)['items']:
            current = patch.get(evidence['cve'])
            if current != 'fix-present-exact-reverse-apply':
                patch[evidence['cve']] = evidence['status']
    hunk = {}
    for path in args.hunk_evidence:
        document = load(path)
        if document.get('fuzz') != 0:
            raise ValueError('hunk evidence must be generated with --fuzz 0: ' +
                             str(path))
        for evidence in document['items']:
            if evidence['status'] == 'already-present-by-hunks':
                hunk[evidence['cve']] = evidence['status']
    semantic = {item['cve']: item['semantic_status']
                for item in semantic_doc['items']}
    reviewed = {}
    for path in args.validated_backports:
        document = load(path)
        for evidence in document['items']:
            status = evidence['status']
            if status not in {'applied', 'already-effective-threeway'}:
                raise ValueError('unsupported reviewed backport status: ' + status)
            previous = reviewed.get(evidence['cve'])
            if previous and previous != status:
                raise ValueError('conflicting reviewed backport status: ' + evidence['cve'])
            reviewed[evidence['cve']] = status
    results = []
    counts = Counter()
    evidence_counts = Counter()
    statements = []
    for item in crosswalk['items']:
        cve = item['cve']
        redhat = redhat_status(args.redhat_vex_root, cve, base_evr)
        final_status, justification, reason = decide(
            item, build.get(cve), patch.get(cve), hunk.get(cve),
            semantic.get(cve), redhat, reviewed.get(cve))
        result = {
            'cve': cve,
            'title': item.get('title', ''),
            'crosswalk_status': item['status'],
            'build_status': build.get(cve, 'not-evaluated'),
            'patch_status': patch.get(cve, 'not-evaluated'),
            'hunk_status': hunk.get(cve, 'not-evaluated'),
            'semantic_status': semantic.get(cve, 'not-evaluated'),
            'reviewed_backport_status': reviewed.get(cve, 'not-evaluated'),
            'redhat': redhat,
            'final_status': final_status,
            'justification': justification,
            'reason': reason,
        }
        results.append(result)
        counts[final_status] += 1
        evidence_counts[reason] += 1
        statement = {
            'vulnerability': {'name': cve},
            'products': [{'@id': purl} for purl in args.purl],
            'status': final_status,
            'impact_statement': reason,
        }
        if justification:
            statement['justification'] = justification
        statements.append(statement)

    input_paths = ([args.crosswalk, args.build_reachability, args.semantic] +
                   args.post_backport + args.hunk_evidence +
                   args.validated_backports + args.redhat_vex_manifest)
    inputs = {str(path): digest(path) for path in input_paths}
    report = {
        'schema_version': 1,
        'scope': ('Terminal CVE accounting for the exact custom EL8 kernel source '
                  'and configuration. Unresolved risk is reported as affected.'),
        'base_evr': args.base_evr,
        'linux_cna_commit': crosswalk.get('linux_cna_commit'),
        'redhat_vex_archive': args.redhat_vex_root.parent.name,
        'inputs_sha256': inputs,
        'counts': dict(sorted(counts.items())),
        'evidence_counts': dict(sorted(evidence_counts.items())),
        'items': results,
    }
    with args.output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    identity = hashlib.sha256(json.dumps(
        {'inputs': inputs, 'purls': args.purl}, sort_keys=True).encode()).hexdigest()
    openvex = {
        '@context': 'https://openvex.dev/ns/v0.2.0',
        '@id': 'https://github.com/emotionbug/slop/security/vex/' + identity,
        'author': 'Linux OSS local build',
        'timestamp': timestamp,
        'version': 1,
        'statements': statements,
    }
    with args.openvex_output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(openvex, indent=2) + '\n')
    print(json.dumps(report['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
