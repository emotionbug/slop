# 비공개 보안 모듈과 EL8 최종 호환성

배포 대상은 `4.18.0-553.168.1.linuxoss2.el8_10.x86_64`입니다. 비공개 보안
모듈 3개는 공개 저장소와 공개 릴리스에 포함하지 않습니다. 선택된 원본 파일은
old-known-good 및 최종 커널에서 같은 328개 import가 전부 일치했고 missing과 CRC
mismatch가 각각 0개였습니다.

최종 커널의 격리 QEMU 검증은 세 모듈의 동시 로드, namespace 간 TCP/UDP 통신,
해제와 재로드를 통과했습니다. `--force-vermagic`, modversion 수정 또는 바이너리
패치는 사용하지 않았습니다. module format 오류, unknown symbol, 커널 fault와
warning도 검출되지 않았습니다.

## 서명 overlay

비공개 전달물은 다음 5개 regular file만 가진 gzip tar입니다.

- 서명된 `module-profile.json`
- `module-profile.json.sig`
- 프로필에 지정된 모듈 payload 3개

프로필에는 실행 원본 커널, 최종 대상 커널, 최종 `Module.symvers` 해시, 파일 해시,
vermagic, identity, import/export 집합이 고정됩니다. 공개 번들의
`module-profile-signing-public.pem`과 `install-private-module-overlay.py`가 서명,
파일 수, 안전한 경로 및 payload 해시를 검사합니다. 변조된 서명과 payload는 설치
전에 거부됩니다.

`stage-reviewed-modules.py`는 다음 조건을 모두 확인한 뒤 대상 커널의 별도 디렉터리에
동일 파일만 복사합니다.

- 현재 커널과 프로필의 source release 일치
- 최종 kernel/devel RPM 및 커널 이미지 해시 일치
- 최종 `Module.symvers` 해시와 target release pin 일치
- 로드된 모듈 identity와 선택 파일의 identity/vermagic 일치
- kernel 및 peer export를 포함한 import 328개 전부 일치
- 기존 파일 충돌, symlink 및 대상 경로 이탈 없음

스크립트는 임의의 대체 파일을 고르거나 모듈을 로드·해제하지 않습니다.

## 검증 범위

- 전체 커널 빌드: PASS, 모듈 2,804개
- 최종 서버 프로필: 요청 67개, 보존 69개, 누락 0개
- 정적 외부 모듈 ABI: 3개/328 imports, 328 matched, 0 missing, 0 mismatch
- QEMU: 4/4 marker, 동시 로드·network·해제·재로드 PASS
- 실제 EL8 RPM 설치 및 외부 모듈 smoke: PASS
- 서명/변조/CRC/release/symvers/missing-peer 음성 시험: 모두 예상대로 거부
- SSH dispatcher 정상 commit과 SSH/network fail-closed: PASS, reboot 호출 0개

실제 VMware 부팅, 전체 사용자 공간 에이전트 정책, 관리 서버 연결, Java daemon과
Tomcat 업무 기능은 대상 서버에서 최종 확인해야 합니다.
