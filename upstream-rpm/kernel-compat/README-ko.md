# EL8 보안 모듈 호환 커널 후보 — 2026-09-26

> **작업 목표 정정:** 최종 목표는 Linux **7.2.7**입니다. 이 문서의 EL8 `.168`
> 결과는 별도 비교 실험이며, 7.2.7 전환의 필수 설치 단계가 아닙니다.
> [7.2.7 작업 상태](../kernel-deploy/TARGET-7.2.7.md)를 기준으로 진행합니다.

`4.18.0-553.168.1.linuxoss1.el8_10.x86_64`는 EL8 .168 소스에 NFQUEUE 구조체
호환 패치를 적용한 병렬 설치 후보입니다. **7.2.7이 아니며, 기존 커널 CVE 전체를
해결하지 않습니다.** 현재 실행 중인 .166 커널과 기존 부팅 기본값을 유지합니다.

## 실제 수정 범위

Rocky의 공식 서명이 검증된 `kernel-4.18.0-553.168.1.el8_10.src.rpm`의 소스와
설정을 기반으로 빌드했습니다. Red Hat의 다음 두 보안 공지에 해당하는 수정이
.166 대비 포함됩니다.

- [RHSA-2026:71213](https://access.redhat.com/errata/RHSA-2026:71213):
  CVE-2026-43370, 63831, 64564, 72261, 80844, 81000, 89846.
- [RHSA-2026:71329](https://access.redhat.com/errata/RHSA-2026:71329):
  CVE-2026-31566, 52912, 68121, 80714, 89480.

이것은 자체 빌드 RPM이며 Red Hat 서명·지원 또는 FIPS 인증을 뜻하지 않습니다.

## 호환성 보완

CVE-2026-52912의 saved-device 참조 보존을 제거하지 않고, 추가 포인터를 공개
`nf_queue_entry` 구조체에서 할당 영역 끝의 정렬된 private storage로 이동했습니다.
복제 시에도 함께 복사하며, 장치 해제·NETDEV_DOWN 경로는 같은 getter를 사용합니다.
vermagic이나 심볼 CRC를 조작하거나 모듈 강제 로드를 사용하지 않았습니다.

대상 서버가 제공한 심볼 목록과 비교한 결과:

| 대상 | 일치 | CRC 불일치 |
|---|---:|---:|
| gc_enforcement kernel imports | 161 | 0 |
| dsa_filter kernel imports | 120 | 0 |
| dsa_filter_hook kernel imports | 39 | 0 |
| dsa_filter → dsa_filter_hook imports | 8 | 0 |

심볼 일치는 전체 에이전트 기능 검증과 다릅니다. 이후 서버의 실제 바이너리를
받아 Guardicore와 Trend 8491의 동시 로드·ICMP/TCP/UDP·해제를 격리 QEMU에서
통과했습니다. [추가 분석과 모듈 준비 방법](SERVER-MODULES-20260926.md)을
확인하세요. 전체 에이전트와 운영 정책 집행은 아직 시험하지 못했습니다.

## 완료한 검증

- GCC 8.5 / EL8 binutils 2.30로 커널·전체 모듈 빌드.
- 격리 QEMU에서 실제 커널 부팅.
- NFQUEUE에서 패킷을 보류한 채 bridge/veth를 삭제하고 늦은 verdict를 처리하는
  회귀 시나리오 통과. Oops/BUG 없음.
- 공식 Trend Micro EL8 KSP의 `dsa_filter 12.6.0.8527`와 hook 모듈을
  강제 옵션 없이 로드하고 해제하는 시험 통과.
- EL8 컨테이너에서 두 RPM 실제 설치·재설치·`rpm -V` 통과.
- devel RPM으로 외부 시험 모듈 빌드 통과.

최종 포장에서는 devel의 불필요한 `perl` 전체 묶음 의존성을 `/usr/bin/perl`로
바로잡았습니다. 원래 부팅 시험한 커널·모듈·개발 파일의 해시, 권한, 소유자,
심볼릭 링크는 유지했습니다. RPM 자동 생성 디렉터리의 artifact 표시만 차이가 있습니다.
이 최종 RPM으로 OpenSSL/glibc 동시 업그레이드 환경에서 DNF 설치, `rpm -V`,
외부 모듈 빌드도 통과했습니다.

최초 Trend 시험은 공개 KSP 8527 기준이고, 이후 실제 서버의 8491과 Guardicore
바이너리로 추가 시험했습니다. 전체 ds_agent/Guardicore 사용자 공간 프로그램,
관리 서버 연결, 보호 정책을 검증한 것은 아닙니다.
Secure Boot 및 대상 VMware 부팅도 아직 검증하지 않았습니다.

## 배포 동작

RPM 이름은 `kernel-linuxoss-el8-compat` 및 `kernel-linuxoss-el8-compat-devel`입니다.
기존 `kernel`, `kernel-core`, `kernel-modules`, `kernel-headers`를 교체하지 않습니다.
RPM 설치는 파일 배치와 depmod만 수행합니다. initramfs 생성, GRUB 변경,
기본 커널 변경, 재부팅을 하지 않습니다. 따라서 설치만으로 실행 중 커널의
취약점이 수정되지는 않습니다.

SSH만 가능한 서버에서 부팅 전 멈춤까지 자동 복구한다고 보장할 수 없습니다.
7.2.7의 활성 외부 모듈 검사도 그대로 유지합니다. ABI가 다른 모듈에
`--force-vermagic`, `--force-modversion`을 적용하지 마세요.

## 재현과 스캔

SRPM에 전체 소스, 설정, 패치와 spec이 포함됩니다. `rpmbuild --rebuild`는
전체 커널 빌드를 수행합니다. 배포 spec의 `linuxoss_prebuilt`는 검증된 기존
빌드 트리를 재포장하기 위한 내부 옵션입니다.

Trivy에는 정확한 RPM/SRPM 및 변경 불가 파일 해시를 연결합니다. 위 12건 외의
기존 커널 CVE는 별도 근거 없이 해결 처리하지 않습니다. 실행 중인 커널과
설치만 된 다른 커널의 결과도 분리합니다.
