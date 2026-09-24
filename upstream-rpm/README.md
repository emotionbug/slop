# RHEL 8 전체 취약 RPM의 upstream 재빌드 작업

대상은 제공된 취약점 CSV의 **323개 패키지 이름 전체**입니다. rsync, GCC, 커널,
glibc, OpenSSL을 포함하며 위험도가 높다는 이유로 분석 대상에서 제외하지 않습니다.
실제 서버에서 추출한 RPM 메타데이터로 **323종 → 140개 배포판 Source RPM 묶음**을 확인했습니다.
한 Source RPM에 여러 upstream 소스가 포함될 수 있어 실제 빌드 프로젝트 수와는 다릅니다.
서버별 수집 자료와 상세 분석 결과는 로컬의 무시된 폴더에만 보관합니다.

## 현재 배포본: 20260924-7

[전체 평가 산출물](ALL-BUILDS.md): 바이너리 **342개**, 소스 RPM **162개**.
원래 140개 Source RPM 묶음 중 134개에 대응하는 빌드가 있으며,
323개 이름 중 201개와 같은 이름의 산출물이 있습니다.
별도 경로·일부 기능만 만든 경우를 포함하며 전체 교체 완료를 뜻하지 않습니다.

[77 RPM 묶음](CANDIDATES.md)은 참조 컨테이너 DNF 설치·의존성·실행 검사를 통과했습니다.
서버 적용 전에는 묶음의 읽기 전용 사전 검사로 DNF 예정 작업과 제거 심볼 600개를 함께 확인합니다.
[Trivy v3](native-trivy/README.md)는 전체 자체 RPM 카탈로그와 upstream NVD 피드를 결합합니다.
설치 파일이 일치하는 명시적 수정 근거만 적용하고 미해결 CVE와 범위 부족은 유지합니다.

## 이전 단계와 상세 검증 기록

- 323개 이름을 모두 포함한 소스 프로젝트 대응표와 검증 분류 생성.
- 공식 upstream 공개 릴리스 후보 조회 도구 작성. 후보는 자동으로 빌드 버전에
  채택하지 않습니다. 실제 최신 안정판·유지보수 계열·API 전환 여부를 검토해야 합니다.
- Dockerfile 빌드 성공. 개발기의 Podman에서 검증했으며 Docker CLI 실행은 미검증입니다.
- rsync 3.5.1의 바이너리 RPM과 SRPM 생성. upstream 테스트 270개 통과, 90개 건너뜀.
- 별도 UBI 8.10에서 이전 rsync 설치 → 자체 RPM 업그레이드 → `dnf check` 통과.
- 로컬 복사 및 기존 rsync 3.1.3과의 송·수신 프로토콜 테스트에서 내용·심볼릭 링크·
  하드링크 보존 확인. 이는 로컬 파이프 테스트이며 실제 SSH/상대 서버 테스트가 아닙니다.
- zlib 1.3.2의 zlib/zlib-devel RPM, PCRE2 10.48의 8/16/32비트 라이브러리와
  개발용 RPM 제작 및 upstream 테스트 통과.
- 별도 UBI 8에서 위 라이브러리 업그레이드와 `dnf check`, Java 8/Python 압축,
  PCRE2 JIT 컴파일·매칭 테스트 통과.
- 실제 서버 헤더와 rsync/zlib/PCRE2 교체 RPM을 비교했을 때 충족되지 않는
  **이름 기반 의존성은 0개**. 파일·rich dependency·모듈·설치 스크립트·실행 중
  프로세스의 라이브러리 사용 여부까지 해결한 결과는 아닙니다.
- OpenSSL 4.0.2의 별도 경로 평가용 RPM 생성. upstream 4,386개 테스트와
  UBI 설치·서명 생성/검증·TLS 1.3 로컬 통신 통과. 시스템 OpenSSL을 교체하지 않습니다.
- pahole/dwarves 1.32 빌드 도구 RPM 생성. 최신 커널의 BTF 빌드에 사용합니다.
- Expat 2.8.5와 XZ 5.8.4의 교체 RPM 5종 생성. Expat parser 테스트와
  XZ 22개 테스트 통과. 앞의 7종과 함께 UBI에서 설치·DNF·Python XML/XZ·
  Java/rsync/PCRE2 연동 테스트를 통과했습니다.
- Expat/XZ의 기존 UBI 공개 심볼 74개/198개가 유지되는 것을 확인했습니다.
  자료구조 크기·함수 의미·실제 서버 프로그램 전체의 ABI 검증은 아닙니다.
