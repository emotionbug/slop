# RHEL 8 x86_64 프록시 다운로드 및 설치 — 2026-09-25

`20260925-4`는 Bison의 `yacc` 파일이 기존 byacc와 충돌하는 문제를 수정했습니다.
[변경 내용과 검증](BISON-YACC-FIX.md). 기존 byacc 파일과 기능은 유지합니다.
같은 심볼 이름과 함께 제거되는 구버전 파일을 구분하는
[기존 검사 수정](SYMBOL-POLICY-FIX.md)도 포함합니다.
sed 등의 `/bin/*` 의존성 수정도 유지합니다([기존 수정](LEGACY-PATH-FIX.md)).
기존 77개 후보에서 현재 설치된 패키지를
업그레이드합니다(`noarch`↔`x86_64` 전환 허용). 아직 설치되지 않은 패키지는 필수 의존성일 때만 추가합니다.
이전에 제거한 도구를 77개 모두 재설치하는 방식이 아닙니다.

## 프록시로 다운로드하고 설치

서버에서 프록시 주소를 지정해 실행합니다. 약 43 MB 묶음을 GitHub에서 받은 뒤
릴리스의 SHA256과 대조하고 설치합니다. RPM 설치 단계는 로컬 파일만 사용하므로
RHSM 등록이나 외부 DNF 저장소 인증은 필요하지 않습니다.

```bash
(
set -e
PROXY='http://PROXY_HOST:PORT'
mkdir -p linuxoss-update-20260925-4
cd linuxoss-update-20260925-4
BASE='https://github.com/emotionbug/slop/releases/download/linuxoss-install-20260925-4'
for FILE in linuxoss-install-20260925-4.tar.gz linuxoss-install-20260925-4.tar.gz.sha256; do
wget -e use_proxy=yes -e https_proxy="$PROXY" -e http_proxy="$PROXY" \
  --timeout=60 --tries=3 \
  -O "$FILE" "$BASE/$FILE"
done
sha256sum -c linuxoss-install-20260925-4.tar.gz.sha256
tar -xzf linuxoss-install-20260925-4.tar.gz
cd linuxoss-install-20260925-4
sudo bash install.sh apply
)
```

[릴리스와 체크섬 파일](https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-4).
다운로드 실패 또는 체크섬 불일치 시 설치하지 않습니다.

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

## 심볼 검사에서 중단된 경우

`symbol-audit.json`의 일치는 취약점 개수가 아니라 ELF가 참조하는 심볼 이름입니다.
여러 라이브러리가 같은 이름을 제공하거나, 참조 파일도 같은 트랜잭션에서 교체될 수
있으므로 이름 일치만으로 실제 ABI 충돌을 단정하지 않습니다. `.build-id` 경로도
실제 ELF 경로로 해석해야 합니다. 기존 설치기의 차단 조건을 임의로 삭제하지 마세요.

[`diagnose-symbol-audit.py`](diagnose-symbol-audit.py)는 기존 검사에서 걸린 파일만
상세히 조사합니다. 실제 경로·RPM 소유자·DT_NEEDED·해당 심볼의 import/export와
직접 의존 라이브러리 후보, 디버그 링크 이외의 오류, 예정 트랜잭션을 JSON으로
출력합니다. 기본값은 가장 최근 `/var/log/linuxoss-install/run-*/symbol-audit.json`입니다.

```bash
sudo /usr/libexec/platform-python diagnose-symbol-audit.py > symbol-details.json
# 특정 실행 결과를 선택하려면:
sudo /usr/libexec/platform-python diagnose-symbol-audit.py \
  /var/log/linuxoss-install/run-실제경로/symbol-audit.json > symbol-details.json
```

RPM 조회, `readelf`, `ldconfig -p`만 사용합니다. 검사 대상 프로그램이나 `ldd`를 실행하지
않고 패키지·서비스·링크를 변경하지 않습니다. 전체 파일 재검사도 하지 않습니다.
라이브러리 후보는 실행 중의 실제 바인딩 증명이 아니며, 이 결과로 설치를 자동 승인하거나
기존 검사를 우회하지 않습니다. 서버 경로와 패키지 정보가 들어 있는 결과 파일은
공개 저장소에 올리지 마세요. EL8 Python 3.6에서 실제 ELF·심볼 제공 라이브러리·
별칭 링크·끊어진 링크를 이용한 진단 테스트를 통과했습니다.

## 범위와 중단 조건

