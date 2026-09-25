# EL8 호환성 보완 묶음 20260925-6

이 묶음은 앞 단계에서 ABI·의존성·시험 실패로 남아 있던 패키지를 다시 제작한 결과입니다. 기존 설치 묶음을 포함하며, 설치기는 **서버에 이미 있는 이름의 패키지를 업그레이드하고 필요한 로컬 의존성만 추가**합니다. 설치된 버전이 더 높으면 내리지 않습니다.

## 보완 내용

| 프로젝트 | 선택한 빌드 | 해결 방법 |
|---|---|---|
| binutils | 2.47-3 | GCC 8의 예전 slim-LTO 형식을 인식하도록 BFD 수정. 앞서 실패한 12개 링크 시험 해결 |
| GDK-Pixbuf | 2.44.8-3 | EL8 GLib 2.56 기준 재빌드, 기존 `query-loaders-64` 경로와 로더 캐시 갱신 복원 |
| MTR | 2:0.96-3 | raw IPv4 패킷 길이 계산 보완, CVE-2026-14461 수정 반영 |
| OpenJPEG | 2.5.4-3 | 잘못된 입력을 성공으로 기대하던 기존 시험을 오류 거부 시험으로 수정. 정상 디코딩과 구분 |
| libidn | 1.34-6 | `.so.11`과 EL8 Stringprep 구조체 유지, CVE-2026-57053 백포트 |
| libbpf | 0.8.3-1 | `.so.0` 유지, ELF section-count 및 빈 프로그램 처리 보안 수정 백포트 |
| libxslt | 1.1.32-7 | EL8 libxml2 ABI를 유지하며 배포판 패치와 2019-13117/13118, 2025-11731 추가 반영 |
| libtiff | 4.3.0-2 | `.so.5` 유지. Ubuntu 48개 패치와 2026년 EL8/업스트림 수정 추가 |
| Graphviz | 12.2.1-2 | 기존 cgraph/gvc/cdt SONAME 계열 유지, GD 플러그인 분리와 정확한 의존성 제공 |
| GTK2 | 2.24.33-5 | 기존 GLib 기준 빌드, CVE-2024-6655 수정, devel과 런타임 버전 의존성 일치, GTK3와 충돌하는 도구 이름 분리 |
| libevent | 2.1.8-12 | `.so.6` 유지, CVE-2026-63379/63381/63382/63383/63384/63385/63387/63388 백포트 |
| Brotli | 1.2.0-1 | FreeType 개발용 패키지의 의존성까지 로컬 RPM으로 제공 |
| bzip2 | 1.0.8-2 | 기존 보안 패치 유지, 누락된 pkg-config 메타데이터 추가 |

라이브러리와 짝이 맞는 Cairo, FreeType, HarfBuzz, libgcrypt, libgpg-error, JPEG, PNG, Pixman 개발용 RPM도 포함합니다. `--nodeps`, `--allowerasing` 또는 파일 충돌 강제 덮어쓰기를 사용하지 않습니다.

## 시험과 판정 범위

최종 RPM 수, SHA-256, 실제 설치 시험 결과는 `COMPAT-WAVE-MANIFEST.json`에 기록합니다. EL8 컨테이너에 기존 라이브러리로 미리 컴파일한 소비 프로그램을 둔 뒤, 같은 바이너리를 업그레이드 후 다시 실행합니다. DNF transaction, 공유 라이브러리 연결, GCC C/C++ LTO, TIFF·XSLT·Graphviz·GTK·GDK-Pixbuf, MTR 로컬 패킷, 보안 입력 회귀 검사를 함께 수행합니다.

libevent 시험은 모든 원래 assertion을 유지합니다. WSL 스케줄링 지연으로 실제로 실패한 네 시간 제한 시험(`thread/no_events`, `thread/conditions_simple`, `main/loopexit`, `main/persistent_active_timeout`)만 처음 실패했을 때 새 프로세스로 최대 5회 재시도하며, **3회 연속 통과**해야 합니다. 그 밖의 실패는 재시도하지 않습니다. 이 변경은 시험 도구에만 적용되며 라이브러리의 제한값을 완화하지 않습니다.

OpenJPEG는 정상·오류 입력을 포함한 전체 1,586개 CTest 집합을 실행합니다. 이 중 `issue226`은 손상된 다음 타일 마커를 가진 파일이므로 기존 성공·출력 MD5 기대를 오류 거부 기대와 무출력 확인으로 바꿨습니다. 잘못된 파일을 정상 파일로 읽도록 디코더를 변경하지 않았습니다.

MTR의 설치 후 시험은 명령 파서와 IPv4/IPv6 루프백 패킷 10건, 실제 `mtr --report` 실행을 포함합니다. 0.96의 첫 시퀀스 값 `MIN_PORT=33434`와 시험 수신기의 과거 상수 `33000`이 달라, 시험 수신기만 실제 프로토콜에 맞췄습니다. 패킷 크기·TOS·내용에 대한 assertion은 유지했습니다. 시험 중 외부 DNS를 사용하지 않으며 실패 시 하위 프로세스를 정리합니다.

