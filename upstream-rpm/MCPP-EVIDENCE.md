# MCPP 2.7.2-3 수정 근거

대상은 `linuxoss-mcpp-evaluation-2.7.2-3.linuxoss.el8.x86_64.rpm`입니다.
SHA-256: `cad0d1564c2a5160e588902d34eedb82999e5d63d41f9ee6621483304ba80895`.
`/opt/linux-oss/mcpp-2.7.2`에 설치하는 별도 평가본이므로 기존 배포판 mcpp/libmcpp의
취약점까지 해결한 것으로 계산하지 않습니다.

- [Debian CVE-2019-14274 기록](https://security-tracker.debian.org/tracker/CVE-2019-14274)이 지정한 수정은
  2.7.2-5부터 포함됩니다. 공식 Debian 2.7.2-5.3 소스 패키징의 전체 패치 순서를 반영했습니다.
- 패치 아카이브 SHA-256은 `280ba2407e3251d406eb1aeb70fb8219d191ced28a56245c4beda0db461f174a`입니다.
- [upstream bug 13](https://sourceforge.net/p/mcpp/bugs/13/)의 `test-do_msg01`, `test-do_msg02`를
  실제 빌드한 실행 파일과 라이브러리에 입력했습니다.
- Debian 패치 적용 뒤 두 번째 입력에서 `get_line`의 길이 0 버퍼 앞쪽 읽기가 남았습니다.
  `patches/mcpp-zero-length-line.patch`는 경고 후 해당 입력 행을 건너뛰어 `ptr[-1]` 접근을 막습니다.
  이는 자체 보완 패치이며 upstream이 승인한 것으로 표현하지 않습니다.
- 최종 빌드에서 두 재현 입력 모두 Valgrind `ERROR SUMMARY: 0 errors`를 확인했습니다.
  잘못된 C 입력의 정상적인 오류 종료 코드 22를 허용하며 Valgrind 오류 코드 99는 실패 처리합니다.
- 매크로 정의·전처리 결과 42 확인도 통과했습니다. 누수 검사는 이 판정에 포함하지 않았습니다.

SPEC와 SRPM에 패치 및 재현 입력을 포함하고 `sources.lock.json`에 각각의 출처와 해시를 기록했습니다.
Trivy 수정 판정은 위 RPM/SRPM 및 설치된 비설정 파일 해시가 일치할 때 이 CVE 한 건에만 적용합니다.
전체 MCPP 취약점, 다른 RPM 또는 실행 중 프로세스의 상태를 보증하지 않습니다.