- 기준: `linuxoss-install-20260925-3`의 77 RPM 중 Bison 1개를 release 4로
  교체했습니다. Trivy 카탈로그/모듈도 새 Bison 식별 정보를 포함합니다.
  나머지 76 RPM과 기존 설치기의 심볼 검사 수정은 유지합니다.
- 전체 342개 제작본을 한 서버에 모두 설치하는 스크립트가 아닙니다.
  커널·GCC·glibc·systemd와 `/opt` 평가본의 일괄 전환은 포함하지 않습니다.
- 새 OpenSSL은 해당 후보의 의존성인 `/opt`용 `linuxoss-openssl4`입니다.
  시스템 OpenSSL 패키지를 제거하거나 `/usr/bin/openssl`을 바꾸지 않습니다.
- 외부 저장소나 RHSM에 접속하지 않습니다. 필요한 기존 의존성이 서버와 묶음에
  모두 없으면 적용 전에 중단합니다. Perl·graphite2·X11 라이브러리 등은 이 조건에
  해당할 수 있습니다. 의존성을 무시하거나 자동으로 패키지를 지우지 않습니다.
- 제거·다운그레이드·다른 이름으로의 교체·묶음 외 패키지 설치를 거절합니다.
- 심볼 일치 결과는 변경 대상과 제공 라이브러리를 함께 판단해
  `symbol-audit-policy.json`에 기록합니다. 확인되지 않은 사용과 검사 오류는 중단합니다.
  기존 끊어진 심볼릭 링크는 대상을 재확인하고 경고로 남기며 삭제하거나 복구하지
  않습니다. 해당 프로그램이 정상이라는 의미도 아닙니다. 존재하는 `/usr/src`는
  자동으로 추가 검사해 커널 소스 링크를 포함합니다. 자세한 조건은
  [심볼 검사 수정 내용](SYMBOL-POLICY-FIX.md)을 참조하세요.
  일치가 없다는 결과만으로 모든 플러그인, dlsym, JNI, 실제 운영 호환성이
  검증되는 것은 아닙니다. 기본 경로 밖의 프로그램은 반드시 경로를 추가하세요.
- 자동 재부팅이나 Java/Tomcat 재시작 명령은 없습니다. 개별 RPM의 scriptlet은
  실행되므로 실제 적용은 운영 점검 시간에 수행하세요.
- 실제 대상 서버의 설치·부팅·Java/Tomcat 검증과 취약점 0개 달성은 미확인입니다.

## 출처

수정판 설치기 검증: Bison/byacc와 CUPS가 있는 UBI 8.10 참조 컨테이너에서
41개 업그레이드와 필수 의존성 2개 추가, `dnf check`, byacc 파일 보존 및
Bison의 보안 회귀 검사가 통과했습니다. Bison/byacc 참조 RPM은 동일 EL8 버전의
Rocky 배포본이며 서버의 Red Hat 바이너리와 동일하다는 의미는 아닙니다.
Trivy 카탈로그는 새 Bison 해시를 포함하도록 갱신했고 기존 피드는 유지했습니다.
오프라인 통합 스캔에서 새 Bison RPM 식별과 기존 보안 패치 2건의 해시 일치를
확인했습니다. 이 결과만으로 모든 취약점이 해결되었다는 의미는 아닙니다.
참조 환경은 binutils·Perl·Cairo·graphite2 등의 기본 의존성을 갖춘 조건입니다.
이 개수는 실제 서버의 적용 개수나 취약점 해결 개수가 아닙니다.

- RPM/SRPM: https://github.com/emotionbug/slop/releases/tag/upstream-rpm-candidates-20260924-7
- 수정 RPM/SRPM: https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-2
- Bison 수정 RPM/SRPM: https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-4
- Trivy v3: https://github.com/emotionbug/slop/releases/tag/trivy-native-rpm-20260924-3
- 원래 후보 압축 SHA256: `f701fdbb1031ace9af6a4248c3b6ed309a563341fa7c9d8cbe7391bd8c85682b`
- 원래 native 압축 SHA256: `278f91968a0178208029ff6b747149f50f7a18924e25c88afeca031481cc84a0`
- 자체 RPM은 미서명입니다. 원래 manifest와 내부/외부 SHA256으로 배포 파일을 대조합니다.
- [DNF 공식 API](https://dnf.readthedocs.io/en/latest/api_base.html)의 local package
  sack, upgrade, dependency resolve, transaction API를 사용합니다.
- 소스 RPM은 위 원래 릴리스에 그대로 있으며, 설치 파일 크기를 줄이기 위해 제외했습니다.
