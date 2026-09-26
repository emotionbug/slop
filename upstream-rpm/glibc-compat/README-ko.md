# EL8 glibc 호환 보안 백포트

`glibc-2.28-251.el8_10.40.linuxoss.1`은 서명을 확인한 Rocky EL8 `.40` SRPM의
기존 배포판 패치에 아래 공식 수정을 추가한 자체 빌드입니다. glibc ABI 2.28과
기존 RPM 이름을 유지합니다. Red Hat 서명·지원 또는 FIPS 인증을 뜻하지 않습니다.

## 실제 추가한 수정

공식 저장소: https://sourceware.org/git/glibc.git

| CVE | 공식 수정 커밋 |
|---|---|
| CVE-2026-18374 | `9765a538ebf8661a6e5578e01e35a3dd30db7eb4` 및 회귀 테스트 `cca93e5d88d3d4ed073c03100467696f652269e7` |
| CVE-2026-19542 | `e2789c46e3bfdcd67a82bea9946b315c179e83d3` |
| CVE-2026-77117 | `68d94bbe50b7577d48998107d632ef3a0df050e3` |
| CVE-2026-80489 | `4dafa087ff5fe7df45bd37dc727e988da6b8c935` |
| CVE-2026-8674 | `506ea57086bfb9ce3daff1c14246a1cb532aba0a` |
| CVE-2026-86805, CVE-2026-95818 | `ed0c137b97eb940b4b64981e84ed806d3276edd9` |
| CVE-2026-6791 | `07c24f35392b727e6100d33edfdf811a6c68c218` |
| CVE-2026-6368 | `e2cefe16c37a617df9f11407cb00a272a6098823` |

동적 로더 수정은 EL8의 include 및 버퍼 구현에 맞춰 포팅했습니다.
DNS 회귀 사례와 wordexp 테스트를 포함하고, 경계 보호 페이지를 만드는 최신
시험 helper도 함께 가져왔습니다. helper는 시험 코드이며 libc 공개 ABI를 바꾸지 않습니다.

`prepare-backport.py`는 이미 배포판 패치가 적용된 EL8 소스에서 통합 패치를
생성하는 보조 도구입니다. 배포 SRPM에는 원본 소스·기존 패치·통합 패치·spec과
변경 파일 해시가 들어 있습니다. 공식 참조 소스 revision은
`3edeb81021feff11a3d0e934d68446f6a67dd1a3`입니다.

## 별도로 구분한 항목

- CVE-2026-19499: glibc 2.38의 `__printf_buffer` 기반 strfmon 재작성에 해당합니다.
  이 EL8 소스는 해당 구현을 포함하지 않습니다.
- CVE-2026-4437 / CVE-2026-4438: `getanswer_ptr` 구현에 해당합니다. EL8의
  `getanswer_r`는 답변 개수 제한과 `res_hnok` 검사를 유지합니다.
- CVE-2026-89092: **nscd 소스의 취약점은 아직 수정하지 않았습니다.** 이번 배포의
  glibc/common/devel/headers/gconv-extra/en/ko/minimal 8개 RPM에는 nscd 실행 파일이
  없으므로 해당 payload에만 구성요소 비해당 근거를 연결합니다. nscd RPM이나
  전체 glibc 소스가 수정됐다는 판정으로 확장하지 않습니다.
  공식 도입 커밋 `d19687d6ebc545b633e14c07429f7892a599d0b9`과 EL8
  `nscd/aicache.c`의 두 unbounded alloca 경로, `nscd/Makefile`의 실행 파일
  연결 대상을 확인했습니다.

## 설치 및 판정 범위

검증 결과는 [VALIDATION.json](VALIDATION.json)에 RPM 해시와 함께 기록했습니다.
전체 glibc 시험에서 6,157건 PASS였고, 컨테이너 제약·시계 동작으로 실패한 9건은
실제 EL8 커널 QEMU에서 모두 통과했습니다. 25 UNSUPPORTED, 16 XFAIL,
2 XPASS는 그대로 기록하며 전체 시험을 무조건 PASS로 바꾸지 않습니다.
동적 로더 Valgrind smoke test는 오류 0건입니다.

새 SRPM의 기본 `%prep`에서 변경 파일 21개가 빌드한 소스와 해시 일치했습니다.
최종 설치기로 OpenSSL과 함께 DNF check/apply한 뒤, glibc 라이브러리 9개의
심볼 3,915개에서 삭제·타입·객체 크기 변경이 없음을 확인했습니다.
TLS 1.2/1.3, Python/curl HTTPS, OpenSSH 공개키+PAM 세션, Java 8의
NSS/스레드/mmap/문자셋/zlib/프로세스 실행 및 Tomcat 9의 실제 JSP HTTP 응답도
통과했습니다. Java는 Temurin 8u504-b01, Tomcat은 9.0.122의 격리 시험입니다.

설치기는 설치되어 있는 패키지 이름만 업그레이드하고, 의존성 때문에 필요한
동일 빌드 패키지를 선택합니다. 다른 버전의 i686 glibc 등 해결되지 않은 의존성이
있으면 DNF transaction에서 멈추며 `--nodeps`나 강제 덮어쓰기를 사용하지 않습니다.

Trivy의 해결 근거는 정확한 RPM/SRPM 해시와 설치된 변경 불가 파일에 묶습니다.
설치 scriptlet이 재생성하는 `gconv-modules.cache`는 RPM 자체도 digest 검증을
제외하므로 변경 불가 파일로 취급하지 않습니다. 실제 libc·로더·문자 변환
라이브러리 해시는 계속 필수로 확인합니다.
업그레이드 후에도 기존 프로세스는 이전 라이브러리를 매핑할 수 있으므로
유지보수 시간에 Java/Tomcat 등 서비스를 다시 시작해야 합니다. 대상 서버의
실제 애플리케이션·보안 에이전트·부팅 검증은 로컬 테스트와 구분합니다.
