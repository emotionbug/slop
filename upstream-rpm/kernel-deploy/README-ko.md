# Linux 7.2.7 커널 추가 설치 묶음

기존 `linuxoss-install-20260925-6` 사용자 공간 패키지 묶음에 이어 적용하는
**별도 커널 묶음**입니다. Linux 7.2.7 소스로 만든 `kernel`과 동일 버전
`kernel-devel`을 추가합니다. RHEL 커널·모듈·개발용 RPM을 지우지 않고,
glibc용 `/usr/include`의 `kernel-headers`도 바꾸지 않습니다.

`uname -r`에서 확인할 새 버전은 **7.2.7-linuxoss+**입니다.
RPM Release 3은 EL8의 cgroup v1 메모리 제어를 다시 켠 빌드입니다.
기존 평가용 Release 2에서 서비스 메모리 제한 경로가 생기지 않는 문제를 재현했고,
새 빌드에는 `CONFIG_MEMCG_V1=y`와 기존 BTF·드라이버 설정을 함께 반영했습니다.
이 커널은 Red Hat이 서명·지원하는 커널이나 RHEL kABI 호환 커널이 아닙니다.
설치 중에는 기존 기본 부팅 커널을 유지하며 자동 재부팅하지 않습니다.

## 프록시로 다운로드하고 설치

다음 명령은 새 디렉터리에 다운로드하고, 스크립트에 고정한 SHA-256을 확인한 후
커널 RPM 2개만 추가합니다. 의존 패키지를 제거하거나 외부 저장소에서 받지 않습니다.

```bash
wget -e use_proxy=yes -e https_proxy=http://192.168.32.104:9080 \
  -O download-kernel.sh \
  https://raw.githubusercontent.com/emotionbug/slop/main/upstream-rpm/kernel-deploy/download-kernel.sh
sudo bash download-kernel.sh apply
```

설치 전에 결과만 보려면 마지막 인수를 `check`로 바꿉니다.
설치가 끝나면 출력된 `Kernel kit retained at:` 디렉터리로 이동합니다.
로그는 `/var/log/linuxoss-kernel/run-*/kernel.log`에 남습니다.

## SSH만 가능한 서버에서 적용

`linuxoss-kernel-20260925-2`는 기존과 동일한 커널 RPM에 **확정 제한시간과 복귀 서비스**를
추가한 묶음입니다. 커널의 정상 부팅을 보장하는 장치는 아니며, 펌웨어·GRUB·커널이
완전히 멈춰 타이머도 실행되지 않으면 SSH만으로 복구할 수 없다는 제한은 남습니다.

설치가 성공한 뒤 출력된 키트 디렉터리에서 아래 명령으로 예약하고 재부팅합니다.
현재 SSH 연결을 처리하고 있는 실행 중 커널을 복귀 대상으로 선택합니다.
이전에 RPM 업데이트만 하여 아직 부팅하지 않은 커널이 기본값으로 잡혀 있어도,
그 버전 대신 현재 실행 중인 커널로 돌아가도록 기록합니다.

```bash
sudo bash kernel.sh boot-once-remote && sudo reboot
```

예약이 성공한 경우에만 재부팅합니다. 예약 상태부터 확인하려면 `&& sudo reboot`를
빼고 실행한 뒤 `sudo bash kernel.sh status`를 확인하세요.

새 커널에서 다음과 같이 동작합니다.

- 커널 패닉: `panic=60`으로 60초 후 재부팅하도록 설정합니다. kdump 등 별도
  패닉 처리 경로에서 멈추는 경우까지 보장하지는 않습니다.
- dracut 복구 실패: `rd.shell=0 rd.emergency=reboot`를 적용합니다.
  initqueue 재시도는 180초, 장치 대기는 240초로 제한합니다.
- 사용자 공간까지 진입했으나 **커널 부팅 후 20분 안에 직접 확정하지 않으면**
  기존 커널로 재부팅합니다. SSH 서비스가 활성인지 여부만으로 성공 판정하지 않습니다.
- 기존 커널의 부팅 인수는 바꾸지 않습니다. 기존 커널로 돌아오면 재시도를 반복하지 않습니다.

SSH로 다시 접속하면 설치 키트 디렉터리에서 현재 커널과 실제 서비스 상태를 확인하고,
20분 이내에 확정합니다. `status`의 `seconds_remaining`에서 남은 시간을 확인할 수 있습니다.

```bash
uname -r                 # 7.2.7-linuxoss+ 확인
sudo bash kernel.sh status
systemctl --failed
# 실제 Java daemon·Tomcat의 서비스와 응답을 확인한 뒤 실행
sudo bash kernel.sh confirm
```

확정하면 타이머를 해제하고 새 커널을 기본값으로 설정합니다. 확정하지 않으면
서비스가 정상이어도 복귀를 위해 재부팅하므로, 접속한 채 방치하지 마세요.
복귀 시 우선 정상 종료를 요청하고, 120초 후에도 복귀 프로세스가 실행 중이면
`systemctl --force reboot`로 종료를 강화합니다. 이 단계에서는 서비스 종료 절차가
생략될 수 있습니다. 완전 정지에는 하이퍼바이저 측 복구 수단이 필요합니다.

