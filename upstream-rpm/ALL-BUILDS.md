# 전체 RPM 제작 결과: 20260924-7

[바이너리·SRPM 다운로드](https://github.com/emotionbug/slop/releases/tag/upstream-rpm-all-builds-20260924-7)
와 [Trivy 통합 번들](https://github.com/emotionbug/slop/releases/tag/trivy-native-rpm-20260924-3).

- 바이너리 RPM **342개**, 대응 소스 RPM **162개**.
- 원래 140개 Source RPM 묶음 중 **134개**에 대응하는 산출물을 만들었습니다.
  별도 경로 또는 일부 라이브러리만 만든 경우도 포함합니다.
- 원래 323개 패키지 이름 중 **201개**와 동일한 이름의 RPM이 있습니다.
  이것은 323개 전체 교체·호환성 통과·취약점 해결 수치가 아닙니다.
- 개별 파일, 해시, 출처와 검증 제한은 [BUILD-CATALOG.json](BUILD-CATALOG.json)에 기록했습니다.
  실제 서버 인벤토리·취약점 CSV·사용자 파일·키·실행 로그는 배포하지 않습니다.

## 다운로드 구성

- `el8-all-binary-rpms-20260924-7.tar.gz`: 전체 바이너리 평가본과 공개 산출물 카탈로그.
- `el8-all-source-rpms-20260924-7-partNN.tar.gz`: 대응 소스 RPM. 재빌드할 때 필요하며 서버 검사에는 필요 없습니다.
- `SHA256SUMS`: 배포 파일 체크섬. 자체 RPM은 미서명이며 공식 UBI 패키지와 구분됩니다.
- 일반적인 검토 시작점은 전체 묶음 대신 별도의 [77 RPM 평가 묶음](CANDIDATES.md)입니다.

**전체 디렉터리를 `dnf upgrade *.rpm`으로 적용하지 마세요.** SONAME/API 전환,
서비스 설정 변경, 보안 정책과 커널·부트로더 연동이 포함되어 있습니다.
이 릴리스는 제작 가능한 산출물을 모은 평가 자료이며 일괄 서버 업그레이드 저장소가 아닙니다.

## 검증 범위

77 RPM 묶음은 UBI 8.10 참조 컨테이너에서 실제 DNF 설치·`dnf check`와 실행 검사 10개를 통과했습니다.
대상 헤더와 비교한 이름 기반 의존성 누락과 downgrade는 0개입니다.
파일/rich dependency 1,188개는 정적 검사로 판단하지 않았습니다.
Samba 클라이언트 의존성 일부는 참조 컨테이너용 Rocky 8 fixture이며 대상 서버에 배포하지 않습니다.

확장 묶음 전체를 한 시스템에 설치한 것은 아닙니다. 일부는 upstream 테스트 실패가 남아 있고
컴파일 결과를 평가할 수 있도록 체크 단계를 재실행하지 않고 패키징했습니다.
기존 실패를 지우거나 통과로 바꾸지 않았습니다. GCC, GTK, NetworkManager, OpenJPEG,
binutils, Pango, librsvg, BIND 등의 제한은 개별 카탈로그에 표시합니다.

GCC·glibc·Python·Perl·OpenSSL·RPM6·Samba·SSSD·RHSM·fwupd 등의 `linuxoss-*`는 주로
`/opt/linux-oss`의 별도 경로 평가본입니다. 기존 시스템 RPM은 별도로 남으므로 그 취약점이
조치된 것으로 계산하지 않습니다. fwupd는 라이브러리만 제작했고 펌웨어 갱신 기능을 제공하는
데몬 교체본이 아닙니다. Java 8은 컴파일·암호·TLS·ZIP smoke 범위이고 실제 Tomcat은 미검증입니다.
커널은 기본 QEMU 부팅만 확인했으며 실제 서버 부팅·VMware·SSH·보안 에이전트는 미검증입니다.

MCPP는 [정확한 패치 및 두 재현 입력의 메모리 검사 근거](MCPP-EVIDENCE.md)를 별도로 남겼습니다.

## 남는 제한

교체 산출물이 없는 Source RPM 묶음: linux-firmware, microcode_ctl, mozjs60, shim, subscription-manager-rhsm-certificates, systemd.

- systemd 최신 계열은 EL8보다 높은 glibc/kernel 전제가 있어 PID 1을 교체하는 빌드를 완료하지 않았습니다.
- mozjs60 소비 프로그램은 최신 SpiderMonkey와 API/SONAME이 달라 단순 대체할 수 없습니다.
- linux-firmware·microcode는 주로 제조사가 배포하는 바이너리 데이터입니다. 소스 재컴파일로 수정할 수 없습니다.
- shim의 자체 빌드는 제조사 Secure Boot 서명을 재현하지 못합니다.
- RHSM CA 인증서 묶음은 데이터입니다. 인증서를 재포장해 보안 수정으로 표시하지 않습니다.

실제 서버에는 아직 이 전체 제작본을 설치하지 않았고 업데이트 후 Trivy 검사도 수행하지 않았습니다.
서버의 DNF 예정 작업·심볼 참조·부팅 및 Java/Tomcat 확인을 거쳐 적용 범위를 정해야 합니다.
