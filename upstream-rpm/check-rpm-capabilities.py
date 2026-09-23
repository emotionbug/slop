#!/usr/libexec/platform-python
"""Static RPM header checks using librpm. Does not replace DNF or VM tests.

Run under EL8 /usr/libexec/platform-python with python3-rpm installed.
Only read-only inventory headers and candidate RPMs are inspected.
"""
import argparse
import collections
import csv
import glob
import json
import pathlib
import rpm


def evr(value):
    epoch, sep, rest = value.partition(':')
    if not sep:
        epoch, rest = '0', epoch
    version, sep, release = rest.rpartition('-')
    return (epoch, version, release) if sep else (epoch, rest, '')


def satisfies(requirement, provider):
    # rpm.ds.Compare is an overlap primitive; its unconstrained range is not
    # sufficient evidence for a versioned requirement in this static audit.
    if requirement['flags'] and requirement['version'] and not provider['version']:
        return None
    mapping = {'': 0, '=': rpm.RPMSENSE_EQUAL, '>': rpm.RPMSENSE_GREATER,
               '<': rpm.RPMSENSE_LESS, '>=': rpm.RPMSENSE_GREATER | rpm.RPMSENSE_EQUAL,
               '<=': rpm.RPMSENSE_LESS | rpm.RPMSENSE_EQUAL}
    if requirement['flags'] not in mapping or provider['flags'] not in mapping:
        return None
    req = rpm.ds((requirement['capability'],mapping[requirement['flags']],requirement['version']),rpm.RPMTAG_REQUIRENAME)
    prov = rpm.ds((provider['capability'],mapping[provider['flags']],provider['version']),rpm.RPMTAG_PROVIDENAME)
    return req.Compare(prov)


def flags_text(flags):
    value = flags & (rpm.RPMSENSE_LESS | rpm.RPMSENSE_GREATER | rpm.RPMSENSE_EQUAL)
    return {0: '', rpm.RPMSENSE_EQUAL: '=', rpm.RPMSENSE_GREATER: '>',
            rpm.RPMSENSE_LESS: '<', rpm.RPMSENSE_GREATER | rpm.RPMSENSE_EQUAL: '>=',
            rpm.RPMSENSE_LESS | rpm.RPMSENSE_EQUAL: '<='}.get(value, 'unsupported')


def rows(path):
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def candidate(ts, path):
    with open(path, 'rb') as handle:
        header = ts.hdrFromFdno(handle.fileno())
    if header[rpm.RPMTAG_SOURCEPACKAGE]:
        raise ValueError('Binary RPM required: '+path)
    name, arch = header['name'], header['arch']
    result = {'name': name, 'arch': arch, 'file': path,
              'epoch': str(header['epoch'] or 0), 'version': header['version'], 'release': header['release']}
    for key in ('require', 'provide'):
        result[key+'s'] = [dict(name=name, arch=arch, capability=n, flags=flags_text(f), version=v)
                           for n,f,v in zip(header[key+'name'], header[key+'flags'], header[key+'version'])]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', required=True, type=pathlib.Path)
    parser.add_argument('--output', required=True, type=pathlib.Path)
    parser.add_argument('rpms', nargs='+')
    args = parser.parse_args()
    paths = [p for pattern in args.rpms for p in glob.glob(pattern)]
    if not paths:
        raise SystemExit('No RPMs matched')
    ts = rpm.TransactionSet()
    built = [candidate(ts, p) for p in paths]
    replaced = {(p['name'], p['arch']) for p in built}
    old = rows(args.inventory/'packages.tsv')
    providers = [r for r in rows(args.inventory/'provides.tsv') if (r['name'],r['arch']) not in replaced]
    requirements = [r for r in rows(args.inventory/'requires.tsv') if (r['name'],r['arch']) not in replaced]
    for p in built:
        providers.extend(p['provides'])
        requirements.extend(p['requires'])
    by_cap = collections.defaultdict(list)
    for p in providers:
        by_cap[p['capability']].append(p)
    missing, unresolved = [], []
    for r in requirements:
        cap = r['capability']
        if cap.startswith('rpmlib('):
            continue
        if cap.startswith(('/', '(')):
            unresolved.append(r)
            continue
        matched = [satisfies(r,p) for p in by_cap[cap]]
        if not any(v is True for v in matched):
            (unresolved if any(v is None for v in matched) else missing).append(r)
    old_by_key = {(p['name'],p['arch']):p for p in old}
    comparisons = []
    for p in built:
        before = old_by_key.get((p['name'],p['arch']))
        comparisons.append({'name':p['name'], 'arch':p['arch'], 'candidate':p['epoch']+':'+p['version']+'-'+p['release'],
                            'installed': before,
                            'evr_comparison': rpm.labelCompare((p['epoch'],p['version'],p['release']),
                              (before['epoch'],before['version'],before['release'])) if before else None})
    downgrades = [p for p in comparisons if p['evr_comparison'] is not None and p['evr_comparison'] < 0]
    report = {'check': 'static-capability-headers-only', 'candidates':comparisons,
              'downgrade_candidates':downgrades,
              'missing_named_requirements':missing, 'unverified_requirements':unresolved,
              'dnf_transaction_tested':False, 'file_conflicts_tested':False, 'modularity_tested':False,
              'service_scripts_tested':False, 'runtime_tested':False,
              'limit':'No file owner inventory, RPM payload conflicts, rich deps, scriptlet ordering, module filtering or dlopen analysis. Not deployment clearance.'}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'candidate_count':len(built), 'missing_named_requirements':len(missing),
                      'downgrade_candidates':len(downgrades),
                      'unverified_file_rich_or_unversioned_requirements':len(unresolved)}))
    if missing or downgrades:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