재부팅 전에 취소하려면 `sudo bash kernel.sh fallback`을 실행합니다.
부팅 후에도 이 명령은 기존 기본값을 복원하고 타이머를 취소하며, 자체 재부팅은 하지 않습니다.

관련 로그와 상태:

```bash
sudo journalctl -u linuxoss-kernel-guard.service --no-pager
sudo cat /var/lib/linuxoss-kernel/remote-boot.json
```

구현 근거: [커널 panic 매개변수](https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html),
[dracut 부팅 인수](https://github.com/dracutdevs/dracut/blob/049/dracut.cmdline.7.asc).

## 새 커널로 한 번 부팅하고 확정

다음은 복귀 타이머가 없는 기존 방식입니다. 키트 디렉터리에서 실행합니다.
SSH 연결이 끊기거나 부팅이 멈추었을 때 접근할
VMware 콘솔을 사용할 수 있는 작업 시간에 진행합니다.

```bash
sudo bash kernel.sh boot-once
sudo reboot
```

GRUB은 다음 부팅 한 번에만 새 커널을 선택합니다. 그 다음 부팅의 기본값은
기존 커널입니다. 새 커널 부팅 자체가 멈추면 콘솔에서 재시작해야 하며,
이 기능이 멈춘 서버를 자동으로 재부팅해 주지는 않습니다.

다시 접속한 뒤 새 커널과 실제 Java daemon·Tomcat·보안 에이전트 상태를 확인합니다.

```bash
uname -r
systemctl --failed
sudo bash kernel.sh status
# 실제 서비스와 연결 상태가 정상일 때만 기본 커널로 확정
sudo bash kernel.sh confirm
```

기존 커널로 돌아갈 때는 아래 명령을 사용합니다. 새 RPM은 남겨 둡니다.

```bash
sudo bash kernel.sh fallback
sudo reboot
```

## 설치 전 호환성 확인

설치기는 RHEL 8 x86_64, UEFI/BLS, Secure Boot 비활성 상태를 확인합니다.
새 커널에 실제 PCI 장치 드라이버가 있는지, XFS 형식과 initramfs, 현재 machine-id와 BLS 항목의 일치, 기존 부팅
이미지 및 공간을 확인합니다. FIPS, XFS V4/ASCII-CI, 활성 VDO, 로드된 외부
커널 모듈은 현재 산출물과 호환된다는 근거가 없으므로 변경 전에 멈춥니다.
이 경우 로그에 표시된 기능을 보완한 커널/외부 모듈 빌드가 필요하며,
보안 설정을 끄거나 의존성을 무시해서 진행하지 않습니다.

특히 보안 에이전트가 외부 모듈을 사용하는 경우 제조사 소스나 7.2용 지원 모듈이
필요합니다. `kernel-devel`을 함께 제공하지만, 개발용 헤더만 설치한다고
RHEL 4.18용 모듈이 7.2에서 동작하는 것은 아닙니다.

## Trivy 결과

키트의 `scan.sh`는 기존 Trivy 0.74.0과 로컬 취약점 DB를 사용합니다.

```bash
sudo bash scan.sh
# 자동 탐색이 안 되면
sudo bash scan.sh /실제/경로/trivy /실제/경로/cache
```

이번 모듈은 `7.2.7_linuxoss+`라는 RPM 버전과 upstream `7.2.7`을 정확히 연결하고,
커널 RPM이 CSV에서 빠지던 판정도 수정했습니다. 기존 커널을 보존하므로 해당
설치 RPM의 취약점은 계속 출력될 수 있습니다. 실제 기동 커널은 `uname -r`로
구분합니다. 새 커널도 전체 CVE 해결로 표시하지 않습니다. 확인된 패치·버전 범위와
미확인 항목을 구분하고 원본 Trivy 결과 및 `scan-gaps.csv`를 남깁니다.

## 재현 자료

- 부팅·설치·Trivy 검증 범위: [VALIDATION.md](VALIDATION.md), `VALIDATION.json`
- SSH 접속 확정·미확정 복귀·패닉 복귀 검증: `REMOTE-BOOT-VALIDATION.json`
- 정확한 RPM·커널 이미지 해시: `kernel-manifest.json`
- 소스와 빌드: 상위 디렉터리 `build-kernel.sh`, `repackage-kernel.sh`
- 시험용 EL8 이미지·부팅 코드: 이 디렉터리의 `Containerfile.*`, `fixture-*.sh`, `fixture-boot.py`
- 공식 upstream: https://www.kernel.org/
- RHEL 부팅 관리: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/managing_monitoring_and_updating_the_kernel/index

시험용 SSH 키·가상 디스크·실제 서버 인벤토리는 공개 키트에 포함하지 않습니다.

재빌드에는 `Containerfile.builder`의 binutils 2.47, dwarves 1.32 및 elfutils 개발
라이브러리를 사용합니다. 빌드 공간을 줄이기 위한 DWARF 압축을 사용하므로 EL8의
오래된 binutils 2.30으로는 링크에 실패할 수 있습니다. BTF는 계속 포함하며,
배포 모듈에서는 DWARF를 제거한 뒤 서명합니다.
