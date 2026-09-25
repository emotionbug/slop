# RHEL 8 x86_64 프록시 다운로드 및 설치 — 2026-09-25

기존 77개 참조 검증 RPM에서 현재 서버에 설치된 이름·아키텍처의 패키지를
업그레이드합니다(`noarch`↔`x86_64` 전환 허용). 아직 설치되지 않은 패키지는 필수 의존성일 때만 추가합니다.
이전에 제거한 도구를 77개 모두 재설치하는 방식이 아닙니다.

## 프록시로 다운로드하고 설치

서버에서 프록시 주소를 지정해 실행합니다. 약 43 MB 묶음을 GitHub에서 받은 뒤
고정 SHA256과 대조하고 설치합니다. RPM 설치 단계는 로컬 파일만 사용하므로
RHSM 등록이나 외부 DNF 저장소 인증은 필요하지 않습니다.

```bash
(
set -e
PROXY='http://PROXY_HOST:PORT'
mkdir -p linuxoss-update-20260925
cd linuxoss-update-20260925
wget -e use_proxy=yes -e https_proxy="$PROXY" -e http_proxy="$PROXY" \
  --timeout=60 --tries=3 \
  -O linuxoss-install-20260925.tar.gz \
  https://github.com/emotionbug/slop/releases/download/linuxoss-install-20260925/linuxoss-install-20260925.tar.gz
printf '%s  %s\n' \
  92d32c93d770347b9e713759d58fae6c651170f0ed8bb0d317008bd835dd04d3 \
  linuxoss-install-20260925.tar.gz | sha256sum -c -
tar -xzf linuxoss-install-20260925.tar.gz
cd linuxoss-install-20260925
sudo bash install.sh apply
)
```

[릴리스와 체크섬 파일](https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925).
다운로드 실패 또는 체크섬 불일치 시 설치하지 않습니다. 압축 안의 설치기는 이미
검증한 것과 동일하며, 동봉 안내의 반입 단계는 위 다운로드 단계로 대신합니다.

`apply`가 체크섬, 의존성, 해당 라이브러리에서 제거된 심볼의 직접 사용 여부,
RPM 트랜잭션 검사를 수행한 다음 설치합니다. 별도의 `check`를 먼저 실행할
필요는 없습니다. 설치 없이 예정 작업만 보려면 `sudo bash install.sh check`입니다.

Java/Tomcat 또는 보안 에이전트가 `/opt`, `/usr/local`, `/usr/bin`, `/usr/sbin`,
`/usr/lib`, `/usr/lib64`, `/usr/libexec` 밖에 있다면 실제 디렉터리를 추가합니다.

```bash
sudo bash install.sh apply /data/실제-Tomcat-디렉터리 /app/실제-Java-디렉터리
```

로그는 `/var/log/linuxoss-install/run-.../`에 저장합니다. `transaction.json`은
적용할 버전과 추가 의존성, `rpms-before.tsv`/`rpms-after.tsv`는 전후 목록입니다.
`etc-before.tar.gz`는 `/etc` 설정 백업이며 **전체 시스템 복구본이나 이전 RPM 백업은
아닙니다**. 이전 RPM 없이 `dnf history undo`가 성공한다고 보장할 수 없습니다.
이 디렉터리에는 서버 설정이 포함되므로 공개 GitHub에 업로드하지 마세요.

## 적용 후 Trivy

운영 일정에 맞춰 Java/Tomcat을 재시작한 뒤 다음 명령을 실행합니다.
실행 중인 JVM이 이미 읽어 둔 라이브러리는 RPM 교체만으로 바뀌지 않습니다.

```bash
sudo bash scan.sh
```

기존 `/root/trivy` 아래 Trivy와 DB 경로를 자동 확인합니다. 경로가 다르면 지정합니다.

```bash
sudo bash scan.sh /실제/경로/trivy /실제/경로/cache
```

