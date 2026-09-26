# EL8 호환 보안 백포트 배포 — 2026-09-26

기존 사용자 공간 릴리스 `linuxoss-install-20260925-6`에 이어 적용하는 추가 묶음입니다.
**OpenSSL 1.1.1과 glibc 2.28의 기존 ABI를 유지하면서 보안 수정을 추가**합니다.
커널은 별도 병렬 설치 묶음이며, 설치만으로 실행 커널이 바뀌지는 않습니다.

| 구성 | RPM | 실제 범위 |
|---|---:|---|
| 시스템 OpenSSL | 5 | 기존 CSV 23개 CVE의 공식 수정/문서 수정, 7개 정확한 비해당 근거, 1개 미해결 |
| glibc | 8 | 공식 CVE 수정 9개, 코드/분리 패키지 범위 비해당 4개 |
| EL8 `.168` 호환 커널 | 2 | `.166` 대비 공식 CVE 수정 12개와 NFQUEUE ABI 보완 |

이는 RPM별 중복 행을 합한 숫자가 아니며 운영 서버 적용·해결 수치도 아닙니다.
OpenSSL 23개 중 CVE-2023-0466은 upstream 문서 수정입니다. 인증서 정책 검사를
자동 활성화하는 변경은 아닙니다. glibc의 nscd 취약 소스는 수정하지 않았고,
이번 8개 split RPM에는 nscd 실행 파일이 없다는 범위만 판정합니다.

## 프록시 다운로드와 설치

```bash
wget -e use_proxy=yes -e https_proxy=http://192.168.32.104:9080 \
  -O download-backports.sh \
  https://raw.githubusercontent.com/emotionbug/slop/main/upstream-rpm/deploy/download-backports.sh
sudo bash download-backports.sh apply
```

설치 전 실제 DNF 예정 작업과 파일 충돌만 확인하려면 `apply` 대신 `check`를
사용합니다. 별도 애플리케이션 경로가 있으면 마지막에 추가할 수 있습니다.
로그와 반입 디렉터리는 실행 끝에 표시됩니다. 실패해도 자료는 남깁니다.

설치된 이름만 업그레이드하고, 필요한 로컬 의존 패키지를 함께 선택합니다.
외부 저장소 조회·패키지 삭제·다운그레이드·강제 의존성 무시는 하지 않습니다.
i686 등 제공하지 않은 아키텍처가 함께 설치되어 의존성이 맞지 않으면 멈춥니다.
자체 암호 라이브러리는 FIPS 인증 빌드가 아니므로 FIPS 활성 시스템에서는 적용하지 않습니다.

OpenSSL의 다중 수신자 RSA CMS/PKCS7 복호화는 보안 수정에 따라 수신자 인증서를
명시해야 합니다. [상세 사용 변경](../openssl-compat/README-ko.md)을 확인하세요.

## 커널 파일 추가 설치

**이 절은 EL8 `.168` 실험 묶음입니다. 현재 요청한 커널 목표는 7.2.7이며,
아래 명령은 그 전환에 필요하지 않습니다.** [7.2.7 상태](../kernel-deploy/TARGET-7.2.7.md)를
기준으로 진행합니다. 위 OpenSSL/glibc 사용자 공간 묶음과는 별개입니다.

```bash
wget -e use_proxy=yes -e https_proxy=http://192.168.32.104:9080 \
  -O download-kernel-compat.sh \
  https://raw.githubusercontent.com/emotionbug/slop/main/upstream-rpm/kernel-compat/download-kernel-compat.sh
sudo bash download-kernel-compat.sh apply
```

이 명령은 커널 파일과 devel RPM만 추가합니다. initramfs 생성, GRUB 변경,
기본 커널 변경 및 재부팅은 하지 않습니다. 실행 커널의 CVE 조치는 새 커널로
부팅하고 실제 서비스를 확인한 뒤에 판단해야 합니다.

