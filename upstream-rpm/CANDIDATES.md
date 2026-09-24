# 77 RPM 참조 환경 검증 묶음: 20260924-7

[다운로드](https://github.com/emotionbug/slop/releases/tag/upstream-rpm-candidates-20260924-7)

바이너리 77개(자체 76개 + 공식 UBI cmake-filesystem 1개), 소스 RPM 56개와
체크섬·읽기 전용 사전 검사 도구를 포함합니다. 실제 서버 적용이나 전체 CVE 해결을 완료한 묶음은 아닙니다.

UBI 8.10 참조 컨테이너에 설치하고 DNF 의존성 검사와 실행 검사 10개를 통과했습니다.
검사 범위는 Python/DNF, SQLite FTS5, curl/wget HTTP·인증서를 검증하는 TLS,
OpenSSL4/p11-kit, ncurses/net-tools, GD 및 라이브러리 로딩, Cairo 폰트 렌더링,
sysstat/CIFS 실행 진입점, Flex 생성입니다. 실제 CIFS 마운트나 운영 서비스를 검사하지 않았습니다.
헤더 정적 비교에서는 이름 기반 의존성 누락·downgrade 0개이며 파일/rich dependency 1,188개는 미판정입니다.

## 서버에서 한 번에 확인

`el8-rpm-candidates-20260924-7.tar.gz`와 릴리스 `SHA256SUMS`를 같은 폴더로 옮깁니다.

```bash
sha256sum -c SHA256SUMS
mkdir el8-candidates-77
tar -xzf el8-rpm-candidates-20260924-7.tar.gz -C el8-candidates-77
cd el8-candidates-77
sudo bash preflight-candidates.sh
```

Java/에이전트가 기본 검사 경로 밖에 있으면 마지막 명령 뒤에 실제 설치 경로를 추가합니다.
이 명령은 패키지 설치·삭제·서비스 재시작 없이 `symbol-audit.json`, `dnf-preview.txt`를 수집합니다.
DNF 예정 작업을 거절한 결과의 종료 코드 1 자체는 설치 실패 증거가 아닙니다.
결과에는 서버 경로가 담기므로 공개 저장소에 올리지 마세요.

기존 v6 검사와 새 export 비교를 합쳐 제거된 심볼 **600개 이름**을 확인합니다.
새 비교에서 제거된 export 항목 616개에는 중복·내부 심볼·링커 표식도 포함됩니다.
모두 무해하다고 판정하지 않았으며 직접 import가 없더라도 dlsym, 추가 플러그인과
메모리에 남은 이전 바이너리는 별도로 확인해야 합니다.
`ether-wake`, `mii-diag`, `cairo-sphinx` 제거와 설정 6개 변경도 기록했습니다.

## 설치 후 검사

[Trivy v3 통합 번들](native-trivy/README.md)을 별도 폴더에 풀고 실행합니다.
추가 NVD 피드·RPM/SRPM·설치 파일 해시를 결합하며 공식 RHEL 결과도 보존합니다.
원하는 후보만 실제 서버의 DNF 예정 작업과 호환성을 검토해 적용해야 합니다.
이 문서는 77개 전체에 대한 무조건 설치 명령을 제공하지 않습니다.

## 포함 바이너리

- `rsync-3.5.1-1.linuxoss.el8.x86_64.rpm`
- `zlib-1.3.2-1.linuxoss.el8.x86_64.rpm`
- `zlib-devel-1.3.2-1.linuxoss.el8.x86_64.rpm`
- `pcre2-10.48-1.linuxoss.el8.x86_64.rpm`
- `pcre2-devel-10.48-1.linuxoss.el8.x86_64.rpm`
- `pcre2-utf16-10.48-1.linuxoss.el8.x86_64.rpm`
- `pcre2-utf32-10.48-1.linuxoss.el8.x86_64.rpm`
- `expat-2.8.5-1.linuxoss.el8.x86_64.rpm`
- `expat-devel-2.8.5-1.linuxoss.el8.x86_64.rpm`
- `xz-5.8.4-1.linuxoss.el8.x86_64.rpm`
- `xz-libs-5.8.4-1.linuxoss.el8.x86_64.rpm`
- `xz-devel-5.8.4-1.linuxoss.el8.x86_64.rpm`
- `c-ares-1.34.8-1.linuxoss.el8.x86_64.rpm`
- `libpng-1.6.58-1.linuxoss.el8.x86_64.rpm`
- `lcms2-2.19.1-1.linuxoss.el8.x86_64.rpm`
- `sed-4.10-1.linuxoss.el8.x86_64.rpm`
- `diffutils-3.12-2.linuxoss.el8.x86_64.rpm`
- `patch-2.8-1.linuxoss.el8.x86_64.rpm`
- `gawk-5.4.1-1.linuxoss.el8.x86_64.rpm`
- `bison-3.8.2-3.linuxoss.el8.x86_64.rpm`
- `cpio-2.15-2.linuxoss.el8.x86_64.rpm`
- `bzip2-1.0.8-1.linuxoss.el8.x86_64.rpm`
- `bzip2-libs-1.0.8-1.linuxoss.el8.x86_64.rpm`
- `tar-1.35-2.linuxoss.el8.x86_64.rpm`
- `cmake-filesystem-3.26.5-2.el8.x86_64.rpm`
- `libtasn1-4.21.0-1.linuxoss.el8.x86_64.rpm`
- `popt-1.19-1.linuxoss.el8.x86_64.rpm`
- `oniguruma-6.9.10-2.linuxoss.el8.x86_64.rpm`
- `nano-9.2-1.linuxoss.el8.x86_64.rpm`
- `libXpm-3.5.19-1.linuxoss.el8.x86_64.rpm`
- `jq-1.8.2-1.linuxoss.el8.x86_64.rpm`
- `tmux-3.7c-1.linuxoss.el8.x86_64.rpm`
- `libpcap-1.11.0-1.linuxoss.el8.x86_64.rpm`
- `tcpdump-4.99.7-1.linuxoss.el8.x86_64.rpm`
- `file-5.48-1.linuxoss.el8.x86_64.rpm`
- `file-libs-5.48-1.linuxoss.el8.x86_64.rpm`
- `python3-magic-5.48-1.linuxoss.el8.noarch.rpm`
- `libssh-0.12.2-1.linuxoss.el8.x86_64.rpm`
- `libssh-config-0.12.2-1.linuxoss.el8.noarch.rpm`
- `zstd-1.5.7-1.linuxoss.el8.x86_64.rpm`
- `libzstd-1.5.7-1.linuxoss.el8.x86_64.rpm`
- `libzstd-devel-1.5.7-1.linuxoss.el8.x86_64.rpm`
- `libjpeg-turbo-3.2.0-1.linuxoss.el8.x86_64.rpm`
- `harfbuzz-14.5.0-1.linuxoss.el8.x86_64.rpm`
- `freetype-2.14.3-1.linuxoss.el8.x86_64.rpm`
- `time-1.10-1.linuxoss.el8.x86_64.rpm`
- `libgpg-error-1.61-1.linuxoss.el8.x86_64.rpm`
- `libgcrypt-1.12.4-1.linuxoss.el8.x86_64.rpm`
- `coreutils-9.12-1.linuxoss.el8.x86_64.rpm`
- `coreutils-common-9.12-1.linuxoss.el8.noarch.rpm`
- `libsolv-0.7.40-1.linuxoss.el8.x86_64.rpm`
- `protobuf-c-1.5.2-1.linuxoss.el8.x86_64.rpm`
- `jbig2dec-libs-0.20-1.linuxoss.el8.x86_64.rpm`
- `wget-1.25.0-1.linuxoss.el8.x86_64.rpm`
- `flex-2.6.4-1.linuxoss.el8.x86_64.rpm`
- `gd-2.3.3-1.linuxoss.el8.x86_64.rpm`
- `cups-libs-2.4.19-1.linuxoss.el8.x86_64.rpm`
- `efivar-libs-39-1.linuxoss.el8.x86_64.rpm`
- `net-tools-2.10-1.linuxoss.el8.x86_64.rpm`
- `ncurses-6.6-1.linuxoss.el8.x86_64.rpm`
- `ncurses-base-6.6-1.linuxoss.el8.x86_64.rpm`
- `ncurses-libs-6.6-1.linuxoss.el8.x86_64.rpm`
- `avahi-libs-0.8-1.linuxoss.el8.x86_64.rpm`
- `p11-kit-0.26.5-1.linuxoss.el8.x86_64.rpm`
- `p11-kit-trust-0.26.5-1.linuxoss.el8.x86_64.rpm`
- `pixman-0.46.4-1.linuxoss.el8.x86_64.rpm`
- `cairo-1.18.6-1.linuxoss.el8.x86_64.rpm`
- `cairo-gobject-1.18.6-1.linuxoss.el8.x86_64.rpm`
- `sqlite-3.53.4-1.linuxoss.el8.x86_64.rpm`
- `sqlite-libs-3.53.4-1.linuxoss.el8.x86_64.rpm`
- `curl-8.22.0-1.linuxoss.el8.x86_64.rpm`
- `libcurl-8.22.0-1.linuxoss.el8.x86_64.rpm`
- `linuxoss-openssl4-4.0.2-1.linuxoss.el8.x86_64.rpm`
- `sysstat-12.8.0-1.linuxoss.el8.x86_64.rpm`
- `cifs-utils-7.7-1.linuxoss.el8.x86_64.rpm`
- `rpcbind-1.3.1-1.linuxoss.el8.x86_64.rpm`
- `unzip-debuginfo-6.0-71.linuxoss.el8.x86_64.rpm`
