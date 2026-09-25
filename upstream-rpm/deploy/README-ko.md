# RHEL 8 x86_64 프록시 다운로드 및 설치 — 20260925-6

[이번 묶음의 수정 내용과 검증](COMPAT-WAVE-20260925-6.md),
[배포 파일](https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-6).
이전 Bison/byacc·legacy `/bin` 경로·심볼 판정 수정도 유지합니다.
정확한 RPM 목록과 버전은 `candidate-manifest.json`에 고정되어 있습니다.

## 다운로드와 적용

```bash
(
set -e
PROXY='http://PROXY_HOST:PORT'
mkdir -p linuxoss-update-20260925-6
cd linuxoss-update-20260925-6
BASE='https://github.com/emotionbug/slop/releases/download/linuxoss-install-20260925-6'
for FILE in linuxoss-install-20260925-6.tar.gz linuxoss-install-20260925-6.tar.gz.sha256; do
  wget -e use_proxy=yes -e https_proxy="$PROXY" -e http_proxy="$PROXY" \
    --timeout=60 --tries=3 -O "$FILE" "$BASE/$FILE"
done
sha256sum -c linuxoss-install-20260925-6.tar.gz.sha256
tar -xzf linuxoss-install-20260925-6.tar.gz
cd linuxoss-install-20260925-6
sudo bash install.sh apply
)
```

`apply`는 체크섬, 의존성, 심볼 사용, 실제 RPM 트랜잭션 검사를 거친 다음 설치합니다.
별도의 `check`를 먼저 실행할 필요는 없습니다. 설치 없이 예정 작업만 보려면
`sudo bash install.sh check`를 실행합니다.

기존 설치된 이름만 업그레이드하고 필수 의존성만 추가합니다. 이미 삭제한 도구를
모두 재설치하지 않습니다. 삭제·다운그레이드·묶음 밖 RPM 설치는 거절합니다.
RPM 적용 중에는 외부 저장소나 subscription-manager를 사용하지 않습니다.
의존성을 무시하거나 `--allowerasing`으로 밀어 넣지 않습니다.

Java/Tomcat/보안 에이전트가 기본 검사 경로 `/usr`, `/opt`, `/usr/local` 밖에 있으면
실제 디렉터리를 함께 전달하세요. `/usr` 중 bin/sbin/lib/lib64/libexec/src/share를 검사합니다.

```bash
sudo bash install.sh apply /data/실제-Tomcat-디렉터리 /app/실제-Java-디렉터리
```

로그는 `/var/log/linuxoss-install/run-.../`입니다. `transaction.json`에 적용 버전과
의존성이 기록됩니다. `etc-before.tar.gz`는 설정 백업이며 전체 복구 이미지나 이전 RPM
백업은 아닙니다. 설치 로그와 설정은 공개 저장소에 올리지 마세요.

## 적용 후 Trivy

운영 일정에 맞춰 Java/Tomcat을 재시작한 뒤 실행합니다. 자동 재시작·재부팅은 하지 않습니다.
RPM 교체만으로 이미 실행 중인 JVM의 라이브러리가 바뀌지는 않습니다.

```bash
sudo bash scan.sh
# 경로가 다른 경우
sudo bash scan.sh /실제/경로/trivy /실제/경로/cache
```

Trivy **0.74.0**과 기존 DB를 재사용합니다. Trivy 본체·DB·Java DB는 이 묶음에 없습니다.
먼저 `reports/fix-available.csv`, `reports/native-review.csv`를 확인하세요.
`actionable.csv`는 둘을 포함한 전체 남은 CVE, `reviewed-resolutions.csv`는 근거가 있는
수정/비해당 결과, `scan-gaps.csv`는 검사 범위 제한입니다. 원본 JSON은 그대로 남습니다.

## 검증 범위

EL8 참조 컨테이너의 DNF 교체·의존성·공유 라이브러리 로딩·명령 실행과 Trivy 연결을
검증합니다. 참조 환경 일부 구버전 RPM은 Rocky EL8이며 실제 서버의 Red Hat 바이너리와
동일하다는 뜻은 아닙니다. 세부 결과는 변경 문서와 공개 manifest를 확인하세요.
운영 서버의 부팅·SSH·JNI·보안 에이전트·Java/Tomcat 검증과 모든 CVE 해결은 별도입니다.

커널 헤더 업데이트는 부팅 커널 업데이트가 아닙니다. 실행 커널, glibc, systemd,
SSH/PAM 및 스토리지·네트워크 핵심 서비스는 ABI를 유지하는 보안 패치와 부팅·인증 검증이 남은 후속 작업입니다.
기존 끊어진 링크는 기록만 하고 변경하지 않습니다. 심볼 검사에서 멈추면
[`diagnose-symbol-audit.py`](diagnose-symbol-audit.py)로 해당 결과를 조사할 수 있습니다.

자체 RPM은 미서명이며 신뢰한 릴리스의 SHA256으로 대조합니다. 공식 UBI RPM은 Red Hat
서명을 확인해 묶었습니다. 새 SRPM은 같은 릴리스에, 이전 제작본의 소스는
[전체 제작 릴리스](https://github.com/emotionbug/slop/releases/tag/upstream-rpm-all-builds-20260924-7)에 있습니다.
