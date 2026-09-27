# EL8 Trend·Guardicore 호환 보안 커널 — 2026-09-27

배포 후보는 `4.18.0-553.168.1.linuxoss1.el8_10.x86_64`입니다. RHEL 8.10
`.168.1` 소스에 검증된 Linux stable 수정과 NFQUEUE kABI 보완을 적용해
`kernel-linuxoss-el8-compat`라는 별도 install-only RPM으로 만들었습니다. 기존
`.166` 커널과 기본 부팅 항목은 설치 단계에서 유지합니다.

7.2.7은 사용하지 않습니다. 서버에서 수집한 Guardicore와 Trend 바이너리는 7.2.7에서
kernel import 320개 중 다수가 없거나 CRC가 다르고, Guardicore가 직접 접근하는
`struct proto` callback 위치도 달랐습니다. 반면 이 `.168.1` 빌드에서는 세 모듈의
kernel import 328개가 모두 일치했습니다.

## 실제 모듈 시험

서버에서 수집한 다음 파일의 SHA-256을 고정했습니다. 파일 자체는 공개 저장소나
릴리스에 포함하지 않습니다.

- Guardicore `gc_enforcement`:
  `e5895f7a3148497dd809408a4acb2600df900d8eb95d61e8a4ad72ead1147dad`
- Trend hook:
  `198bb5c9c11c294f7122c85a48883d7e92ad255dc997ece83064c8316cb8e45c`
- Trend filter 12.6.0.8491:
  `abf6aea64fb58678d80387c2c000f5f9437e730f2a41843082c9f0130807d3b2`

최종 CVE 백포트 소스로 커널 전체와 모듈 2,804개를 다시 빌드했습니다. 그 커널을
격리 QEMU에서 실제로 부팅해 세 바이너리를 동시에 로드한 뒤 ICMP 3/3,
namespace 간 TCP/UDP echo, namespace 제거, 역순 모듈 해제를 통과했습니다.
vermagic·modversion 강제 옵션은 사용하지 않았고 Oops, BUG, KASAN, GPF 및
커널 WARNING은 없었습니다. 상세 해시는
[SERVER-MODULE-VALIDATION.json](SERVER-MODULE-VALIDATION.json)에 있습니다.

이 시험은 전체 `ds_agent`/`gc-guest-agent` 사용자 공간, 관리 서버 연결, 정책
allow/deny 및 실제 VMware 부팅을 대신하지 않습니다.

## CVE 판정

입력은 기존 Trivy CSV의 커널 고유 CVE 4,195개입니다. Linux CNA
`b5f074657ecf643c43102c5dbb151606efd6690d`, CVE List V5
`60251ab81d62f05055745b1b9222d5244ba8073f`, Red Hat CSAF VEX
`csaf_vex_2026-09-20.tar.zst`와 2026-09-27 증분을 고정했습니다.

| 최종 상태 | CVE 수 |
|---|---:|
| `fixed` | 1,355 |
| `not_affected` | 2,053 |
| `under_investigation` | 787 |
| 합계 | 4,195 |

`fixed`는 exact reverse apply, zero-fuzz hunk 일치 또는 대상 EVR 이하의 Red Hat
fixed 근거만 인정합니다. `not_affected`는 CNA 범위 밖, 명시적 unaffected 또는
정확한 빌드 설정에서 소스가 포함되지 않은 경우입니다. 의미가 비슷해 보이는 줄만
있는 경우는 해결로 올리지 않습니다.

남은 787개 중 786개는 최신 Red Hat VEX도 RHEL 8 커널을 `known_affected`로
표시하고, 한 건은 RHEL 8 일반 커널 진술이 없습니다. 따라서 이 빌드는 모든
4,195개 CVE를 해결했다고 주장하지 않습니다. 그 상태를 숨기지 않고 OpenVEX의
`under_investigation`으로 유지합니다. 정확한 목록과 근거는 배포 키트의
`el8-168-final-cve-accounting-kabi-final.json`에 있습니다.

## RPM

- `kernel-linuxoss-el8-compat-4.18.0-553.168.1.linuxoss2.el8_10.x86_64.rpm`
- `kernel-linuxoss-el8-compat-devel-4.18.0-553.168.1.linuxoss2.el8_10.x86_64.rpm`
- `kernel-linuxoss-el8-compat-4.18.0-553.168.1.linuxoss2.el8_10.src.rpm`

RPM 두 개의 오프라인 DNF transaction check/test/install, `rpm -V`, depmod,
modinfo를 격리 EL8 컨테이너에서 통과했습니다. SRPM에는 원본 소스, 설정, spec,
NFQUEUE kABI 패치와 전체 CVE 백포트 패치가 포함됩니다. 이 RPM은 Red Hat
서명·지원이나 FIPS 인증을 뜻하지 않습니다.

## SSH 전용 설치와 1회 부팅

키트 안에서 다음 한 번으로 RPM 설치, 현재 로드된 정확한 Trend·Guardicore
바이너리 복사, initramfs 생성 및 **다음 부팅 한 번만** 새 커널 선택까지
준비합니다.

```bash
sudo bash install-kernel-compat.sh
```

이 명령은 재부팅하지 않습니다. 현재 기본 커널도 바꾸지 않습니다. 준비가 끝난 뒤
사용자가 `sudo reboot`를 실행하면 GRUB `next_entry`로 한 번만 새 커널을
시도합니다. 새 커널에서 12분 안에 SSH, 기본 route와 세 보안 모듈의 정확한
version/srcversion이 확인되지 않으면 boot guard가 원래 기본 커널을 복원하고
재부팅합니다. 정상인 경우에도 영구 기본값은 자동 변경하지 않습니다.

SSH로 접속한 뒤 Java daemon과 Tomcat까지 확인해 영구 기본값으로 승격합니다.

```bash
sudo bash confirm-kernel.sh
```

프로세스 식별 규칙이 다른 경우 `LINUXOSS_JAVA_PATTERN`과
`LINUXOSS_TOMCAT_PATTERN` 환경변수로 `pgrep -af` 정규식을 지정할 수 있습니다.
되돌리기만 하려면 `sudo bash rollback-kernel-boot.sh`를 실행합니다.

`panic=60`, `nmi_watchdog=1`, `softlockup_panic=1`, `hung_task_panic=1`을 새
부팅 항목에만 넣습니다. 커널이 systemd까지 올라오지 못한 채 완전히 정지하고
VMware watchdog도 없는 경우에는 SSH만으로 재부팅시킬 방법이 없습니다. 1회 부팅
설정 덕분에 다음 물리적/가상 재시작은 원래 기본 커널로 돌아가지만, 정지한 VM을
원격에서 재시작하는 기능 자체를 만들 수는 없습니다.

## Trivy 연계

키트의 `scan-kernel-vex.sh`는 Trivy 0.74.0의 기존 오프라인 DB와 최종 OpenVEX를
사용해 rootfs를 검사하고, 원본 Trivy JSON·suppressed 항목·실행 커널·RPM 목록과
독립적인 4,195개 소스 판정 보고서를 같은 출력 디렉터리에 보존합니다.

```bash
sudo bash scan-kernel-vex.sh \
  /root/trivy/trivy \
  /root/trivy/trivy-proxy-work/cache \
  /root/trivy/kernel-report-20260927
```

OpenVEX는 기존 Trivy finding의 상태를 연결할 뿐 새 CVE를 만들지 않습니다.
자체 RPM이 Trivy vendor DB에 없어서 결과에서 사라진 것을 해결로 세지 말고,
`el8-168-final-cve-accounting-kabi-final.json`의 787개
`under_investigation`을 함께 확인해야 합니다.