설치기의 ELF 검사는 버전이 일치하는 실제 라이브러리 제공자와 이번 transaction에서 교체될 새 실행 파일을 확인합니다. 제거되는 SONAME을 직접 요구하는 수동 설치 바이너리도 검사합니다. 해석되지 않은 외부 소비자나 검사 누락은 설치를 중단하며 해당 RPM 자체를 배포 대상에서 제거하지 않습니다. `dlopen`, 변경된 프로세스 환경, 실행 중인 구버전 매핑과 애플리케이션의 모든 동작은 이 정적 검사만으로 증명되지 않습니다.

## Trivy 연계

검사 원본 JSON을 유지합니다. 통합 CSV에서는 패키지 이름·epoch·버전·release·아키텍처와 실제 파일 해시가 모두 일치한 보안 패치만 `fixed-evidence-matched`로 연결합니다. split RPM에 해당 취약 구성요소가 없다는 개별 검토 근거는 `not-affected-evidence-matched`로 구분합니다. multilib 모호성, 파일 변조, 다른 빌드 또는 미등록 CVE에는 이 판정을 적용하지 않습니다.

이전 자체 RPM의 해시도 카탈로그에 남깁니다. NVD의 선택한 CPE 목록에 대한 부분적인 조회이며 누락·지연·조회 오류를 숨기지 않습니다. 빌드 성공이나 최신 버전이라는 이유만으로 `all_cves_fixed`를 참으로 바꾸지 않습니다.

## 완료한 참조 환경 결과

- 누적 161개 RPM, 앞 릴리스 대비 새 빌드 38개, 이번 선택 프로젝트 13개, 소스 RPM 15개.
- 실제 DNF transaction: 기존 패키지 43개 교체와 의존성 2개 추가. 설치 후 회귀 검사 36건 통과, 변경 라이브러리 미해결 심볼 0건.
- 새 Trivy 실행: 자체 RPM 144개를 수집했고 수정 근거 118행, 구성요소 비해당 근거 142행을 출력했습니다. 이는 서로 다른 CVE 수나 운영 서버의 조치 건수가 아닙니다.
- 참조 환경에는 여전히 조치/검토 대상 5,004행이 남습니다. 서버 구성과 다르므로 서버의 감소율로 사용하지 않습니다. NVD 조회 미완료·미매핑과 링크만 있는 `pkgconf-pkg-config`의 payload 미검증도 그대로 남깁니다.
- libevent 분리 라이브러리 3개는 원래 링크 계약에 따라 코어 라이브러리와 함께 검사하고 HTTP·스레드 실행으로 확인했습니다.

## 소스 근거

- [libidn ACE 처리 보안 공지](https://lists.gnu.org/archive/html/help-libidn/2026-05/msg00000.html)
- [libbpf ELF section-count 수정](https://github.com/libbpf/libbpf/commit/741277511035893c72a34df05da3b943afa747a4), [빈 프로그램 수정](https://github.com/libbpf/libbpf/commit/d0d382f95a9270dcf803539d6781d6bd67e3f5b2)
- [GTK 모듈 검색 수정](https://gitlab.gnome.org/GNOME/gtk/-/commit/3bbf0b6176d42836d23c36a6ac410e807ec0a7a7)
- [TIFF Ubuntu 소스 배포](https://archive.ubuntu.com/ubuntu/pool/main/t/tiff/), [tiff2pdf 64비트 크기 처리 수정](https://gitlab.com/libtiff/libtiff/-/merge_requests/729), [tiffcrop 이중 해제 수정](https://gitlab.com/libtiff/libtiff/-/merge_requests/753)
- EL8 호환 소스와 기존 배포판 패치: [Rocky Linux 8 BaseOS SRPM](https://download.rockylinux.org/pub/rocky/8/BaseOS/source/tree/Packages/). 배포한 것은 해당 바이너리를 그대로 바꿔 넣은 것이 아니라 명시된 레시피로 EL8에서 제작한 RPM입니다.

각 소스·패치 SHA-256은 `sources.lock.json`, RPM과 SRPM 연결은 카탈로그와 manifest에 고정합니다. OpenJPEG의 `.nosrc.rpm`에는 프로그램 원본과 패치가 포함되며 대형 **시험 데이터 Source1만** 제외합니다. 시험 데이터의 다운로드 경로와 해시는 별도로 고정되어 있습니다.

## 남은 작업

커널, glibc, systemd, SSH/PAM 등 기반 패키지도 영구 제외 목록으로 취급하지 않습니다. 기존 ABI를 유지한 보안 백포트와 부팅·인증·서비스 의존성 보완이 다음 작업입니다. 이 묶음은 해당 기반 패키지의 전체 교체 또는 실제 서버의 재부팅·Java/Tomcat·보안 에이전트 검증을 완료한 결과가 아닙니다. 커널의 기존 설치본과 실행 중 버전은 재부팅 후 다시 구분해야 합니다.
