# 2026-09-24 v3 로컬 통합 검증

- 최종 배포 카탈로그: 자체 RPM 341개, Source project 식별자 161개. 공식 UBI RPM 1개는 자체 판정에서 제외.
- NVD 제품 매핑 97개, CPE 조회 140개, 프로젝트별 CVE 기록 23,126개. 전체 NVD 복제나 완전한 CVE 범위는 아님.
- UBI 8.10 참조 환경의 검증 묶음 77 RPM에 별도 MCPP 평가본을 설치해 자체 RPM 77개를 검사.
- 최종 배포 `scan-native.sh`를 네트워크 차단 상태, Trivy 0.74.0과 2026-09-22 DB로 실행.
- 자체 RPM 77개 모두 평가 결과에 포함. 수정 근거 일치 23행, 검토 필요 CVE 431행,
  범위 부족 77행, 비설정 일반 파일을 대조할 수 없는 패키지 1행.
- 공식 Trivy 취약점 569행과 자체 후보 431행이 `actionable.csv` 1,000행에 포함됨.
- JSON, actionable.csv, integrated.csv, summary.json 생성 완료. 실제 운영 서버의 잔여 취약점 수가 아님.
- Go 경계 조건/제품 식별/해시/피드 검사와 Python feed 테스트 통과.
- 커널 피드 확장으로 드러난 반복 SHA-256 계산을 평가당 한 번으로 줄였으며 결과 의미는 유지.
- v2에서 검증한 bzip2recover 변조 시 수정 근거 취소 동작은 유지. v3에서 같은 변조 검사를 반복하지 않음.
- 별도 SSSD Release 3 평가본: 격리 EL8 builder에 DNF 설치, 버전, ELF loader, dnf check 통과.
  원래 전체 upstream 검사 실패를 통과로 바꾸지 않았으며 PAM/AD/LDAP 또는 운영 인증을 검증하지 않음.
- fwupd 라이브러리 테스트 15/15, MCPP 공식 재현 입력 2개의 Valgrind 검사 통과.
- 최종 RPM 압축 파일은 모든 내부 파일의 SHA-256 및 누락/중복 여부를 검사.
- 실제 서버 설치·부팅·VMware·보안 에이전트·Java/Tomcat 검사는 미실시.

전체 342개 바이너리를 한 시스템에 설치한 검증이 아닙니다. 개별 범위는
[전체 결과](../ALL-BUILDS.md)와 [카탈로그](../BUILD-CATALOG.json)에 기록합니다.
