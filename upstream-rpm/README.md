# RHEL 8 전체 취약 RPM의 upstream 재빌드 작업

대상은 제공된 취약점 CSV의 **323개 패키지 이름 전체**입니다. rsync, GCC, 커널,
glibc, OpenSSL을 포함하며 위험도가 높다는 이유로 분석 대상에서 제외하지 않습니다.
현재 EL8 저장소 Source RPM 메타데이터로는 **140개 소스 패키지 묶음**입니다.
대상 서버의 Source RPM 헤더가 도착하기 전까지는 이 대응이 잠정적입니다.

## 현재 완료 범위

- 323개 이름을 모두 포함한 소스 프로젝트 대응표와 검증 분류 생성.
- 공식 upstream 공개 릴리스 후보 조회 도구 작성. 후보는 자동으로 빌드 버전에
  채택하지 않습니다. 실제 최신 안정판·유지보수 계열·API 전환 여부를 검토해야 합니다.
- Dockerfile 빌드 성공. 개발기의 Podman에서 검증했으며 Docker CLI 실행은 미검증입니다.
- rsync 3.5.1의 바이너리 RPM과 SRPM 생성. upstream 테스트 270개 통과, 90개 건너뜀.
- 별도 UBI 8.10에서 이전 rsync 설치 → 자체 RPM 업그레이드 → `dnf check` 통과.
- 로컬 복사 및 기존 rsync 3.1.3과의 송·수신 프로토콜 테스트에서 내용·심볼릭 링크·
  하드링크 보존 확인. 이는 로컬 파이프 테스트이며 실제 SSH/상대 서버 테스트가 아닙니다.

**323종 전체의 최신판 검토·RPM 제작·서버 적용은 완료되지 않았습니다.**
GCC/커널/glibc/OpenSSL 등 나머지 프로젝트별 SPEC과 역의존성 재빌드가 남아 있습니다.
커널·부트로더·systemd·PAM·SSSD 등은 컨테이너 테스트 외에 RHEL 8 VM의 부팅과
로그인 테스트가 필요합니다. 컨테이너는 호스트 커널을 공유하므로 커널 부팅을
검증하지 않습니다.

## 빌드 환경

UBI 8 공개 저장소에는 bison/flex 등 일부 빌드 의존성이 없었습니다. 따라서
**빌드 컨테이너에만 Rocky Linux 8.10 저장소**를 사용합니다. 대상 RHEL 서버에
Rocky 저장소를 추가하지 않습니다. 결과물은 별도 UBI 8에서 검증합니다.
이것은 Red Hat 공식 빌드/지원 인증을 의미하지 않습니다.

이미지 digest는 고정했으나 DNF 저장소 내용까지 스냅샷으로 고정한 것은 아닙니다.
현재 빌드의 전체 RPM 목록을 결과 폴더의 `builder-rpms.tsv`에 기록합니다.
동일 입력으로 바이트까지 동일한 결과가 나오는 재현 빌드는 아직 검증하지 않았습니다.

```powershell
# 이 폴더에서 실행. Docker가 없으면 아래 docker를 podman으로 바꿀 수 있습니다.
docker build --platform linux/amd64 -t linux-oss-upstream-builder:el8 .
python fetch-sources.py
New-Item -ItemType Directory -Path output/rsync -Force | Out-Null
$recipePath = (Get-Location).Path
docker run --rm --network=none --security-opt=no-new-privileges `
  -v "${recipePath}:/recipe:ro" `
  -v "${recipePath}/sources:/sources:ro" `
  -v "${recipePath}/output/rsync:/output" `
  linux-oss-upstream-builder:el8 bash /recipe/build-rpm.sh /recipe/specs/rsync.spec
```

SPEC마다 별도 빌드와 검증이 필요합니다. `build-rpm.sh`는 지정한 SPEC만 빌드하고,
의존성이나 테스트가 실패하면 중단합니다.

## rsync 검증용 RPM의 현재 범위

- 자체 Vendor/Release를 가진 검증용 RPM이며 Red Hat 서명이 없습니다.
- rsync 소스는 공식 릴리스 서명을 검증했습니다. RPM 자체는 미서명 상태이고,
  `rpmkeys --checksig`로 확인한 것은 다이제스트입니다.
- xxHash 0.8.4를 정적으로 포함하며 `Provides: bundled(xxhash)`와 SRPM에 기록합니다.
- 현재 EL8의 `libcrypto.so.1.1` 등에 연결됩니다. OpenSSL까지 최신화한
  전체 교체 트랜잭션의 완성품은 아닙니다.
- 데몬 서비스와 rrsync는 이 검증용 패키지에 추가하지 않았습니다.
  기존 rsync-daemon 및 패키지 구성과의 호환성은 서버 정보로 확인해야 합니다.
- upstream 테스트 생략은 root/ASan/TCP/이전 peer 등의 조건에 따른 것입니다.
  모든 보안 조건의 검증 완료를 의미하지 않습니다.
- Trivy가 자체 RPM을 탐지하지 못한 것을 취약점 해결로 판정하지 않습니다.

## 다음 단계에 필요한 서버 정보

[INVENTORY.md](INVENTORY.md)의 읽기 전용 스크립트로 Source RPM과
Requires/Provides/Conflicts/Obsoletes를 수집합니다. CSV에는 취약점이
표시되지 않은 의존 패키지와 아키텍처, 모듈 구성 정보가 부족합니다.

출력 파일, CSV, 서버 수집 정보는 공개 Git 저장소에 추가하지 마세요.
