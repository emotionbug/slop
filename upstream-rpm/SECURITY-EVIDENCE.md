# 보안 수정 확인 범위

이 문서는 자체 RPM 버전이 높아졌다는 이유만으로 전체 CVE를 해결 처리하지 않기 위한
근거 목록입니다. 로컬 빌드·테스트 결과이며 실제 서버 설치·재검사 결과가 아닙니다.

| 프로젝트 | 확인한 보안 수정 | 근거 및 한계 |
|---|---|---|
| sed 4.10 | CVE-2026-5958 | [CNA 공지](https://cert.pl/en/posts/2026/04/CVE-2026-5958/)의 수정 버전. 원본 테스트 및 UBI 기능 검사 통과 |
| gawk 5.4.1 | CVE-2026-40467, 40468, 40469, 40553 | [CNA 공지](https://cert.pl/en/posts/2026/07/CVE-2026-40467/)의 수정 버전. 원본 테스트 및 MPFR·확장 기능 검사 통과 |
| diffutils 3.12-2 | CVE-2026-53910 | 최신 정식 소스에 upstream 커밋 `73ed7ce85cc78effb94daf028c9af6b4e5252e50`, `9ff04d5b84743e331e80b589335a52c5480d1815` 반영. [Ubuntu 공식 소스 발표](https://lists.ubuntu.com/archives/stonking-changes/2026-August/007706.html)의 SHA-256과 패치 아카이브 대조. 원본 테스트 및 과도한 행 번호 3개 거부 확인 |
| Bison 3.8.2-3 | CVE-2026-56389, CVE-2026-56390 | [CNA 공지](https://cert.pl/en/posts/2026/07/CVE-2026-56389/)의 upstream 수정 2개 반영. grammar 파서를 다시 생성. 원본 RPM에서 프로그램 지정 및 출력·헤더 경로 이탈 3개 재현, 수정 RPM에서 같은 입력 차단 |
| cpio 2.15-2 | CVE-2026-66484, CVE-2026-66485, CVE-2026-66486 | [CNA 공지](https://cert.pl/en/posts/2026/08/CVE-2026-66484/)의 수정 3개 반영. 원본과 수정 RPM으로 hardlink 경로 이탈·터미널 escape·긴 경로 스택 오류 비교. 수정 RPM의 원본 테스트 17개 통과 |
| bzip2 1.0.8-1 | CVE-2026-42250 및 recovery 출력 파일 생성 보호 | [CNA 공지](https://cert.pl/en/posts/2026/05/CVE-2026-42250/)의 경계 검사 패치 반영. ASan으로 원본 소스의 전역 배열 초과 접근을 재현하고 패치 소스에서 차단 확인. RPM의 기존 파일/심볼릭 링크 덮어쓰기 거부 및 기존 라이브러리 연결 프로그램 동작 확인 |
| tar 1.35-2 | CVE-2025-45582, CVE-2026-5704 관련 패치 묶음 | [Ubuntu 수정 및 회귀 공지](https://ubuntu.com/security/notices/USN-8477-3)의 1.35+dfsg-4ubuntu0.4 소스에 포함된 보안·회귀 수정 반영. 공식 소스 아카이브의 SHA-256을 DSC와 대조. 아래 잔여 항목은 해결로 판정하지 않음 |
| libtasn1 4.21.0 | CVE-2025-13151 | [GNU 릴리스 공지](https://lists.gnu.org/archive/html/info-gnu/2026-01/msg00003.html)의 수정 버전. 소스 OpenPGP 서명 확인, upstream 검사 40개 및 DER 길이 입력 검사 통과 |
| libssh 0.12.2 | CVE-2026-59843 | [upstream 보안 릴리스](https://www.libssh.org/2026/07/28/libssh-0-12-2-security-release/)의 수정 버전. upstream 검사 44개와 호스트 키를 대조한 로컬 공개키 인증·명령 실행 통과. 실제 서버 SSH 정책 검증은 아님 |
| jq 1.8.2 | CVE-2026-32316, 33947, 33948 등을 포함한 릴리스 보안 수정 | [공식 릴리스 노트](https://github.com/jqlang/jq/releases/tag/jq-1.8.2)에 수정 항목 명시. upstream 검사 9개 통과. 외부 Oniguruma 6.9.10-2에 연결하여 JSON·정규식 실행 확인. CSV의 모든 jq 항목과 개별 대조 완료를 의미하지 않음 |
| libsolv 0.7.40 | CVE-2026-9149, CVE-2026-9150, CVE-2026-48863 수정 이력 포함 | [upstream 변경 이력](https://github.com/openSUSE/libsolv/blob/0.7.40/package/libsolv.changes)의 0.7.37/0.7.38 보안 수정이 포함된 버전. upstream 검사 29개와 설치 후 DNF/hawkey 조회 통과. EL8의 AppData·Conda 기능을 포함하여 기존 export 유지 |

coreutils 9.12, protobuf-c 1.5.2, jbig2dec 0.20도 소스 빌드·로컬 검증을 마쳤습니다.
이 세 프로젝트는 버전 증가만으로 CSV의 모든 CVE를 해결 처리하지 않습니다.
protobuf-c의 [공식 릴리스 이력](https://github.com/protobuf-c/protobuf-c/releases)은
1.5.1의 unknown-fields 포인터 초기화 수정 등을 설명하며 1.5.2에 포함돼 있습니다.

Libgcrypt 1.12.4는 [공식 안정판 안내](https://gnupg.org/software/libgcrypt/)와
[공식 SHA-256 목록](https://gnupg.org/download/integrity_check.html)을 대조했습니다.
Libgcrypt 검사 41개와 SHA256/AES 알려진 정답 벡터를 통과했고 대용량 해시 검사
2개는 건너뛰었습니다. 의존 라이브러리 libgpg-error 1.61 검사 15개도 통과했습니다.
이 결과만으로 모든 암호 취약점의 해결이나 Red Hat FIPS 검증을 주장하지 않습니다.

Oniguruma 6.9.10-2의 추가 패치는 EL8의 POSIX 함수 이름 8개를 현재 구현에 연결하는
**호환성 패치**입니다. 별도 보안 수정으로 계산하지 않습니다. 최신 FreeType 등의
제거된 심볼도 취약점 수정 여부와 별개로 [호환성 확인 대상](CANDIDATES.md)에 기록합니다.

diffutils 입력 검사는 자원 한도를 둔 오류 처리 검사이며 모든 공격 경로에 대한 증명은
아닙니다. GNU patch 2.8은 빌드 및 기능 검사를 통과했지만 CVE별 수정 근거를 아직
모두 확인하지 않았습니다. 다른 CVE는 이 표만으로 해결 처리하지 않습니다.

Bison 3.8.2와 cpio 2.15는 최신 정식 소스에도 보안 문제가 남아 있어 추가 패치를
반영했습니다. 회귀 검사는 네트워크가 차단된 일회용 컨테이너의 임시 파일과 무해한
도우미 프로그램만 사용합니다. cpio 메모리 검사는 스택·주소 공간·실행 시간에 한도를 둡니다.

Bzip2의 ASan 검사는 별도 계측 빌드에 대한 결과입니다. 배포 RPM 자체에 ASan을
넣은 것은 아니며, 배포 RPM은 UBI에서 별도로 설치·기능 검사했습니다.
Ubuntu에서 가져온 패치 아카이브는 공식 HTTPS와 DSC의 SHA-256을 확인했으며,
DSC의 OpenPGP 서명을 독립적으로 검증한 것은 아닙니다.

tar의 [CVE-2026-18477](https://ubuntu.com/security/CVE-2026-18477)과
[CVE-2026-18508](https://ubuntu.com/security/CVE-2026-18508)은 해결을 확인하지 못했습니다.
cpio의 다른 CVE 역시 위 3개 검증 결과만으로 일괄 해결 처리하지 않습니다.

`tar`라는 이름만으로 GNU tar, npm node-tar, Rust tar-rs의 CVE를 합치면 안 됩니다.
각 CVE의 실제 제품과 배포판 피드의 매핑이 일치하는지 확인해야 합니다. 보고서 항목을
일괄 오탐 처리하거나 삭제하지 않습니다.

Trivy가 자체 Source RPM 이름·배포판 버전 규칙을 인식하지 못해서 결과가 사라지는
경우도 있습니다. 수정 근거, 실제 설치 버전, 실행 중 바이너리 및 서비스 검증을 함께
확인해야 합니다.
