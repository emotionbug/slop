# 커널 Release 3 검증 범위

배포 대상은 `7.2.7-linuxoss+`, RPM Release `3.el8`의 `kernel`과
`kernel-devel`입니다. 정확한 산출물·소스 해시와 검증 로그 해시는
`VALIDATION.json`에 기록합니다.

## 설치와 부팅

실제 서버 파일을 사용하지 않은 EL8 참조 VM에서 다음 세 단계를 실행했습니다.

1. 기존 4.18 커널로 부팅하여 점검 모드의 RPM 목록 불변을 확인하고, 새 RPM 2개를
   추가 설치했습니다. 두 DNF 트랜잭션 모두 제거 대상이 없었습니다.
2. 새 7.2.7 커널로 UEFI 부팅했습니다. PVSCSI 디스크의 LVM/XFS 루트,
   VMXNET3 네트워크, 호스트에서의 SSH 접속과 Java 8 HTTP 응답,
   firewalld/nftables 및 DNF 의존성 검사를 확인했습니다.
   Java 서비스의 cgroup v1 메모리 제한값은 실제로 268435456바이트였습니다.
3. 새 커널을 기본값으로 확정한 뒤 기존 기본값으로 되돌리고, 기존 4.18 커널로
   다시 부팅했습니다. 새 RPM은 설치된 상태로 남았습니다.

QEMU TCG와 OVMF를 사용했습니다. OVMF에는 VMware PVSCSI 부팅 펌웨어가 없어
EFI와 `/boot`만 virtio 디스크에 두었고, 루트 파일시스템은 PVSCSI로 시험했습니다.
Secure Boot는 비활성 상태였습니다. 실제 VMware 펌웨어와 동일한 시험은 아닙니다.

SELinux는 Enforcing 상태에서 시험했습니다. 다만 EL8의 기존 정책에 없는 새 커널의
클래스·권한을 허용한다는 경고도 확인했습니다. Enforcing이라는 상태만으로 최신
커널 기능까지 기존 정책과 같은 범위로 통제된다고 보장할 수는 없습니다.

## 빌드와 Trivy

- GCC 8.5, binutils 2.47, dwarves 1.32로 빌드했습니다. BTF와
  `CONFIG_MEMCG_V1=y`를 유지했습니다.
- EL8에서 함께 제공한 kernel-devel로 외부 모듈 컴파일과 vermagic을 확인했습니다.
  그 모듈의 실제 적재 시험은 하지 않았습니다. 빌드 컨테이너에 대응 vmlinux가 없어
  외부 모듈의 BTF 생성은 생략됐습니다. 배포 커널 자체의 BTF는 유지됩니다.
- 소스·바이너리 RPM에 커널 서명용 비밀키가 포함되지 않았음을 확인했습니다.
- Trivy 0.74.0 오프라인 실행과 자체 모듈의 Go/Python 회귀 검사를 통과했습니다.
  RPM의 `7.2.7_linuxoss+`를 upstream `7.2.7`로 연결하고 두 RPM의 정확한 해시를
  확인했습니다. 미확인 커널 피드 범위는 `coverage-gap`으로 유지합니다.

## 실제 서버에 남은 확인

실제 Java daemon·Tomcat·보안 에이전트 및 부하 시험은 수행하지 않았습니다.
Red Hat 서명·지원·kABI 호환성을 제공하는 커널도 아닙니다.
설치기는 기존 커널을 보존하고 자동 재부팅하지 않습니다. 실제 서버의 1회 부팅과
서비스 확인 후 `confirm`해야 합니다. 기존 커널의 취약점과 미확인 CVE를
모두 해결된 것으로 표시하지 않습니다.