- Expat 개발용 RPM에 필요한 `cmake-filesystem`은 공식 UBI RPM을 확보하고
  Red Hat 서명을 검증했습니다. 12종 교체 RPM과 보조 RPM을 합친 이름 기반
  의존성 검사에서 누락은 0개이며, 파일/rich dependency 등 1,180건은 미검증입니다.
- libpng 1.6.58은 36개 upstream 테스트를 통과했고 RHEL의 Epoch 2를 유지합니다.
  Little CMS 2.19.1도 upstream 테스트를 통과했습니다. 기존 UBI 라이브러리로
  연결한 동일 실행파일이 교체 전후 PNG/색상 변환 테스트를 통과했고,
  기존 PNG 493개/LCMS 360개 공개 심볼이 유지됩니다.
- c-ares 1.34.8은 오프라인 테스트 1,140개와 fuzz suite 2개를 통과했습니다.
  외부 DNS 테스트는 62개 중 60개 통과, 2개 ANY 질의 실패입니다. 독립 질의에서도
  DNS 서버의 RCODE 4 응답을 재현했습니다. 전부 통과한 것으로 기록하지 않습니다.
  UBI 설치·DNS 파서 검증과 별도 Rocky EL8 참조 라이브러리의 60개 심볼 비교는
  통과했습니다. 후자는 정확한 RHEL 바이너리와의 비교는 아닙니다.
- sed 4.10, diffutils 3.12(보안 패치 2개 포함), patch 2.8, gawk 5.4.1의
  빌드·원본 테스트·UBI 기능 검사도 통과했습니다. 상세 범위는 CANDIDATES.md에 기록합니다.
- Bison 3.8.2-3, cpio 2.15-2, bzip2 1.0.8, tar 1.35-2에 추가 보안 패치를 반영했습니다.
  원본 테스트와 수정 전후 회귀 검사, UBI 기능 검사의 범위는 SECURITY-EVIDENCE.md와
  CANDIDATES.md에 기록합니다. 최신 정식 버전에도 추가 패치가 필요했던 사례입니다.
- 이전 배포본의 **24종 교체 RPM + 공식 UBI 보조 RPM 1종**을 함께 검증했습니다.
  UBI 기능 검사와 이름 기반 의존성 검사 통과, downgrade 0개입니다.
  파일/rich dependency 등 1,172건과 실제 서버 적용은 아직 미검증입니다.
  최종 UBI 환경의 자체 RPM 이름이 정확히 24종인 것도 확인했습니다.

binutils 2.47은 GCC Toolset 14로 재검증하여 앞선 LTO 실패 12개가 해결됐습니다.
그러나 CTF `Slice` 테스트 1개가 실패해 배포를 보류합니다. assembler 2,098개,
linker 3,263개, binutils 349개, libsframe 168개, libctf 39개가 통과했습니다.
GCC 16.2는 3단계 bootstrap 빌드와 전체 회귀 테스트를 마쳤습니다.
본 검사에서 489,896개 통과, 예상 밖 실패 72개와 예상 밖 통과 2개가 있어
전체 통과로 기록하지 않습니다. 별도 진단 실행의 건수는 본 검사 합계에서 제외합니다.
별도 비교에서 C++ 실패 33건과 C 링크 경고 실패 1건은 기본 PIE/스택 보호 옵션의
영향으로 재현됐고, 비교용 옵션으로 실행한 동일 검사 408개는 통과했습니다.
컴파일러의 기본 보호 옵션을 제거하거나 전체 검사의 실패를 삭제한 것은 아닙니다.
GCC 16을 사용한 binutils 전체 재검증에서도 CTF Slice 1개가 실패했습니다.
glibc 2.44는 별도 경로 평가 RPM/SRPM을 만들었습니다. 원본 검사 7,177개 통과,
121개 환경 미지원, 16개 예상 실패이며 예상 밖 실패는 0개입니다. UBI에서 새 libc를
명시적으로 사용한 Python의 스레드/NSS/SQLite/압축/OpenSSL 및 Java 8의
스레드/RSA/압축 검사를 통과했습니다. 실제 프로세스의 메모리 매핑으로 새 libc 사용을
확인했습니다. 이 패키지를 설치해도 시스템 glibc의 취약점이 해결되는 것은 아닙니다.

