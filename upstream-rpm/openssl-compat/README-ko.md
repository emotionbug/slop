# 시스템 OpenSSL 1.1.1 보안 백포트 — 2026-09-26

`1:1.1.1k-17.el8_10.linuxoss.1`은 기존 `libssl.so.1.1` / `libcrypto.so.1.1`
ABI와 EL8 패치를 유지한 자체 빌드입니다. 별도 설치된 OpenSSL 4.0.2와는 다른
패키지이며, 시스템의 기존 `openssl`, `openssl-libs`, `openssl-devel` 등을
같은 이름으로 업그레이드합니다.

## 수정 근거

- 공식 서명을 확인한 Rocky `openssl-1.1.1k-17.el8_10.src.rpm`을 기반으로 합니다.
- [OpenSSL 1.1.1 보안 공지](https://www.openssl-library.org/news/vulnerabilities-1.1.1/)의
  공개 수정과 [Debian bullseye 보안 패치](https://salsa.debian.org/debian/openssl/-/tree/48082ef2c8649dc61f88371e2e299962a6c4c7f2/debian/patches)를 적용했습니다.
- CVE-2026-54874는 공지의 3.0 링크가 CMS 수정 해시를 중복 가리키고 있어,
  실제 [DTLS 수정 1ca5a124](https://github.com/openssl/openssl/commit/1ca5a124b48f1ffe6980ad33724b452fbd62da1e)를
  확인해 이식했습니다. 작은 DTLS 레코드마다 전체 수신 버퍼를 보관하던 부분을
  레코드 크기만큼 복사하도록 바꾸고 포인터 재배치·해제 경로를 함께 반영했습니다.
- CVE-2026-63072는 [a0c8ec55](https://github.com/openssl/openssl/commit/a0c8ec557d9cac078f032d76cdf684fe743eb382)의
  CMS unwrap 출력 버퍼 수정입니다.
- CVE-2026-42768은 upstream 공지의 버전 범위만으로 비해당 처리하지 않았습니다.
  EL8에는 RSA implicit rejection과 이를 끄는 CMS/PKCS7 코드가 백포트되어 있었습니다.
  [dd683641](https://github.com/openssl/openssl/commit/dd68364107a58841c0a2546812518b65d3a23abd)에
  맞춰 해당 비활성화 코드를 제거했습니다.

기존 CSV의 OpenSSL 31개 CVE 중 23건에 upstream 수정 또는 문서 수정이 반영되며,
7건은 해당 소스·아키텍처에 없는 코드에 대한 별도 판정 대상입니다.
**CVE-2024-41996은 수정 완료로 처리하지 않습니다.** 이 숫자는 서버 적용 결과가 아닙니다.
CVE-2023-0466의 upstream 수정은 문서 정정이며, 인증서 정책 검사를 원하는
애플리케이션은 여전히 올바른 플래그/API를 사용해야 합니다.

## 확인한 결과

- 전체 upstream 테스트: **160개 recipe / 1,482개 test, PASS**.
  비활성화된 암호·외부 테스트 등 원래 구성에 따른 skip은 유지했습니다.
- 악성 PKCS12/CMS/CRL 입력에 대한 Debian 공식 fixture와 테스트를 포함했습니다.
- EL8 컨테이너에서 실제 DNF 업그레이드, `rpm -V`, `dnf check` 통과.
- 기존 두 라이브러리의 공개 동적 심볼 삭제·타입 변경 없음.
- TLS 1.2 및 TLS 1.3 인증서 검증, platform-python TLS, curl HTTPS,
  EL8 OpenSSH 8.0p1의 실제 loopback 공개키 세션 통과.

이는 격리된 로컬 시험이며 대상 서버의 Java/Tomcat, 에이전트 전체 기능과
운영 SSH 설정을 검증한 것은 아닙니다.

## 필요한 사용 방식 변경

RSA CMS/PKCS7 메시지에 수신자가 여럿일 때 키만으로 올바른 수신자를 추측하는
동작은 보안 수정 후 보장하지 않습니다. upstream과 같이 수신자 인증서를
명시하세요. 복호화 성공 여부를 수신자 식별 수단으로 사용하지 않습니다.

```bash
openssl cms -decrypt -inform DER -in message.der \
  -recip recipient.crt -inkey recipient.key -out message.txt
```

이 변경에 맞춰 upstream의 인증서+키 테스트 방식을 사용했습니다. 실패한
기존 테스트를 숨기거나 implicit rejection을 다시 끄지 않았습니다.

## 배포와 한계

SRPM에는 원본 소스와 모든 EL8·추가 패치, 공식 악성 입력 테스트 파일이 포함됩니다.
재빌드 시 전체 테스트가 실행됩니다. 자체 빌드의 공급자는 LinuxOSS이며 Red Hat
서명·지원·FIPS 인증을 주장하지 않습니다. `openssl version`에 남은 EL8의 `FIPS`
문자열도 검증 인증을 뜻하지 않습니다. FIPS 운영 시스템의 교체 대상으로 배포하지 않습니다.

설치 뒤 기존 프로세스는 이전 라이브러리를 계속 사용하므로 서비스 재시작과
실제 서버 재검사가 필요합니다. 실행 중 메모리를 Trivy의 파일 해시 검증으로
검증했다고 간주하지 않습니다.
