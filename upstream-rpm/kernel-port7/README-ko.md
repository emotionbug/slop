# Linux 7.2.7 보안 모듈 포팅 실험 — 2026-09-26

목표는 RHEL 8 사용자 공간에서 Linux `7.2.7`을 사용하면서 Guardicore와
Trend Micro 보호 기능을 유지하는 것입니다. 현재 결과는 **호환성 작업 중간
산출물**이며 운영 설치 RPM이 아닙니다.

## 완료된 작업

- 서명 검증한 upstream Linux 7.2.7 소스를 GCC 15와 DWARF 모듈 버전 방식으로
  빌드했습니다. UBSAN과 무작위 kmalloc cache 기능을 실제로 활성화했습니다.
- 공식 Ubuntu 7.0용 Trend Micro 모듈이 요구하는 네 개의 누락 심볼 중 UBSAN 두
  개와 `random_kmalloc_seed`는 커널 기능 활성화로 제공했습니다. 삭제된
  `strncpy`의 기존 동작을 제공하는 자체 모듈을 작성했습니다. Ubuntu 7.0의
  실제 generic 구현 선언까지 맞춰 네 심볼의 요구 CRC가 모두 일치합니다.
- `strncpy`의 패딩·잘림·0 길이·페이지 경계 시험을 7.2.7 QEMU에서 통과했습니다.
- 디스크와 외부 네트워크가 없는 QEMU에서 ICMP, TCP/UDP, network namespace와
  NFQUEUE bridge 삭제 후 늦은 verdict 처리를 통과했습니다.
- 상용 모듈에는 강제 적재·vermagic 변경·CRC 덮어쓰기를 사용하지 않았습니다.
  불일치 모듈 세 개가 정상적으로 거부되는 것도 확인했습니다.
- 기존 CVE 교차검사에서 CNA의 명시적인 기본 `unaffected` 판정을 빠뜨린 문제를
  고쳤습니다. 62건을 `not_affected`로 분리했으며 수정 건수에 더하지 않습니다.

## 아직 해결되지 않은 호환성

| 모듈 | import | 일치 | CRC 불일치 | 누락 |
|---|---:|---:|---:|---:|
| Trend `dsa_filter` 7.0용 | 136 | 100 | 36 | 0 |
| Trend `dsa_filter_hook` 7.0용 | 43 | 27 | 16 | 0 |
| 서버 Guardicore 4.18용 | 161 | 0 | 134 | 27 |

Trend 모듈은 누락 심볼을 없앴어도 `module_layout` 등 CRC가 달라 적재되지
않습니다. 특히 모듈이 직접 읽는 `net_device.pcpu_refcnt` 위치는 공식 Ubuntu
7.0 빌드에서 1392 byte, 이 7.2.7 빌드에서 1496 byte입니다. 버전 검사만
우회하면 잘못된 메모리를 읽게 됩니다.

Guardicore 4.18 모듈은 더 큰 차이가 있습니다. 바이너리가 프로토콜 callback
120/128 byte 위치를 sendmsg/recvmsg로 취급하지만 7.2.7에서는
splice_eof/bind입니다. accept callback 인자도 바뀌었습니다. 바이너리만으로
안전하게 보완할 수 있는 shim 범위를 벗어납니다.

따라서 현재 상태에서는 세 상용 모듈이 동작하는 7.2.7 RPM을 만들었다고 표시하지
않습니다. Trend 공식 목록도 2026-09-25 기준 Ubuntu 26.04용 7.0 KSP까지만
제공합니다: https://files.trendmicro.com/documentation/guides/deep_security/Kernel%20Support/20.0/Deep_Security_20_0_kernels_EN.html

## CVE 상태

기존 Trivy kernel 행의 고유 CVE 4,195건을 고정된 Linux CNA snapshot으로 다시
분류한 결과는 다음과 같습니다.

- upstream 7.2.7 fixed 범위: 3,985
- CNA 기본 범위상 비해당: 62
- CNA record 없음: 125
- 버전 범위만으로 추가 검토 필요: 23

`fixed`와 `not_affected`는 분리합니다. 새 시험 빌드는 기존 Release 3 RPM과
해시가 다르므로 기존 Trivy 증거를 자동 승계하지 않습니다. 운영 RPM을 만들 때
정확한 SRPM/RPM 해시에 CNA 근거를 다시 결합해야 합니다.

위 23건에는 Linux CNA가 지목한 공식 수정 패치 97개를 다시 대조했습니다.
10건은 패치가 7.2.7 소스에서 정확히 역적용됐고, 12건은 stable 패치가 지목한
mainline 원본 수정 커밋이 `v7.2` 태그의 조상임을 확인했습니다.
`CVE-2026-68086`은 해당 stable 패치가 설명한 취약 코드 제거 커밋이 `v7.2`의
조상임을 확인해 비해당으로 분리했습니다. 따라서 소스 검토까지 합치면 4,007건은
수정 포함, 63건은 비해당이며 추가 검토 23건은 모두 해소됐습니다. Linux CNA
record 자체가 없는 125건은 이 근거만으로 해결됐다고 표시하지 않습니다.

추가로 CVE-2026-89632의 7.2.7 실제 `reparse_buf_ptr()` 소스에서 헤더 길이 검사
후 필드를 읽는 순서를 확인하고 경계 시험을 통과했습니다. 검사 순서를 제거한
대조군은 guard page fault가 발생해 시험 자체의 검출력도 확인했습니다.

## 재현 자료

- `legacy-string.c`, `legacy-string-selftest.c`: 자체 호환 구현과 커널 내 경계 시험
- `legacy-string-abi-probe.S`, `Makefile.abi-probe`: Ubuntu 7.0의 DWARF CRC를
  재현할 때 사용한 compile-only 선언 비교 자료
- `compare-imports.py`: 버전 심볼을 읽는 정적 비교기
- `export-cna-review-manifest.py`, `verify-cna-patches.py`,
  `verify-mainline-ancestry.py`: 고정 CNA 기록, 공식 패치 역적용과 mainline 계보 검사
- `CVE-SOURCE-REVIEW.json`: 23건의 공개 URL·패치 해시·판정 근거
- `lab-init.sh`: 디스크·외부 네트워크 없는 QEMU 시험 시나리오
- `test-smb-reparse.py`: 실제 7.2.7 SMB 함수 추출 및 경계/대조군 시험
- `VALIDATION.json`: 해시와 통과 범위

상용 모듈 원본, 디스어셈블리와 private initramfs는 저장소·릴리스에 포함하지
않습니다.
