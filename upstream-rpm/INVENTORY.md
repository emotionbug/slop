# 전체 RPM 교체 분석용 서버 정보 수집

`collect-inventory.sh`는 서버의 RPM 메타데이터를 읽어 로컬 압축 파일을 만듭니다.
패키지 설치/삭제, 저장소 변경, 서비스 재시작, 네트워크 연결을 하지 않습니다.

```bash
sudo bash collect-inventory.sh /var/tmp
```

출력되는 `rpm-inventory-날짜-임의값.tar.gz` 파일을 분석 개발기로 복사합니다.
민감할 수 있는 서버 패키지/드라이버 정보이므로 공개 저장소에 올리지 않습니다.

수집 항목:

- 전체 설치 RPM 이름, Epoch/Version/Release, 아키텍처, Source RPM, 모듈 정보
- RPM Requires/Provides/Conflicts/Obsoletes 관계
- 실행 중인 커널, OS 정보, `/boot/config-*`
- 동적 라이브러리 캐시 목록, 서비스 활성화 상태, PCI 드라이버와 로드된 모듈
- 확인 가능한 경우 Secure Boot 및 BIOS/UEFI 여부

애플리케이션 소스/JAR/WAR, 설정 파일 본문, 환경변수, 비밀번호, 인증서/키는
수집하지 않습니다. 라이브러리 실제 사용 여부나 Java/Tomcat 동작을 증명하는
자료는 아니며, 최종 검증에는 별도의 RHEL 8 VM 및 실제 애플리케이션 테스트가 필요합니다.

검증: 로컬 UBI 8.10 컨테이너에서 실제 실행 및 압축 파일 생성 확인.
실제 대상 서버에서의 실행은 아직 확인하지 않았습니다.
