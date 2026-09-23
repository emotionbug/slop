#!/usr/bin/env python3
"""Keep every CSV target and prefer exact host RPM headers over reference data."""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
VERIFIED = {
    'rsync': ('3.5.1', 'https://rsync.samba.org/'),
    'gcc': ('16.2.0', 'https://gcc.gnu.org/releases.html'),
    'kernel': ('7.2.7', 'https://www.kernel.org/releases.json'),
    'glibc': ('2.44', 'https://ftp.gnu.org/gnu/glibc/'),
    'openssl': ('4.0.2', 'https://www.openssl-library.org/source/'),
    'binutils': ('2.47', 'https://ftp.gnu.org/gnu/binutils/'),
    'zlib': ('1.3.2', 'https://zlib.net/'),
    'pcre2': ('10.48', 'https://github.com/PCRE2Project/pcre2/releases/tag/pcre2-10.48'),
    'expat': ('2.8.5', 'https://github.com/libexpat/libexpat/releases/tag/R_2_8_5'),
    'xz': ('5.8.4', 'https://github.com/tukaani-project/xz/releases/tag/v5.8.4'),
    'zstd': ('1.5.7', 'https://github.com/facebook/zstd/releases/tag/v1.5.7'),
    'c-ares': ('1.34.8', 'https://github.com/c-ares/c-ares/releases/tag/v1.34.8'),
}
BOOT = {'kernel', 'grub2', 'shim', 'systemd', 'lvm2', 'device-mapper-multipath',
        'device-mapper-persistent-data', 'mdadm', 'iscsi-initiator-utils'}
AUTH = {'openssh', 'pam', 'sssd', 'shadow-utils', 'krb5', 'polkit',
        'polkit-pkla-compat', 'openldap'}
MANAGEMENT = {'rpm', 'python3', 'python36', 'python-pip', 'subscription-manager',
              'subscription-manager-rhsm-certificates', 'policycoreutils',
              'NetworkManager', 'firewalld', 'libsolv'}
ABI = {'glibc', 'openssl', 'gcc', 'libxml2', 'glib2', 'libcurl', 'curl',
       'nss', 'nss-util', 'nss-softokn', 'gnutls', 'mozjs60', 'libicu',
       'libsoup', 'samba', 'perl', 'sqlite', 'util-linux', 'dbus', 'libbpf'}
FIRMWARE = {'linux-firmware', 'microcode_ctl'}


def source_name(filename):
    match = re.fullmatch(r'(.+)-([^-]+)-([^-]+)\.(?:src|nosrc)\.rpm', filename)
    return match[1] if match else None


