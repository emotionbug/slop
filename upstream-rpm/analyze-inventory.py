#!/usr/bin/env python3
"""Private host inventory analysis; capability matching is not a DNF solver."""
import argparse
import collections
import csv
import hashlib
import json
import pathlib


def read_tsv(root, name):
    with (root/name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def analyze(root, findings_path):
    packages = read_tsv(root, 'packages.tsv')
    requires = read_tsv(root, 'requires.tsv')
    provides = read_tsv(root, 'provides.tsv')
    by_name = collections.defaultdict(list)
    for package in packages:
        by_name[package['name']].append(package)
    families = {
        'glibc': {'glibc', 'glibc-common', 'glibc-devel', 'glibc-headers'},
        'openssl': {'openssl', 'openssl-libs', 'openssl-devel'},
        'gcc-runtime': {'libgcc', 'libstdc++', 'libgomp'},
        'binutils': {'binutils'},
        'rsync': {'rsync'},
        'rpm': {'rpm', 'rpm-libs', 'rpm-build-libs', 'python3-rpm'},
        'platform-python': {'platform-python', 'python3-libs'},
    }
    reverse = {}
    for family, names in families.items():
        caps = {p['capability'] for p in provides if p['name'] in names}
        matches = [r for r in requires if r['capability'] in caps and r['name'] not in names]
        reverse[family] = {
            'direct_consumer_count': len({r['name'] for r in matches}),
            'direct_consumers': sorted({r['name'] for r in matches}),
            'matching_requirements': matches,
        }
    old_crypto = [r for r in requires if r['capability'].startswith(('libssl.so.1.1', 'libcrypto.so.1.1'))]
    platform = (root/'platform.txt').read_text()
    running_kernel = next(line.split('=', 1)[1] for line in platform.splitlines() if line.startswith('running_kernel='))
    stale = collections.Counter()
    current = collections.Counter()
    with findings_path.open(encoding='utf-8-sig', newline='') as handle:
        findings = list(csv.DictReader(handle))
    for row in findings:
        versions = {('' if p['epoch'] == '0' else p['epoch']+':')+p['version']+'-'+p['release']
                    for p in by_name[row['패키지명']]}
        counter = current if row['설치버전'] in versions else stale
        counter[row['패키지명']] += 1
    modules = [line.split()[0] for line in (root/'loaded-modules.txt').read_text().splitlines()[1:] if line.split()]
    services = [line.split()[0] for line in (root/'service-states.txt').read_text().splitlines()
                if len(line.split()) >= 2 and line.split()[1] == 'enabled']
    config = root/('config-'+running_kernel)
    essential = ['CONFIG_VMWARE_PVSCSI', 'CONFIG_VMXNET3', 'CONFIG_XFS_FS', 'CONFIG_BLK_DEV_DM',
                 'CONFIG_EFI', 'CONFIG_EFI_STUB', 'CONFIG_DEVTMPFS', 'CONFIG_VFAT_FS', 'CONFIG_BLK_DEV_INITRD']
    config_values = {}
    for line in config.read_text().splitlines():
        if '=' in line:
            name, value = line.split('=', 1)
            if name in essential:
                config_values[name] = value
    return {
        'inventory_directory': str(root),
        'packages_tsv_sha256': hashlib.sha256((root/'packages.tsv').read_bytes()).hexdigest(),
        'installed_rpm_records': len(packages), 'installed_package_names': len(by_name),
        'architecture_counts': dict(collections.Counter(p['arch'] for p in packages)),
        'running_kernel': running_kernel, 'boot_mode': (root/'boot-mode.txt').read_text().strip(),
        'secure_boot': (root/'secure-boot.txt').read_text().strip(),
        'csv_rows_for_versions_absent_from_inventory': dict(stale),
        'csv_rows_matching_installed_versions': sum(current.values()),
        'csv_current_rows_are_not_a_rescan': True,
        'third_party_vendor_packages': [p for p in packages if p['vendor'] not in ('Red Hat, Inc.', '(none)')],
        'enabled_service_names': services, 'enabled_is_not_running': True,
        'loaded_modules': modules, 'required_kernel_config_from_current_host': config_values,
        'reverse_dependencies_by_capability_name': reverse,
        'openssl_1_1_direct_consumers': sorted({r['name'] for r in old_crypto}),
        'analysis_limit': 'Capability-name matches only. Does not solve RPM version/rich/file dependencies or identify dlopen/JNI/private agent runtimes. Not an installation approval.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inventory', type=pathlib.Path)
    parser.add_argument('csv', type=pathlib.Path)
    parser.add_argument('--output', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent/'output')
    args = parser.parse_args()
    report = analyze(args.inventory, args.csv)
    args.output.mkdir(exist_ok=True, parents=True)
    (args.output/'host-analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# 실제 서버 RPM과 빌드 조건', '',
             f"- 설치 RPM 레코드 {report['installed_rpm_records']}개 / 이름 {report['installed_package_names']}개.",
             f"- 실행 커널: `{report['running_kernel']}`.",
             f"- {report['boot_mode']}, {report['secure_boot']}.",
             f"- CSV의 과거 버전 행 {sum(report['csv_rows_for_versions_absent_from_inventory'].values()):,}개는 현재 설치 목록과 불일치.",
             '- 이것은 버전 대조이며 취약점 재검사 결과가 아닙니다.', '',
             '| 교체 구성요소 | 직접 의존하는 다른 패키지 이름 수 |', '|---|---:|']
    for family, value in report['reverse_dependencies_by_capability_name'].items():
        lines.append(f"| {family} | {value['direct_consumer_count']} |")
    lines.extend(['', '## 서버에 설치된 외부 공급업체 패키지', ''])
    for package in report['third_party_vendor_packages']:
        lines.append(f"- `{package['name']}` {package['version']}-{package['release']} ({package['vendor']})")
    lines.extend(['', '이들의 커널·libc 호환성은 RPM 헤더만으로 확정할 수 없습니다.',
                  '서비스 enabled 표시는 실행 중이라는 뜻이 아닙니다.', '',
                  '## 최신 커널 설정에 유지할 조건', ''])
    for name, value in report['required_kernel_config_from_current_host'].items():
        lines.append(f'- `{name}={value}`')
    lines.extend(['', 'VMware PVSCSI/VMXNET3, XFS, device mapper, EFI 부팅 조건을 검증해야 합니다.',
                  '위 의존성 수는 capability 이름 매칭입니다. RPM 버전·파일·rich dependency 해결과 실제 VM 부팅을 대신하지 않습니다.',
                  '이 문서와 입력 수집 파일은 비공개로 유지합니다.', ''])
    (args.output/'HOST-ANALYSIS.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['installed_rpm_records', 'installed_package_names', 'running_kernel', 'csv_rows_for_versions_absent_from_inventory', 'csv_rows_matching_installed_versions']}, ensure_ascii=False))
    print(json.dumps({k:v['direct_consumer_count'] for k,v in report['reverse_dependencies_by_capability_name'].items()}))


if __name__ == '__main__':
    main()
