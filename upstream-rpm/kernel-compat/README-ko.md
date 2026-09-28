# EL8 보안 커널 호환 배포 — linuxoss6

최종 커널은 `4.18.0-553.168.1.linuxoss2.el8_10.x86_64`, RPM 릴리스는
`4.18.0-553.168.1.linuxoss6.el8_10`입니다. RHEL 8.10 `.168.1` 소스에
검증된 수정들을 백포트하고, 기존 커널과 나란히 설치되는 install-only RPM으로
만들었습니다. 설치 스크립트는 기본 부팅 항목을 바꾸거나 재부팅하지 않습니다.

## 완료된 검증

- BTF 활성 설정과 pahole 1.22로 전체 커널 및 모듈 2,804개 빌드 통과
- 서버 프로필 요청 67개와 의존성 폐쇄를 반영해 모듈 69개 유지, 누락 0개
- 비공개 보안 모듈 3개의 import 328개가 old-known-good 및 최종
  `Module.symvers`에서 모두 일치, missing/CRC mismatch 0개
- 격리 QEMU에서 동시 로드, 네트워크, 해제, 재로드 4개 marker 통과
- module format 오류, unknown symbol, Oops/BUG/KASAN/panic/CPU warning 0건
- 실제 EL8 환경에서 kernel/devel RPM 동시 설치, `kmod` 의존성, scriptlet,
  `depmod`, 외부 모듈 smoke test 통과
- SSH 배포 제어기의 상태 조회, 복귀, 정상 commit, SSH·network 실패 시 fail-closed
  동작을 임시 경로와 명령 stub으로 검증; 테스트 중 reboot 호출 0건

상용 모듈 파일, 서명 프로필, 바이너리 해시 및 운영 경로는 공개 저장소와 공개
릴리스에 포함하지 않습니다. 공개 번들의 공개키로 별도 전달된 5파일 서명 overlay를
검증합니다.

## CVE 판정

기존 Trivy 자료에서 얻은 커널 고유 CVE 4,195개를 실제 최종 소스, 빌드 설정,
Red Hat VEX 및 Linux 수정 근거와 대조했습니다.

| 최종 상태 | CVE 수 |
|---|---:|
| `fixed` | 1,583 |
| `not_affected` | 2,612 |
| `affected` | 0 |
| 합계 | 4,195 |

`not_affected`는 공격 경로가 최종 빌드에 없거나 대상 코드/설정이 존재하지 않는
경우처럼 구체적인 근거가 있는 항목만 포함합니다. Raw Trivy 결과는 detector
관점의 별도 입력이며, 자체 RPM 이름 때문에 finding이 사라진 것을 수정으로 세지
않습니다. 공개 배포 번들의 `TRIVY-ACCOUNTING.md`, `vulnerability-summary.csv`,
`openvex.json`에 두 관점을 함께 보존합니다.

### Trivy OpenVEX 적용

`openvex.json`은 검토된 의미 판정의 원본입니다. 스캔 스크립트는 먼저 VEX 없이
`trivy-raw.json`을 만들고, 그 보고서에 실제로 기록된
`kernel-linuxoss-el8-compat`의 이름·버전·PURL을 읽어
`openvex.exact.json`을 생성합니다. 따라서 RHEL namespace와 distro qualifier를
추측하지 않습니다. 기존 `kernel`, `kernel-core`, `kernel-headers`, 롤백 커널,
이전 linuxoss 빌드는 VEX 대상에 자동으로 추가하지 않습니다.

```bash
sudo bash scan-kernel-vex.sh /path/to/trivy /path/to/cache /var/log/linuxoss-trivy/run-001 both
```

마지막 인자는 다음 중 하나입니다.

- `final`: VEX 적용 후 남은 finding만 `trivy-final.json`에 기록
- `audit`: 억제 항목을 `ExperimentalModifiedFindings`로 포함한
  `trivy-audit.json` 기록
- `both`: 두 결과를 모두 생성하는 기본값

모든 모드에서 변경하지 않은 `trivy-raw.json`, 실제 PURL로 묶은
`openvex.exact.json`, `openvex-binding-summary.json`을 함께 남깁니다. 정확한
커스텀 런타임 RPM이 스캔 결과에 없거나 버전이 다르면 스크립트는 VEX를 만들지 않고
종료합니다. 원시 결과의 기존 커널 finding을 커스텀 커널의 판정으로 숨기지 않기
위한 fail-closed 동작입니다.

## RPM

현재 릴리스 파일은 다음 두 개입니다.

- `rpms/kernel-linuxoss-el8-compat-4.18.0-553.168.1.linuxoss6.el8_10.x86_64.rpm`
- `rpms/kernel-linuxoss-el8-compat-devel-4.18.0-553.168.1.linuxoss6.el8_10.x86_64.rpm`

이전 linuxoss5 RPM은 재현 및 비교를 위해 같은 디렉터리에 보존합니다.
`SHA256SUMS`에서 네 RPM의 해시를 확인할 수 있습니다. RPM은 로컬 빌드이며 Red Hat
서명·지원 또는 FIPS 인증을 의미하지 않습니다.

## SSH 전용 배포

공개 번들과 별도 비공개 overlay를 서버에 옮긴 뒤 먼저 체크섬을 확인합니다.

```bash
sha256sum -c SHA256SUMS
sudo bash server-profile-ssh-deploy.sh --status
sudo bash server-profile-ssh-deploy.sh --install \
  --profile-overlay /secure/path/linuxoss6-private-module-overlay.tar.gz
sudo bash server-profile-ssh-deploy.sh --arm-next-boot
```

위 명령들은 재부팅하지 않습니다. `--arm-next-boot`는 새 커널을 다음 부팅 한 번에만
선택하고 기존 기본 커널을 저장합니다. 사용자가 직접 재부팅한 뒤 boot guard가
SSH, network, 서명된 모듈 프로필과 선택 서비스 상태를 모두 확인해야 최종 커널을
기본값으로 고정합니다. 실패하면 저장된 기본 커널을 복원하고 다음 재시작에 사용합니다.

수동 상태 확인과 복귀도 가능합니다.

```bash
sudo bash server-profile-ssh-deploy.sh --status
sudo bash server-profile-ssh-deploy.sh --rollback
```

실제 VMware 부팅, 운영 관리 서버 연결, 전체 사용자 공간 정책 집행, Java daemon과
Tomcat 업무 기능은 대상 서버에서 최종 확인해야 합니다. VMware가 완전히 정지했고
watchdog과 콘솔이 모두 없으면 SSH만으로 전원을 다시 넣을 수는 없습니다.

## 파일 역할

- `kernel-linuxoss-el8-compat-linuxoss6.spec`: 최종 linuxoss6 재현용 spec
- `linuxoss6-krel-linuxoss2-combined.patch`: 최종 소스 변경 묶음
- `kernel-compat-linuxoss2.config`: 최종 빌드 설정
- `server-profile-module-manifest-final.json`: 빌드·모듈·RPM·CVE 검증 근거
- `server-profile-ssh-deploy.sh`: 설치, one-shot 부팅, commit, rollback dispatcher
- `install-private-module-overlay.py`: 별도 서명 overlay 검증 및 설치
- `stage-reviewed-modules.py`: 실행/대상 커널과 import/export CRC 사전검사