def category(source):
    if source in FIRMWARE:
        return 'firmware', '배포 라이선스·장치 호환성 확인; 일반 소스 컴파일 대상과 다름'
    if source in BOOT:
        return 'boot-storage', 'RHEL 8 VM 부팅·initramfs·스토리지·외부 모듈 검증 필요'
    if source in AUTH:
        return 'authentication', 'SSH·PAM·SSSD·계정 인증 연동 검증 필요'
    if source in MANAGEMENT:
        return 'os-management', '패키지 관리자·인터프리터·SELinux·네트워크 연동 검증 필요'
    if source in ABI:
        return 'shared-abi', 'SONAME·심볼·역의존성 재빌드 및 Java/JNI 영향 확인 필요'
    return 'package-specific', '기존 SPEC 기능·설정·의존성·upstream 변경점 확인 필요'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv', type=pathlib.Path)
    ap.add_argument('--reference', type=pathlib.Path, default=ROOT/'work/el8-reference-packages.tsv')
    ap.add_argument('--inventory', type=pathlib.Path, help='Directory containing host packages.tsv')
    ap.add_argument('--output', type=pathlib.Path, default=ROOT/'output')
    args = ap.parse_args()
    with args.csv.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    required = {'패키지명', '설치버전', '수정버전', 'CVE', '심각도', '상태'}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit('Input CSV does not have the expected Trivy columns')
    targets = collections.defaultdict(list)
    for row in rows:
        targets[row['패키지명']].append(row)
    reference = collections.defaultdict(list)
    with args.reference.open(encoding='utf-8') as handle:
        for line in handle:
            fields = line.rstrip('\n').split('\t')
            if len(fields) == 7 and fields[4] in ('x86_64', 'noarch'):
                reference[fields[0]].append(fields)
    host = collections.defaultdict(list)
    if args.inventory:
        with (args.inventory/'packages.tsv').open(encoding='utf-8', newline='') as handle:
            for row in csv.DictReader(handle, delimiter='\t'):
                host[row['name']].append(row)
    records = []
    for name, findings in sorted(targets.items()):
        exact = {source_name(r['source_rpm']) for r in host[name]} - {None}
        estimated = {source_name(r[5]) for r in reference[name]} - {None}
        candidates = exact or estimated
        source = next(iter(candidates)) if len(candidates) == 1 else None
        mapping = 'host-rpm-header' if exact else 'EL8-reference-provisional' if source else 'unresolved'
        urls = sorted({r[6] for r in reference[name] if r[6].startswith(('http://','https://'))})
        kind, gate = category(source)
        latest = VERIFIED.get(source)
        csv_versions = sorted({r['설치버전'] for r in findings})
        host_versions = sorted({('' if r['epoch'] == '0' else r['epoch']+':')+
                                r['version']+'-'+r['release'] for r in host[name]})
        records.append({
            'package': name,
            'installed_versions': host_versions if args.inventory else csv_versions,
            'csv_versions': csv_versions,
            'present_in_host_inventory': bool(host[name]) if args.inventory else None,
            'csv_versions_absent_from_inventory': sorted(set(csv_versions)-set(host_versions)) if args.inventory else [],
            'host_source_rpms': sorted({r['source_rpm'] for r in host[name]}),
            'host_architectures': sorted({r['arch'] for r in host[name]}),
            'host_modules': sorted({r['module'] for r in host[name] if r['module'] != '(none)'}),
            'source_project': source,
            'source_candidates': sorted(candidates),
            'mapping_evidence': mapping,
            'reference_source_rpms': sorted({r[5] for r in reference[name]}),
            'upstream_urls_from_reference': urls,
            'latest_stable': latest[0] if latest else None,
            'latest_evidence': latest[1] if latest else None,
            'latest_checked_on': ('2026-09-24' if source in {'expat','xz','zstd','c-ares'}
                                  else '2026-09-23') if latest else None,
            'latest_status': 'verified-upstream' if latest else 'not-yet-verified',
            'category': kind,
            'required_validation': gate,
            'findings': len(findings),
            'unique_cves': len({r['CVE'] for r in findings}),
            'severity_counts': dict(collections.Counter(r['심각도'] for r in findings)),
            'status_counts': dict(collections.Counter(r['상태'] for r in findings)),
            'build_status': 'not-built',
            'target_install_status': 'not-tested',
        })
    projects = collections.defaultdict(list)
    for record in records:
        projects[record['source_project'] or 'UNRESOLVED:'+record['package']].append(record)
    report = {
        'generated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'input_sha256': hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        'target_package_count': len(records),
        'source_project_count_including_unresolved': len(projects),
        'source_mapping_confirmed_from_host': all(r['mapping_evidence']=='host-rpm-header' for r in records),
        'inventory_sha256': hashlib.sha256((args.inventory/'packages.tsv').read_bytes()).hexdigest() if args.inventory else None,
        'inventory_package_records': sum(len(v) for v in host.values()) if args.inventory else None,
        'warning': 'Host headers are authoritative where present; Rocky EL8 fallback mappings are provisional. Header/capability checks are not proof of runtime ABI compatibility. Latest versions are not inferred from EL8 repository versions. No unverified build/install status is promoted to success.',
        'packages': records,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    validation_path = args.output/'validation.json'
    validation = json.loads(validation_path.read_text(encoding='utf-8')) if validation_path.exists() else {}
    for record in records:
        checked = validation.get(record['package'])
        if checked:
            record['build_status'] = checked['build_status']
            record['local_validation'] = checked
    (args.output/'scope.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# 전체 취약 RPM의 upstream 재빌드 범위', '',
             f'- CSV 패키지 이름: **{len(records)}개** (누락 없이 포함)',
             f'- 배포판 Source RPM 묶음: **{len(projects)}개** (실제 upstream 프로젝트 수와 다를 수 있음)',
             '- 최신 안정판 확인은 공식 upstream 근거가 있는 항목에만 표기합니다.',
             ('- Source RPM 대응을 실제 대상 서버의 RPM 헤더로 확인했습니다.'
              if report['source_mapping_confirmed_from_host'] else
              '- 일부 Source RPM 대응은 Rocky EL8 참고값입니다. 실제 RHEL RPM 헤더 확인이 남아 있습니다.'),
             '- CSV의 과거 버전과 수집 시점의 설치 버전을 구분해 scope.json에 기록합니다.',
             '- 실제 대상 서버의 설치·부팅은 아직 검증하지 않았습니다.',
             '- 로컬 빌드·컨테이너 검증은 validation.json에 개별 기록합니다.', '',
             '| 소스 프로젝트 | 바이너리 패키지 수 | 최신 안정판 확인 | 검증 범위 |',
             '|---|---:|---|---|']
    for source, packages in sorted(projects.items()):
        latest = VERIFIED.get(source)
        version = f'[{latest[0]}]({latest[1]})' if latest else '확인 대기'
        lines.append(f"| {source} | {len(packages)} | {version} | {packages[0]['required_validation']} |")
    lines.extend(['', f'## 전체 {len(records)}종의 개별 대응', '',
                  '| 설치 패키지 | 소스 프로젝트 | 대응 근거 |', '|---|---|---|'])
    for record in records:
        lines.append(f"| {record['package']} | {record['source_project'] or '확인 필요'} | {record['mapping_evidence']} |")
    (args.output/'SCOPE.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({
        'packages': len(records), 'projects': len(projects),
        'unresolved': [r['package'] for r in records if not r['source_project']],
        'categories': dict(collections.Counter(r['category'] for r in records)),
        'latest_verified_projects': sorted(set(VERIFIED) & set(projects)),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
