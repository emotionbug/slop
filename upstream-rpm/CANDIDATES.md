# 2026-09-24 EL8 평가용 RPM 묶음

전체 323종 최신화 작업 중 로컬 검증을 통과한 24종과 공식 보조 RPM 1개입니다.
실제 서버에 설치한 결과나 전체 취약점 해결 완료 보고서가 아닙니다.

| 소스 프로젝트 | 버전 | 포함된 교체 패키지 |
|---|---|---|
| rsync | 3.5.1 | rsync |
| zlib | 1.3.2 | zlib, zlib-devel |
| PCRE2 | 10.48 | pcre2, pcre2-devel, pcre2-utf16, pcre2-utf32 |
| Expat | 2.8.5 | expat, expat-devel |
| XZ | 5.8.4 | xz, xz-libs, xz-devel |
| c-ares | 1.34.8 | c-ares |
| libpng | 2:1.6.58 | libpng (RHEL Epoch 2 유지) |
| Little CMS | 2.19.1 | lcms2 |
| GNU sed | 4.10 | sed |
| GNU diffutils | 3.12-2 | diffutils (CVE-2026-53910 수정 2개 반영) |
| GNU patch | 2.8 | patch |
| GNU gawk | 5.4.1 | gawk |
| GNU Bison | 3.8.2-3 | bison (CVE-2026-56389/56390 패치) |
| GNU cpio | 2.15-2 | cpio (CVE-2026-66484/66485/66486 패치) |
| bzip2 | 1.0.8 | bzip2, bzip2-libs (CVE-2026-42250 및 출력 파일 보호 패치) |
| GNU tar | 2:1.35-2 | tar (CVE-2025-45582/2026-5704 보안·회귀 패치, Epoch 2 유지) |

공식 UBI의 `cmake-filesystem-3.26.5-2.el8`은 개발용 CMake 파일의 디렉터리
의존성을 충족하기 위해 포함했고 Red Hat 서명을 검증했습니다.
각 16개 프로젝트의 SRPM도 포함합니다. 자체 빌드 RPM에는 Red Hat 서명이 없으며,
RPM 자체도 아직 미서명입니다. SHA256SUMS는 전송 중 파일 변경을 확인합니다.
서버 인벤토리, 취약점 CSV, 개인 파일, 키는 포함하지 않습니다.

## 검증 범위

- 각 프로젝트의 upstream 테스트 수행.
- 별도 UBI 8에서 후보 패키지를 함께 설치하고 `dnf check` 통과. Bison, c-ares, bzip2 CLI는
  UBI 기준 패키지가 없어 새 설치이며, bzip2-libs와 나머지 기존 패키지는 업그레이드입니다.
- 최종 설치된 자체 RPM의 이름이 정확히 24종인 것을 확인했습니다. 테스트 컴파일에만
  필요했던 UBI libpng-devel은 빌드한 검사 실행파일을 보존한 뒤 컨테이너에서 제거했습니다.
- Java 8/Python 압축 왕복, PCRE2 JIT 매칭, rsync 기존 3.1.3과 양방향
  로컬 파이프 전송 및 파일·심볼릭 링크·하드링크 보존 확인.
- Python XML 파싱·잘못된 XML 거부, XZ/LZMA 왕복, XZ CLI 왕복 확인.
- Expat/XZ의 기존 UBI 동적 공개 심볼 74개/198개 보존 확인.
- PNG/LCMS의 기존 UBI 공개 심볼 493개/360개와 교체 전 컴파일한 실행파일의
  PNG 이미지·색상 변환 동작 보존 확인.
- c-ares 오프라인 1,140개와 fuzz suite 2개 통과, UBI DNS 파서 검사 통과.
  외부 DNS 검사는 60개 통과/2개 실패이며 DNS 서버의 ANY 질의 거부를 독립적으로
  재현했습니다. c-ares 심볼 60개 비교의 기준은 Rocky EL8 참조 RPM입니다.
