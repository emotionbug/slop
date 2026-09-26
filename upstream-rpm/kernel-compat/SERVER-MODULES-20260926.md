# 실제 보안 모듈 분석과 EL8 호환 시험

서버에서 추출한 모듈을 변경하지 않고 EL8 `.168` 호환 커널에서 시험했습니다.
Guardicore와 Trend 세 모듈의 동시 로드, namespace 간 ICMP/TCP/UDP 통신,
namespace 제거 및 세 모듈 해제가 통과했습니다. 강제 로드, vermagic/CRC 수정은
사용하지 않았습니다. **에이전트 사용자 공간 프로그램과 운영 보호 정책은 미검증**입니다.

## 확인한 모듈 선택 문제

Guardicore는 `extra`와 `weak-updates`에 서로 다른 바이너리가 있습니다.
이전 서버 검사에서 로드된 srcversion은 `1E3CF09EA0054B840FB024B`이고,
`modinfo gc_enforcement`가 따라간 weak-updates 파일은
`5FB131940DB04FFB88BDF3B`였습니다. 따라서 modinfo 경로만 복사하면 현재
실행 중인 모듈과 다른 파일을 선택할 수 있습니다.

시험한 파일은 Guardicore `extra`의 정확한 바이너리, Trend filter
`12.6.0.8491 (HUA)`, 해당 hook입니다. SHA-256은
[검증 결과](SERVER-MODULE-VALIDATION.json)와 준비 스크립트에 고정했습니다.
수집기도 `/sys/module`의 실제 로드된 version/srcversion을 별도로 기록합니다.

## 7.2.7에서 필요한 변경

정확한 7.2.7 Release 3 Module.symvers와 비교했습니다.

| 모듈 | 커널 import 수 | 일치 | CRC 변경 | 커널 export 없음 |
|---|---:|---:|---:|---:|
| Guardicore | 161 | 38 | 96 | 27 |
| Trend filter | 120 | 30 | 67 | 23 |
| Trend hook | 39 | 11 | 21 | 7 |

Trend filter의 별도 8개 peer import는 hook의 export와 CRC가 일치합니다.
이 8개를 커널에서 빠진 API로 계산하지 않았습니다.

또한 Guardicore는 `tcp_prot`/`udp_prot`의 callback을 고정 offset에 직접
덮어씁니다. 실제 바이너리의 sendmsg 슬롯은 120, recvmsg 슬롯은 128 byte입니다.
7.2.7 SDK로 만든 layout probe에서 그 위치는 각각 `splice_eof`, `bind`이고,
7.2.7의 sendmsg/recvmsg는 104/112 byte입니다. `accept` callback도 EL8의
4개 인자에서 7.2.7의 `proto_accept_arg *` 방식으로 바뀝니다.

따라서 버전·CRC 변경만으로 정상화할 수 없습니다. wrapper를 만들어 누락된
함수 이름을 채우더라도 직접 구조체 접근과 callback 인자 해석은 별도로
포팅해야 합니다. 이 결과는 7.2.7 호환 패치를 완성했다는 의미가 아닙니다.
[Linux 커널의 binary API 설명](https://kernel.org/doc/html/next/process/stable-api-nonsense.html)

layout probe는 정확한 배포 SDK와 autoconf를 사용한 GCC 15의 **컴파일 전용**
객체입니다. Ubuntu에 EL8 objtool의 libopcodes가 없어 해당 객체의 objtool 후처리만
생략했습니다. 로드용 모듈이나 커널을 이 방식으로 빌드·검증하지 않았습니다.

## 검증된 EL8 커널에 모듈 파일 준비

먼저 [기존 커널 파일 설치](../deploy/BACKPORTS-20260926.md)의
`download-kernel-compat.sh apply`로 `.168` 커널과 devel RPM을 추가합니다.
그 다음 아래를 실행합니다.

```bash
wget -e use_proxy=yes -e https_proxy=http://192.168.32.104:9080 \
  -O stage-reviewed-modules.py \
  https://raw.githubusercontent.com/emotionbug/slop/main/upstream-rpm/kernel-compat/stage-reviewed-modules.py
sudo /usr/libexec/platform-python stage-reviewed-modules.py apply
```

`check`를 사용하면 파일 복사 없이 조건과 예정 작업만 확인합니다.
검사 내용은 현재 커널 `.166`, 실제 로드된 세 모듈의 식별자, 원본 모듈의
정확한 SHA-256, 대상 커널 이미지/Module.symvers 해시와 RPM 검증입니다.
다르면 중단하며 자동으로 다른 모듈을 선택하지 않습니다.

스크립트는 서버에 있는 모듈을 새 커널의 `extra/linuxoss-reviewed`에 복사하고
depmod가 해당 파일을 선택하는지 확인합니다. 다른 내용의 기존 파일을 덮어쓰지
않고, 같은 파일에 대한 재실행은 허용합니다. 모듈 로드/해제, initramfs 생성,
GRUB 변경 및 재부팅은 하지 않습니다. **아직 이 단계만으로 새 커널로 부팅할
준비가 완료되거나 실행 커널의 CVE가 해결된 것은 아닙니다.**

공개 GitHub에는 검사 도구·자체 시험 코드·요약 근거만 올립니다. 수집한 상용
모듈과 디스어셈블리, 운영 설정은 공개 배포하지 않습니다.

## 검증 범위

- QEMU: 세 실제 바이너리 동시 로드, ICMP 3/3, TCP/UDP echo, namespace 정리,
  모듈 해제 통과. Oops/BUG/WARNING 없음. Secure Boot 강제 검증은 하지 않았습니다.
- 최초 두 네트워크 시도는 BusyBox shell이 내부 ip applet을 선택해 실패했습니다.
  `/usr/sbin/ip`를 명시한 최종 시험에서 모두 통과했고 초기 로그도 보존했습니다.
- 준비 스크립트: 변조 원본·기존 파일 충돌·symlink·로드된 식별자 불일치 차단 테스트 통과.
- 별도 EL8 컨테이너: 실제 RPM 검증·파일 복사·depmod·modinfo 경로 검증·재실행 통과.
  이 컨테이너 시험의 실행 커널 식별자와 GRUB 조회는 fixture로 대체했으므로
  실제 서버의 실행 상태/부팅 설정 검증을 대신하지 않습니다.
- 관리 서버 연결, 정책 allow/deny 집행, 실제 Java/Tomcat 및 VMware 부팅은 미검증입니다.
