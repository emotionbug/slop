#!/usr/bin/env python3
"""Attach explicit EL8 backport evidence; preserve unreviewed baseline CVEs.

This does not infer fixes from a version bump or upstream CPE range. The input
ledger must pin the tested binary/source RPMs and name the evidence for each CVE.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--reviews', type=Path, required=True)
    p.add_argument('--projects', type=Path, required=True)
    args = p.parse_args()
    ledger = json.loads(args.ledger.read_text())
    assert ledger['schema_version'] == 1
    reviews = json.loads(args.reviews.read_text())
    projects = json.loads(args.projects.read_text())
    for group in ledger['groups']:
        assert group['validation_state'] == 'local-validation-completed'
        srpm = args.bundle / group['srpm']['path']
        assert args.bundle.resolve() in srpm.resolve().parents
        assert sha(srpm) == group['srpm']['sha256']
        projects['artifacts'][sha(srpm)] = {
            'project': group['project'], 'components': [],
            'include_nonstandard_vendor': True,
            'evidence': group['evidence'],
        }
        for artifact in group['rpms']:
            rpm = args.bundle / artifact['path']
            assert args.bundle.resolve() in rpm.resolve().parents
            assert sha(rpm) == artifact['sha256']
            source_name = subprocess.check_output(['rpm', '-qp', '--qf', '%{SOURCERPM}', str(rpm)], universal_newlines=True)
            assert source_name == srpm.name
            assessments = []
            reviewed = {row['cve']: row for row in group['assessments']}
            for cve in sorted(set(group['baseline_cves']) | set(reviewed)):
                row = dict(reviewed.get(cve, {
                    'cve': cve, 'status': 'under_investigation',
                    'scope': 'Unresolved baseline CVE carried forward. No source fix or non-applicability is claimed.',
                    'advisory': 'https://www.cve.org/CVERecord?id=' + cve,
                    'verification': 'Baseline carry-forward only; requires source review.',
                }))
                assert row['status'] in ('fixed', 'not_affected', 'under_investigation')
                row['evidence'] = group['evidence']
                row['severity'] = group.get('baseline_severities', {}).get(cve, 'UNKNOWN')
                assessments.append(row)
            reviews['artifacts'][artifact['sha256']] = assessments
    for path, data in [(args.reviews, reviews), (args.projects, projects)]:
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    print('Attached', len(ledger['groups']), 'source groups; unresolved baseline retained')


if __name__ == '__main__':
    main()
