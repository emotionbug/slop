# 2026-09-24 EL8 평가용 RPM 묶음

전체 323종 중 **46종과 의존 RPM 2종**의 로컬 설치·실행 검사를 마쳤습니다.
**이 중 11종은 제거된 심볼을 쓰는 서버 프로그램이 있는지 추가 확인해야 합니다.**
실제 서버 적용, 전체 ABI 호환성, 전체 CVE 해결을 완료한 묶음은 아닙니다.

[다운로드: upstream-rpm-candidates-20260924-5](https://github.com/emotionbug/slop/releases/tag/upstream-rpm-candidates-20260924-5)

- `el8-rpm-candidates-20260924-5.tar.gz`: 93.2 MiB
- SHA-256: `acfa0061ee1fdf633cb64570911cabd7253f122ab3641bd388cddfc92e0a976e`
- 바이너리 RPM 48개, 대응 SRPM 34개, 체크섬 및 읽기 전용 사전 검사 도구 포함.
- 자체 RPM은 미서명입니다. `cmake-filesystem`만 Red Hat 서명을 확인한 공식 UBI RPM입니다.
- 서버 인벤토리·취약점 CSV·사용자 파일·키·실행 로그는 포함하지 않습니다.

| 프로젝트 | 버전 | 포함 패키지 |
|---|---|---|
| rsync | 3.5.1 | rsync |
| zlib | 1.3.2 | zlib, zlib-devel |
| PCRE2 | 10.48 | pcre2, pcre2-devel, pcre2-utf16, pcre2-utf32 |
| Expat | 2.8.5 | expat, expat-devel |
| XZ | 5.8.4 | xz, xz-libs, xz-devel |
| c-ares | 1.34.8 | c-ares |
| libpng | 2:1.6.58 | libpng |
| Little CMS | 2.19.1 | lcms2 |
| GNU utilities | sed 4.10, diffutils 3.12-2, patch 2.8, gawk 5.4.1 | sed, diffutils, patch, gawk |
| Archive/parser tools | bison 3.8.2-3, cpio 2.15-2, bzip2 1.0.8, tar 2:1.35-2 | bison, cpio, bzip2, bzip2-libs, tar |
| libtasn1 / popt | 4.21.0 / 1.19 | libtasn1, popt |
| Oniguruma / jq | 6.9.10-2 / 1.8.2 | oniguruma, jq |
| nano / tmux | 9.2 / 3.7c | nano, tmux |
| libXpm | 3.5.19 | libXpm |
| libpcap / tcpdump | 14:1.11.0 / 14:4.99.7 | libpcap, tcpdump |
| file | 5.48 | file, file-libs, python3-magic (noarch) |
| libssh | 0.12.2 | libssh, libssh-config (noarch) |
| Zstandard | 1.5.7 | zstd, libzstd, libzstd-devel |
| libjpeg-turbo | 3.2.0 | libjpeg-turbo |
| HarfBuzz / FreeType | 14.5.0 / 2.14.3 | harfbuzz, freetype |
| GNU time / Libgcrypt | 1.10 / 1.12.4 | time, libgcrypt |

의존 RPM은 자체 `libgpg-error 1.61`과 공식 UBI `cmake-filesystem 3.26.5`입니다.
libgpg-error는 최신 Libgcrypt에 필요하며 원래 323종에는 없는 추가 항목입니다.

## 반입 후 한 번에 사전 확인

다음 명령은 패키지를 **설치하지 않습니다**. 체크섬, 제거된 심볼 참조,
DNF 예정 작업을 한 폴더에 수집합니다. 프록시가 필요하면 서버의 `https_proxy`를 먼저 설정합니다.

```bash
wget -O el8-rpm-candidates-20260924-5.tar.gz \
  https://github.com/emotionbug/slop/releases/download/upstream-rpm-candidates-20260924-5/el8-rpm-candidates-20260924-5.tar.gz
wget -O el8-rpm-candidates-20260924-5.tar.gz.sha256 \
  https://github.com/emotionbug/slop/releases/download/upstream-rpm-candidates-20260924-5/el8-rpm-candidates-20260924-5.tar.gz.sha256
sha256sum -c el8-rpm-candidates-20260924-5.tar.gz.sha256 &&
bundle_dir=$(mktemp -d "${PWD}/el8-rpm-candidates.XXXXXX") &&
tar -xzf el8-rpm-candidates-20260924-5.tar.gz -C "$bundle_dir" &&
sudo bash "$bundle_dir/el8-rpm-candidates/preflight-candidates.sh"
```

기본 검사 경로는 `/usr/bin`, `/usr/sbin`, `/usr/lib`, `/usr/lib64`, `/usr/libexec`,
`/opt`, `/usr/local`입니다. 별도 애플리케이션 경로가 있으면 마지막 명령 뒤에 추가합니다.
결과의 `symbol-audit.json`, `dnf-preview.txt`, `status.txt`를 함께 확인합니다.
`--assumeno`로 거래를 취소했을 때도 DNF 종료 코드가 1일 수 있습니다.

## 조건부 11종과 심볼 차이

`oniguruma`, `libXpm`, `file`, `file-libs`, `python3-magic`, `freetype`, `harfbuzz`,
`libjpeg-turbo`, `zstd`, `libzstd`, `libzstd-devel`은 관련 라이브러리의 제거된
심볼 또는 같은 묶음의 의존성 때문에 서버 확인이 추가로 필요합니다.

- Oniguruma POSIX 함수 8개는 이름이 바뀌어 EL8 이름을 실제 구현에 연결하는 별칭 패치를
  추가했습니다. 구형 헤더로 만든 동일 실행파일이 교체 전후 통과했습니다.
- file/libXpm 및 Oniguruma의 일부 구현용 심볼은 사라졌습니다.
- **FreeType의 `FT_Outline_New_Internal`, `FT_Outline_Done_Internal`은 구형 공개 헤더에
  선언돼 있던 함수입니다.** 이름만 보고 사용자가 없다고 가정하지 않습니다.
- JPEG의 `jpeg_std_message_table`과 Zstd의 `ZSTD_getSequences`도 제거됐습니다.
- 링커 표식을 제외한 **144개 이름**을 사전 검사 대상으로 제공합니다.

전체 목록은 [expected-export-removals.json](expected-export-removals.json)에 있습니다.
기존 두 심볼의 검사 결과로 새 144개까지 확인한 것으로 간주하지 않습니다.
읽기 전용 검사도 `dlsym`, 플러그인, 누락된 경로, 실행 중 삭제된 바이너리를 보증하지 않습니다.
깨진 링크·접근 오류·기본 범위 밖 디렉터리 링크는 결과에 별도로 기록합니다.

## 완료한 로컬 검사

- 최종 48 RPM을 UBI 8에서 함께 설치하고 `dnf check` 통과. 자체 RPM 47개의
  정확한 이름과 ELF 75개의 빌드 전용 경로 RPATH 부재 확인.
- 실제 서버 RPM 헤더 기준 이름 기반 의존성 누락·downgrade 0개.
  파일/rich dependency 등 1,181건은 이 정적 검사만으로 판정하지 않았습니다.
- 교체 전 연결한 C 실행파일의 PNG/JPEG/색 변환, Zstd, Oniguruma POSIX 동작 확인.
- Java 8 폰트·JPEG·gzip, Python 압축·XML, jq 정규식, file Python API, ASN.1 입력,
  AES/SHA256 벡터, GNU time 종료 코드, nano PTY 저장, tmux, tcpdump 등 실행 검사 통과.
- 명시적으로 신뢰한 인증서의 로컬 TLS 연결, 서버 키를 대조한 libssh 키 인증·명령 실행 통과.
  실제 서버의 SSH 구성·PAM·애플리케이션 인증 검증은 아닙니다.
- 새 upstream 검사: libtasn1 40, Oniguruma 23, jq 9, libpcap 14,801, tcpdump 642,
  libssh 44, HarfBuzz 178, time 10, libgpg-error 15, Libgcrypt 41 통과.
  libpcap 6,569, tcpdump 11, HarfBuzz 82 및 Libgcrypt 대용량 해시 2개는 건너뛰었습니다.
- FreeType/nano/tmux/libXpm의 `make check`를 실질적인 전체 테스트로 계산하지 않았습니다.
  기능은 통합 실행 검사에서 확인했습니다. 읽기 전용 심볼 검사 도구는 9개 테스트 통과.

libssh 설정 파일은 `%config(noreplace)`로 보존하며 EL8 crypto-policy/OpenSSH include를 유지합니다.
커스텀 Libgcrypt는 Red Hat FIPS 검증 모듈이 아닙니다.

## 아직 포함하지 않은 주요 항목

- libidn/libevent/TIFF/Theora: 최신 소스 빌드 완료, SONAME 변경 및 소비 패키지 연계 검토 필요.
- OpenJPEG: 공식 전체 테스트 데이터로 1,585개 통과, `issue226` 관련 2개 실패. 후보에서 제외.
- GCC: 별도 bootstrap 검사 489,896 PASS / 72 FAIL / 2 XPASS. 시스템 GCC 교체본 미완료.
- 커널: 일반 QEMU UEFI 부팅 검사 완료. 실제 VMware·에이전트·Java 검증 미실시.
- glibc/OpenSSL: 별도 경로 평가본이며 시스템 교체나 시스템 취약점 조치로 계산하지 않음.

전체 323종 완료 및 모든 CVE 해결은 아닙니다. 실제 수정 근거는
[SECURITY-EVIDENCE.md](SECURITY-EVIDENCE.md)에 분리해 기록합니다.
`--nodeps`, `--force`, `--allowerasing`으로 충돌을 우회하지 않습니다.
