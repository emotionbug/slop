# RHEL 8.10 x86_64 업데이트

확인일: 2026-09-23. 공개 UBI 8 저장소로 업데이트하고, UBI에 없는 패키지는
이 디렉터리의 Red Hat 공식 서명 RPM으로 보완한다.

## 포함 파일

- `rpms/`: 커널 계열 11개(`4.18.0-553.166.1.el8_10`) 및
  `perl-DBI-1.641-10.module+el8.10.0+24875+bc962974.x86_64.rpm`.
- `rollback-registration.sh`: 서버의 subscription-manager 등록 해제와 로컬 등록 정보 정리.
- `patch-rhel8.sh`: UBI 업데이트 및 임의 로컬 RPM 디렉터리 검사/설치.
- `apply-bundle.sh`: 포함된 RPM 중 현재 설치된 이름·아키텍처만 선택해 검사/업데이트.
- `SHA256SUMS`, `RPM-SOURCES.json`: 파일 무결성 및 공식 다운로드 해시/출처.
- `VALIDATION.md`: 실행한 검사와 실제 서버에서 남은 확인 범위.

UBI는 RHEL 전체 저장소의 일부이므로 모든 패키지의 업데이트를 제공하지 않는다.
공식 설명: [UBI 저장소와 패키지](https://access.redhat.com/articles/4238681).
이 구성은 전체 RHEL 구독 저장소를 대체하지 않으며, 취약점이 전부 해소됐다는 의미가 아니다.

## 1. 다운로드

[릴리스](https://github.com/emotionbug/slop/releases/tag/rhel8-patch-20260923)에서
`rhel8-patch-20260923.tar.gz`와 `.sha256` 파일을 받는다.
아래 `PROXY_HOST:PORT`는 실제 프록시로 바꾼다. 직접 연결 시 `-e` 옵션을 생략한다.

```bash
wget -e use_proxy=yes -e https_proxy=http://PROXY_HOST:PORT \
  https://github.com/emotionbug/slop/releases/download/rhel8-patch-20260923/rhel8-patch-20260923.tar.gz \
  https://github.com/emotionbug/slop/releases/download/rhel8-patch-20260923/rhel8-patch-20260923.tar.gz.sha256
sha256sum -c rhel8-patch-20260923.tar.gz.sha256
tar -xzf rhel8-patch-20260923.tar.gz
cd rhel8-patch
sha256sum -c SHA256SUMS
```

설치용 압축에는 바이너리 RPM과 스크립트만 포함한다. 대응 소스 RPM 2개는 같은
릴리스에 별도로 제공하며 서버 업데이트를 위해 받을 필요는 없다. 각 RPM의 원래
라이선스가 적용되며, 공식 파일의 서명과 내용은 변경하지 않았다.

## 2. subscription-manager 등록 롤백

```bash
sudo bash rollback-registration.sh --proxy PROXY_HOST:PORT --reset-rhsm-proxy
```

서버 측 `unregister`가 성공한 뒤에만 `clean`을 실행한다. 연결 실패 시 중단하므로
오류가 나면 프록시 연결을 해결한 뒤 다시 실행한다. 이미 등록을 해제한 서버에서는
이 단계를 반복할 필요가 없다.

현재 `rhsm.conf`는 `/var/lib/rhel8-patch/rollback-*/rhsm.conf.before`에 root 전용으로
백업한다. `--reset-rhsm-proxy`는 RHSM의 proxy_hostname/proxy_port 설정을 제거한다.
등록 전에 별도 RHSM 프록시를 사용했다면 이 옵션을 빼고 기존 설정에 맞게 복원한다.
등록 전 설정 사본이 없으므로 그 밖의 과거 설정을 추측해서 복구하지 않는다.
Red Hat 계정·구독·포털 권한과 설치된 subscription-manager 패키지는 유지한다.

## 3. UBI 업데이트 미리보기 및 적용

```bash
sudo bash patch-rhel8.sh --proxy http://PROXY_HOST:PORT ubi-check
sudo bash patch-rhel8.sh --proxy http://PROXY_HOST:PORT ubi-apply
```

먼저 미리보기의 업데이트 목록과 의존성 해결 결과를 확인한다. `ubi-apply`도 DNF가
목록과 용량을 보여준 뒤 `y/N`을 묻는다. `--proxy direct`를 지정하면 직접 연결한다.
미리보기 마지막의 `Operation aborted.`와 종료 코드 1은 설치를 거절한 정상 결과다.
그 전에 나오는 저장소·의존성 오류는 해결해야 한다.

스크립트는 함께 있는 `ubi8-public.repo`를 DNF에 지정한다. 기존 `/etc/yum.repos.d`를
수정하지 않으며, 이 실행에서는 UBI 3개 저장소만 사용하고 subscription-manager
플러그인을 끈다. 일반 `dnf upgrade` 명령에는 이 설정이 자동 적용되지 않는다.

## 4. 추가 RPM 미리보기 및 적용

```bash
sudo bash apply-bundle.sh --proxy http://PROXY_HOST:PORT check
sudo bash apply-bundle.sh --proxy http://PROXY_HOST:PORT apply
```

이미 설치된 패키지만 선택한다. 예를 들어 `kernel-modules-extra`가 설치돼 있지 않으면
추가 설치하지 않는다. 커널 본체·모듈·설치된 devel/extra의 버전 일치를 검사하고,
다운그레이드와 의도하지 않은 모듈 스트림 변경을 거절한다. 포함된 DBI는 Perl 5.26 ABI용 수정본이다. 최종 의존성은 서버의 설치 상태와
UBI 메타데이터를 이용해 DNF가 판단한다. 의존성 오류가 나면 적용을 중단한다.
`--nodeps`, `--allowerasing`, `--skip-broken`으로 우회하지 않는다.

Red Hat RPM 서명 검증과 HTTPS 인증서 검증을 사용한다. 약한 의존성의 신규 설치는
제외하지만 필수 의존성은 DNF가 함께 해결한다. 기존 커널의 자동 삭제를 막기 위해
이 실행에만 `installonly_limit=0`을 사용한다. 따라서 `/boot`와 루트 파일시스템의
여유 공간을 먼저 확인한다. 원래 존재하던 오래된 커널도 그대로 남는다.

```bash
df -h / /boot
rpm -q kernel kernel-core kernel-modules
```

RPM 로그와 설치 전후 목록은 `logs/`에 저장된다. 설치 실패 시 DNF 트랜잭션과 로그를
확인한다. 운영 서비스 재시작은 서비스 영향에 맞춰 수행하고, 커널 적용은 작업 시간에
재부팅한 후 확인한다. 스크립트는 재부팅을 실행하지 않는다.

```bash
sudo grubby --default-kernel
# 작업 시간에 재부팅한 후
uname -r
sudo dnf --disableplugin=subscription-manager check
```

기대하는 새 커널은 `4.18.0-553.166.1.el8_10.x86_64`다. 부팅·서비스 확인 후 Trivy를
다시 실행한다. 실행 중인 커널이 바뀌어도 남아 있는 이전 커널 RPM이 스캔에 포함될 수
있으므로, 기존 커널 제거는 새 커널 정상 부팅 확인 후 별도로 판단한다.