Trivy **0.74.0**과 기존 취약점 DB가 필요합니다. 이 파일에는 Trivy 본체와 DB,
Java DB를 중복 포함하지 않습니다. RPM 설치 자체는 Trivy 없이도 가능합니다.
결과는 출력된 경로의 **`reports/actionable.csv`**를 확인하세요.
이 검사는 한 번 실행하며 공식 RHEL 결과와 자체 RPM 근거를 함께 표시합니다.
피드/DB 기준 이후의 신규 CVE는 별도 데이터 갱신 전에는 반영되지 않습니다.

## 범위와 중단 조건

- 기준: `upstream-rpm-candidates-20260924-7`의 77 RPM, Trivy 통합 v3.
- 전체 342개 제작본을 한 서버에 모두 설치하는 스크립트가 아닙니다.
  커널·GCC·glibc·systemd와 `/opt` 평가본의 일괄 전환은 포함하지 않습니다.
- 새 OpenSSL은 해당 후보의 의존성인 `/opt`용 `linuxoss-openssl4`입니다.
  시스템 OpenSSL 패키지를 제거하거나 `/usr/bin/openssl`을 바꾸지 않습니다.
- 외부 저장소나 RHSM에 접속하지 않습니다. 필요한 기존 의존성이 서버와 묶음에
  모두 없으면 적용 전에 중단합니다. Perl·graphite2·X11 라이브러리 등은 이 조건에
  해당할 수 있습니다. 의존성을 무시하거나 자동으로 패키지를 지우지 않습니다.
- 제거·다운그레이드·다른 이름으로의 교체·묶음 외 패키지 설치를 거절합니다.
- 제거된 심볼 사용이나 검사 누락이 있으면 `symbol-audit.json`을 남기고 중단합니다.
  대상 ELF가 이미 없는 `.build-id` 디버그 링크만 중단 사유에서 제외하고
  `symbol-audit-policy.json`에 따로 기록합니다. 실제 파일의 검사 오류는 중단합니다.
  일치가 없다는 결과만으로 모든 플러그인, dlsym, JNI, 실제 운영 호환성이
  검증되는 것은 아닙니다. 기본 경로 밖의 프로그램은 반드시 경로를 추가하세요.
- 자동 재부팅이나 Java/Tomcat 재시작 명령은 없습니다. 개별 RPM의 scriptlet은
  실행되므로 실제 적용은 운영 점검 시간에 수행하세요.
- 실제 대상 서버의 설치·부팅·Java/Tomcat 검증과 취약점 0개 달성은 미확인입니다.

## 출처

이번 설치기 검증: UBI 8.10 참조 컨테이너에서 29개 업그레이드와 필수 의존성 2개
추가, `dnf check`, curl 및 DNF 실행이 통과했습니다. 확인 모드 전후의 RPM 목록도
동일했습니다. 참조 환경은 binutils·Perl·Cairo·graphite2를 먼저 갖춘 조건입니다.
이 개수는 실제 서버의 적용 개수나 취약점 해결 개수가 아닙니다.

- RPM/SRPM: https://github.com/emotionbug/slop/releases/tag/upstream-rpm-candidates-20260924-7
- Trivy v3: https://github.com/emotionbug/slop/releases/tag/trivy-native-rpm-20260924-3
- 원래 후보 압축 SHA256: `f701fdbb1031ace9af6a4248c3b6ed309a563341fa7c9d8cbe7391bd8c85682b`
- 원래 native 압축 SHA256: `278f91968a0178208029ff6b747149f50f7a18924e25c88afeca031481cc84a0`
- 자체 RPM은 미서명입니다. 원래 manifest와 내부/외부 SHA256으로 배포 파일을 대조합니다.
- [DNF 공식 API](https://dnf.readthedocs.io/en/latest/api_base.html)의 local package
  sack, upgrade, dependency resolve, transaction API를 사용합니다.
- 소스 RPM은 위 원래 릴리스에 그대로 있으며, 설치 파일 크기를 줄이기 위해 제외했습니다.