- 실제 서버에서 추출한 RPM 메타데이터와 대조하여 충족되지 않는 이름 기반 의존성은 발견되지 않음.
- Epoch를 포함한 버전 비교에서 downgrade 0개. 파일/rich dependency 등 1,172건은 미검증.
- sed의 치환·ACL·모드·심볼릭 링크 동작 확인. in-place 수정 시 `user.*` xattr는
  기존 UBI sed와 새 sed 모두 제거합니다. xattr 보존을 지원한다고 기록하지 않습니다.
- diff/cmp/diff3 병합과 과도한 행 번호 입력 3개 거부, patch dry-run·적용·역적용 확인.
- gawk의 MPFR 큰 정수·배열 정렬·filefuncs 확장 확인.
- Bison 원본 테스트 712개 통과/64개 건너뜀. 수정 전후 grammar 프로그램·출력·헤더
  경로 3개 비교 및 실제 parser 생성·컴파일·실행 확인.
- cpio 원본 테스트 17개 통과. 수정 전후 hardlink 경로·PTY 출력·긴 경로 처리 비교.
- tar 원본 테스트 234개 통과/15개 건너뜀. 파일·링크·ACL·xattr·모드 복원 확인.
- bzip2 기존 라이브러리 심볼 38개 보존, 이전 라이브러리에 연결한 C 실행파일,
  Python/CLI 1 MiB 압축 왕복, recovery 파일 덮어쓰기 거부 확인. 별도 ASan 소스
  빌드에서 CVE-2026-42250 수정 전 오류 재현 및 수정 후 차단 확인.
- 파일 의존성·rich dependency·모듈·설치 스크립트·실행 중 프로그램·실제 SSH
  상대 서버·Tomcat/보안 에이전트 동작을 검증한 것은 아님.

## 반입 후 내용과 DNF 예정 작업 확인

다음 명령은 변경 내용을 미리 보여줍니다. 패키지를 설치하지 않습니다.

```bash
bundle_dir=$(mktemp -d "${PWD}/el8-rpm-candidates.XXXXXX") &&
sha256sum -c el8-rpm-candidates-20260924-4.tar.gz.sha256 &&
tar -xzf el8-rpm-candidates-20260924-4.tar.gz -C "$bundle_dir" &&
cd "$bundle_dir/el8-rpm-candidates" &&
sha256sum -c SHA256SUMS &&
sudo dnf --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False --setopt=install_weak_deps=False \
  --assumeno install ./rpms/*.rpm
```

[24종 압축본](https://github.com/emotionbug/slop/releases/tag/upstream-rpm-candidates-20260924-4)은
약 40.2 MiB이며 SHA-256은
`1046fb75f766683a241c55966709b91654113abf65e279140d919d08db4e4736`입니다.

tar의 CVE-2026-18477/18508 및 다른 잔여 CVE를 모두 해결한 묶음은 아닙니다.
패치별 근거와 확인하지 못한 항목은 [SECURITY-EVIDENCE.md](SECURITY-EVIDENCE.md)를 확인하세요.

Zstandard와 libjpeg-turbo는 빌드·기능 검사를 통과했지만 구형 API 사용 여부를
확인해야 해 이 묶음에서 보류합니다. 커널·glibc·시스템 OpenSSL 교체본도 포함하지 않습니다.

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
- [Expat 2.8.5](https://github.com/libexpat/libexpat/releases/tag/R_2_8_5)와
  [XZ 5.8.4](https://github.com/tukaani-project/xz/releases/tag/v5.8.4):
  공식 GitHub 릴리스에 게시된 SHA-256과 소스 파일을 대조했습니다.

공식 소스의 서명 검증과 자체 RPM의 배포 서명은 서로 다른 항목입니다.

추가 소스는 [c-ares 1.34.8](https://github.com/c-ares/c-ares/releases/tag/v1.34.8),
[libpng 1.6.58](https://www.libpng.org/pub/png/libpng.html),
[Little CMS 2.19.1](https://github.com/mm2/Little-CMS/releases/tag/lcms2.19.1)의
공식 게시 SHA-256과 대조했습니다. c-ares 테스트에는 GoogleTest 1.18.0을 사용합니다.