Java 8을 명시적 로더로 실행하면 `/proc/self/exe`가 java가 아닌 로더를 가리켜
JRE 경로 탐색이 실패했습니다. [OpenJDK launcher 소스](https://github.com/openjdk/jdk8u/blob/master/jdk/src/solaris/bin/java_md_solinux.c)의
탐색 방식에 맞춰 일회용 컨테이너의 JRE bin 폴더에 평가 로더만 복사한 뒤 재검증했습니다.
기존 Java 바이너리를 고치거나 실제 서버의 설치 경로를 바꾼 검사가 아닙니다.

Linux 7.2.7 RPM은 빌드를 마쳤고 일반 QEMU UEFI 환경에서 PVSCSI·XFS·VMXNET3·
device-mapper 테스트를 통과했습니다. 모듈의 디버그 정보를 제거한 약 82.4 MiB
커널 RPM으로 다시 부팅을 확인했습니다. 실제 서버의 부팅·SSH·Java·에이전트 및
RHEL 커널 부패키지 전체 호환 검증은 남아 있어 공개 설치 후보 묶음에는 넣지 않습니다.
일반 QEMU 테스트는 서버 복제 VM 검증을 대체하지 않습니다.
Zstandard 1.5.7과 libjpeg-turbo 3.2.0은 빌드·upstream 테스트 및 기본 기능 검사를
통과했습니다. 각각 `ZSTD_getSequences`, `jpeg_std_message_table` 심볼이 제거되어
이전 배포본에서는 보류했고, 현재 배포본에는 **서버 확인이 필요한 조건부 후보**로
포함했습니다. Zstandard의 구형 ZBUFF API 21개는 활성화해 보존했습니다.
두 심볼은 upstream 실험용/내부 API이지만 기존 사용 프로그램이 없다고 단정할 수 없습니다.

OpenSSL의 첫 테스트 실행은 생성한 인증서가 아직 유효하지 않다는 오류로 실패했고,
동일 소스의 두 번째 전체 실행이 통과했습니다. 로그에서 음수 경과 시간도 관찰되어
빌드 VM 시계 변동의 영향을 의심하지만, 원인이 확정된 것으로 기록하지 않습니다.

**323종 전체의 최신판 검토·RPM 제작·서버 적용은 완료되지 않았습니다.**
GCC/커널/glibc 및 나머지 프로젝트별 SPEC 완성과 역의존성 재빌드가 남아 있습니다.
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
  linux-oss-upstream-builder:el8 bash /recipe/run-build.sh build-rpm.sh /recipe/specs/rsync.spec
```

SPEC마다 별도 빌드와 검증이 필요합니다. `build-rpm.sh`는 지정한 SPEC만 빌드하고,
의존성이나 테스트가 실패하면 중단합니다.
장시간 빌드는 컨테이너 이름을 지정하고 `--rm`을 생략하면 실패 증거와 빌드 캐시를
보존할 수 있습니다. `run-build.sh`는 실행 스크립트를 컨테이너에 복사한 뒤 실행해
작업 중 recipe 편집이 진행 중인 셸 입력을 바꾸지 않도록 합니다.

`check-removed-symbol-users.py`는 실제 서버의 ELF import/COPY relocation을
읽기 전용으로 검사합니다. 기본 경로는 `/usr/bin`, `/usr/sbin`, `/usr/lib`,
`/usr/lib64`, `/usr/libexec`, `/opt`, `/usr/local`입니다. Java의 `/usr/lib/jvm`도
포함합니다. 다른 애플리케이션 경로는 인수로 **추가**합니다.
`--only-roots`를 명시한 경우에만 기본 경로를 제외합니다.

```bash
sudo /usr/libexec/platform-python check-removed-symbol-users.py
# 별도 설치 경로가 있는 경우의 예. 실제 존재하는 경로만 추가하세요.
sudo /usr/libexec/platform-python check-removed-symbol-users.py /data/apps
```

`errors[].kind`는 끊어진 링크(`broken_symlink`), 없는 경로(`missing_path`),
권한 오류 등을 구분합니다. 경로를 삭제하거나 링크를 수정하지 않습니다.
디렉터리 링크는 자동으로 따라가지 않으며, 기본/추가 검사 경로 밖의 대상은
`directory_symlinks_outside_roots`에 표시합니다. 필요한 대상의 실제 경로를 인수로
추가해 재검사할 수 있습니다. 오류/누락 경로가 있으면 종료 코드 2, 직접 참조만
발견되면 1, 둘 다 없으면 0입니다. `coverage_complete_for_declared_roots`는
지정한 파일 경로의 검사 범위에만 해당합니다. 직접 참조가 없어도 dlsym/플러그인,
현재 로드된 삭제 파일, 실제 서비스의 교체 호환성을 확인한 것은 아닙니다.
결과 파일은 공개 저장소에 올리지 않습니다.

## rsync 검증용 RPM의 현재 범위

- 자체 Vendor/Release를 가진 검증용 RPM이며 Red Hat 서명이 없습니다.
- rsync 소스는 공식 릴리스 서명을 검증했습니다. RPM 자체는 미서명 상태이고,
  `rpmkeys --checksig`로 확인한 것은 다이제스트입니다.
- xxHash 0.8.4를 정적으로 포함하며 `Provides: bundled(xxhash)`와 SRPM에 기록합니다.
- 현재 EL8의 `libcrypto.so.1.1` 등에 연결됩니다. OpenSSL까지 최신화한
  전체 교체 트랜잭션의 완성품은 아닙니다.
- 데몬 서비스와 rrsync는 이 검증용 패키지에 추가하지 않았습니다.
  수집 시점의 대상 서버에는 rsync-daemon이 없었습니다. 향후 다른 서버에서는
  해당 패키지와 기능 사용 여부를 별도로 확인해야 합니다.
- upstream 테스트 생략은 root/ASan/TCP/이전 peer 등의 조건에 따른 것입니다.
  모든 보안 조건의 검증 완료를 의미하지 않습니다.
- Trivy가 자체 RPM을 탐지하지 못한 것을 취약점 해결로 판정하지 않습니다.

## 서버 정보와 정적 비교

[INVENTORY.md](INVENTORY.md)의 읽기 전용 스크립트로 Source RPM과
Requires/Provides/Conflicts/Obsoletes를 수집합니다. 현재 대상 서버 정보는 수령했습니다.
`analyze-scope.py --inventory DIRECTORY`와 `analyze-inventory.py DIRECTORY CSV`로
CSV의 과거 버전과 실제 설치 버전, 직접 의존성, 커널 드라이버 조건을 구분합니다.

`check-rpm-capabilities.py`는 EL8의 platform-python/librpm으로 RPM 헤더를 비교합니다.
파일 충돌·모듈 필터·설치 스크립트 순서·프로그램 실행 검증은 별도로 수행해야 합니다.
정적 비교 통과를 서버 설치 검증으로 취급하지 않습니다.

대상 서버의 별도 복제 VM은 없습니다. 개발기 컨테이너 테스트는 실제 서버의
VMware 부팅·SSH·외부 보안 에이전트·Java/Tomcat 연동을 증명하지 않습니다.
`Dockerfile.kernel-boot-test`와 `validate-kernel-boot.sh`는 QEMU의 UEFI,
PVSCSI 디스크/XFS, VMXNET3, device mapper를 시험하도록 준비했습니다.
해당 일반 QEMU 부팅 검사는 통과했지만 실제 서버의 복제 환경을 검증한 것은 아닙니다.

`gcc-plugin-annobin`처럼 배포판에서 추가 소스를 묶은 패키지는 GCC 소스만으로
만들 수 없습니다. `perf`/`python3-perf`/`bpftool`도 커널 RPM 생성만으로 교체되지
않으므로 별도 산출물과 테스트가 필요합니다.

## Trivy와 자체 RPM

Trivy 0.74.0으로 설치된 자체 RPM 52개를 실제 검사했습니다. 목록과 SBOM에는
식별되지만 모두 `third-party`로 분류되어 기본 RHEL 취약점 검사에서 제외됩니다.
CVE 0건을 조치 완료로 해석하지 마세요. [실제 비교 결과, 누락 CSV 도구 및 추가 검사 연계 방법](TRIVY-INTEGRATION.md)을 참고하세요.

[native Trivy 모듈](native-trivy/README.md)은 52개 자체 RPM의 제작 기록과 설치 정보를
선택한 NVD CPE 피드 및 22개 CVE 수정 근거와 함께 같은 Trivy JSON/CSV에 연결합니다.
`actionable.csv`로 확인할 항목을 모으고, 피드·제품 매핑의 범위 부족도 별도로 남깁니다.
전체 자체 RPM의 CVE 범위가 완성됐다는 뜻은 아닙니다.

출력 파일, CSV, 서버 수집 정보는 공개 Git 저장소에 추가하지 마세요.