공개 Trend KSP 8527 시험 이후 실제 서버의 Guardicore·Trend 8491 바이너리도
동시 로드·ICMP/TCP/UDP·해제를 통과했습니다. [추가 결과와 모듈 파일 준비](../kernel-compat/SERVER-MODULES-20260926.md)를
확인하세요. 전체 에이전트와 정책 집행은 아직 시험하지 못했습니다.
SSH만 접근 가능한 서버의 부팅 전 완전 정지를 자동 복구한다고 보장하지 않습니다.
[커널 근거와 한계](../kernel-compat/README-ko.md)를 함께 확인하세요.

## 적용 후 Trivy

설치 후 출력된 키트 디렉터리에서 실행합니다. 실행 중인 프로세스는 이전
라이브러리를 계속 사용할 수 있으므로 유지보수 시간에 Java/Tomcat 등 서비스를
재시작하고 실제 응답을 확인해야 합니다.

```bash
sudo bash scan.sh
# Trivy 경로를 자동으로 찾지 못하면:
sudo bash scan.sh /실제/경로/trivy /실제/경로/cache
```

- `actionable.csv`: 전체 미해결/검토 대상. 자체 RPM으로 이름이 바뀐 항목도 유지합니다.
- `running-kernel-actionable.csv`: 실행 커널 이미지의 RPM과 연결된 미해결 항목.
- `other-installed-kernel-actionable.csv`: 설치만 된 다른 커널의 항목.
- `native-review.csv`: 자체 RPM의 미해결/추가 검토 대상.
- `reviewed-resolutions.csv`: 정확한 RPM·SRPM·파일 해시와 수정/비해당 근거가 일치한 결과.
- `scan-gaps.csv`: 조회·매핑·파일 검증이 불완전한 범위.

정확한 7.2.7 Release 3 RPM에는 Linux CNA 수정 범위 3,985건을 연결했지만,
그 판정을 이 EL8 호환 커널에 복사하지 않습니다. 7.2.7과 활성 보안 모듈의
호환성이 해결되었다는 의미도 아닙니다. 대부분의 커널 CVE를 해결했다는
운영 판정은 아직 할 수 없습니다.

## 소스와 검증 자료

같은 GitHub 릴리스의 `linuxoss-backport-sources-20260926-1.tar.gz`에 전체 SRPM
3개, 패치와 spec, 테스트 근거를 담습니다. 서버 인벤토리, 상용 보안 모듈,
운영 키는 포함하지 않습니다. OpenSSL 공식 공개 테스트의 입력·키 fixture는
소스 재현용으로 포함합니다.

- [OpenSSL 수정·검증](../openssl-compat/README-ko.md)
- [glibc 수정·검증](../glibc-compat/README-ko.md)
- [커널 수정·검증](../kernel-compat/README-ko.md)
- [Trivy 판정 방식](../native-trivy/README.md)

설치기는 `/etc`와 RPM 목록을 저장하지만 전체 시스템 복구 이미지를 만들지는 않습니다.

## 모듈 수집과 후속 분석

`security-kmods.txt`에는 심볼·버전 메타데이터만 있으며, 이후 별도로 받은
실제 바이너리로 [추가 분석](../kernel-compat/SERVER-MODULES-20260926.md)을 완료했습니다.
모듈 버전이 다시 바뀌었을 때는 아래 수집기를 사용합니다. 모듈 파일과 해당
메타데이터만 복사하고, 서비스를 중단하거나 모듈을 해제하지 않습니다.

```bash
wget -e use_proxy=yes -e https_proxy=http://192.168.32.104:9080 \
  -O collect-module-binaries.sh \
  https://raw.githubusercontent.com/emotionbug/slop/main/upstream-rpm/kernel-compat/collect-module-binaries.sh
sudo bash collect-module-binaries.sh
```

출력된 `security-module-binaries-….tar.gz`를 개발기로 옮겨 로컬 분석에 사용합니다.
상용 에이전트 바이너리이므로 공개 GitHub에는 올리지 않습니다.
