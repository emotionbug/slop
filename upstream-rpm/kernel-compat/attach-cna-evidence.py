#!/usr/bin/env python3
"""Bind Linux CNA release evidence to an audited, exact upstream-kernel build.

This deliberately accepts only the existing 7.2.7 release-3 source provenance.
It cannot bless EL8 backports, other kernel builds, or an installed/running OS.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')


def review_for(item, cross):
    if item['status'] not in ('fixed-in-candidate-release', 'unaffected-by-cna-default'):
        return None
    path = item['record_path'].split(':', 1)[1]
    advisory = ('https://git.kernel.org/pub/scm/linux/security/vulns.git/tree/' + path
                + '?id=' + cross['linux_cna_commit'])
    fixed = item['status'] == 'fixed-in-candidate-release'
    scope = ('Linux CNA explicitly lists upstream 7.2.7 in a fixed release range.' if fixed else
             'Linux CNA explicitly marks fully comparable versions outside its listed affected ranges as unaffected; upstream 7.2.7 falls outside all those ranges. Non-applicability, not a newly applied security fix.')
    return {'cve': item['cve'], 'status': 'fixed' if fixed else 'not_affected',
            'scope': scope + ' Exact release-3 RPM files only; running-kernel state and security-agent compatibility are not established.',
            'advisory': advisory, 'evidence': advisory,
            'verification': 'CNA record SHA256 ' + item['record_sha256'] + '; upstream source SHA256 ' + cross['source_sha256'],
            'cna_release_ranges': item['matching_ranges']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('crosswalk', 'catalog', 'evidence', 'provenance', 'source-archive', 'rpms'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    cross = json.loads(args.crosswalk.read_text())
    provenance = json.loads(args.provenance.read_text())
    catalog = json.loads(args.catalog.read_text())
    evidence = json.loads(args.evidence.read_text())
    if cross['candidate'] != '7.2.7' or provenance['name'] != 'linux-7.2.7.tar.xz':
        raise ValueError('Only the reviewed unmodified 7.2.7 source is accepted')
    if provenance.get('upstream_signature_verified') is not True:
        raise ValueError('Missing upstream signature evidence')
    if sha(args.source_archive) != provenance['sha256']:
        raise ValueError('Source archive mismatch')
    if sha(args.rpms / provenance['release_source_rpm']) != provenance['release_source_rpm_sha256']:
        raise ValueError('Source RPM mismatch')
    selected = [a for a in catalog['artifacts'] if a['project'] == 'kernel'
                and a['srpm_sha256'] == provenance['release_source_rpm_sha256']]
    if {a['name'] for a in selected} != {'kernel', 'kernel-devel', 'kernel-headers'}:
        raise ValueError('Unexpected reviewed kernel build set')
    for a in selected:
        filename = '{name}-{version}-{release}.{arch}.rpm'.format(**a)
        if sha(args.rpms / filename) != a['rpm_sha256']:
            raise ValueError('Binary RPM mismatch: ' + filename)
        if a['components'] != [{'project': 'kernel', 'version': '7.2.7'}]:
            raise ValueError('Unexpected upstream component binding')
    cross['source_sha256'] = provenance['sha256']
    reviews = [review for item in cross['items'] if (review := review_for(item, cross))]
    for a in selected:
        existing = evidence['artifacts'].setdefault(a['rpm_sha256'], [])
        indexed = {r['cve']: r for r in existing}
        for review in reviews:
            if review['cve'] in indexed and indexed[review['cve']] != review:
                raise ValueError('Conflicting existing assessment: ' + review['cve'])
            if review['cve'] not in indexed:
                existing.append(review)
        existing.sort(key=lambda r: r['cve'])
        a['assessments'] = existing
    write(args.evidence, evidence)
    catalog['reviewed_evidence_sha256'] = sha(args.evidence)
    write(args.catalog, catalog)
    print(json.dumps({'exact_rpms': len(selected), 'cves_per_rpm': len(reviews), 'running_system_remediated': False}))


if __name__ == '__main__':
    main()
