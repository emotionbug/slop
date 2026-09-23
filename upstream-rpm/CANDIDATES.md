# 2026-09-23 EL8 평가용 RPM 묶음

전체 323종 최신화 작업 중 로컬 검증을 통과한 첫 7종입니다.
실제 서버에 설치한 결과나 전체 취약점 해결 완료 보고서가 아닙니다.

| 소스 프로젝트 | 버전 | 포함된 교체 패키지 |
|---|---|---|
| rsync | 3.5.1 | rsync |
| zlib | 1.3.2 | zlib, zlib-devel |
| PCRE2 | 10.48 | pcre2, pcre2-devel, pcre2-utf16, pcre2-utf32 |

각 프로젝트의 SRPM도 포함합니다. 자체 빌드 RPM에는 Red Hat 서명이 없으며,
RPM 자체도 아직 미서명입니다. SHA256SUMS는 전송 중 파일 변경을 확인합니다.
서버 인벤토리, 취약점 CSV, 개인 파일, 키는 포함하지 않습니다.

## 검증 범위

- 각 프로젝트의 upstream 테스트 수행.
- 별도 UBI 8에서 기존 패키지 → 후보 패키지를 함께 설치하고 `dnf check` 통과.
- Java 8/Python 압축 왕복, PCRE2 JIT 매칭, rsync 기존 3.1.3과 양방향
  로컬 파이프 전송 및 파일·심볼릭 링크·하드링크 보존 확인.
- 실제 서버 RPM 헤더와 대조하여 충족되지 않는 이름 기반 의존성은 발견되지 않음.
- 파일 의존성·rich dependency·모듈·설치 스크립트·실행 중 프로그램·실제 SSH
  상대 서버·Tomcat/보안 에이전트 동작을 검증한 것은 아님.

## 반입 후 내용과 DNF 예정 작업 확인

다음 명령은 변경 내용을 미리 보여줍니다. 패키지를 설치하지 않습니다.

```bash
tar -xzf el8-rpm-candidates-20260923.tar.gz
cd el8-rpm-candidates
sha256sum -c SHA256SUMS &&
sudo dnf --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False --setopt=install_weak_deps=False \
  --assumeno install ./rpms/*.rpm
```

`--nodeps`, `--force`, `--allowerasing`으로 의존성이나 파일 충돌을 우회하지 않습니다.
DNF 미리보기에서 제거·교체·의존성 변경이 예상과 맞는지 확인해야 합니다.
Trivy에서 자체 RPM의 결과가 사라졌다는 사실만으로 조치 완료를 판정하지 않습니다.

## 빌드 입력 확인 근거

- [rsync 공식 릴리스](https://rsync.samba.org/): 공식 소스 서명 검증.
- [zlib 공식 릴리스](https://zlib.net/): 게시된 SHA-256과 대조.
- [PCRE2 10.48](https://github.com/PCRE2Project/pcre2/releases/tag/pcre2-10.48):
  공식 GitHub 릴리스 digest와 Sigstore attestation 검증.
- [PCRE2 JIT 수정 안내](https://github.com/PCRE2Project/pcre2/security/advisories/GHSA-2p8c-ff85-vh9x):
  수정 버전 10.48 명시. 다른 CVE들도 개별 조치 근거 확인이 필요합니다.

공식 소스의 서명 검증과 자체 RPM의 배포 서명은 서로 다른 항목입니다.
