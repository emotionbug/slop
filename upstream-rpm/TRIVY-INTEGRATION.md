# 자체 RPM과 Trivy 연계 확인

2026-09-24에 **Trivy 0.74.0으로 실제 설치 상태를 검사**했습니다.
패키지 식별과 SBOM 생성은 가능하지만, 현재 자체 RPM의 취약점 판정은 기본 RHEL
검사에서 제외됩니다. CVE가 사라졌다는 이유로 자체 RPM 교체를 조치 완료로 계산하면 안 됩니다.

## 실제 확인 결과

- 환경: UBI/RHEL 8.10 x86_64 컨테이너. 실제 운영 서버를 검사한 결과가 아닙니다.
- 설치물: `upstream-rpm-candidates-20260924-6`의 51종과 자체 의존성 `libgpg-error`
  1종, 공식 `cmake-filesystem` 1종. 자체 RPM 합계는 **52개**입니다.
- 전체 컨테이너 RPM 식별: 340개, 그중 GPG 공개키 레코드 2개.
- DB: 2026-09-22 19:06:27 UTC 스냅샷. 모든 검사는 네트워크를 차단하고 같은 DB로 수행했습니다.
  현재 최신 CVE 현황이 아니라 검사 동작을 비교한 결과입니다.
- 기본 명령: `trivy rootfs / --pkg-types os --scanners vuln --list-all-pkgs`
  및 오프라인·DB 갱신 금지 옵션. 기본 검사와 comprehensive 검사 모두 성공했습니다.

| 경로 | 자체 RPM 52개 식별 | 자체 RPM의 취약점 결과 | 판단 |
|---|---|---|---|
| 기존 `rootfs`, `--pkg-types os` | 모두 식별 | 0행, 모두 검사 제외 | 추가 검사 필요 |
| 위 명령에 `--detection-priority comprehensive` 추가 | 모두 식별 | 0행, 모두 검사 제외 | 옵션으로 해결되지 않음 |
| 원본 JSON을 CycloneDX로 변환 | 모두 SBOM에 존재 | 새 취약점 검사를 하는 단계가 아님 | 목록/산출물 추적에 사용 가능 |
| 생성한 CycloneDX를 `trivy sbom`으로 재검사 | 모두 식별 | Red Hat 피드의 결과 215행 | 자체 RPM용 판정으로 사용할 수 없음 |

원본 rootfs JSON은 각 자체 RPM에 다음 정보를 보존합니다.

```json
{
  "Name": "bzip2",
  "Version": "1.0.8",
  "Release": "1.linuxoss.el8",
  "Maintainer": "Linux OSS local build",
  "Repository": {"Class": "third-party"}
}
```

디버그 로그는 52개 이름을 나열하며 `Skipping third-party packages`를 출력합니다.
공식 패키지 286개만 RHEL 취약점 탐지기에 전달되었습니다.
반면 이 버전의 CycloneDX 재검사 JSON에는 RPM의 `Maintainer`와 `Repository.Class`가
복원되지 않았고, 공개키를 제외한 338개가 RHEL 탐지기로 전달됐습니다.
215행은 패키지별 CVE 결과 행 수이며, 서로 다른 CVE 215개라는 뜻은 아닙니다.
이 재검사는 자체 upstream 버전·패치에 맞는 피드를 추가한 것이 아닙니다.
SBOM의 PURL에 `redhat`이 있다고 Red Hat 공식 RPM이 되는 것도 아닙니다.

이 동작은 [공식 third-party 설명](https://trivy.dev/docs/v0.74/guide/scanner/vulnerability/#third-party-packages),
[0.74.0 RPM Vendor 분류 코드](https://github.com/aquasecurity/trivy/blob/v0.74.0/pkg/fanal/analyzer/pkg/rpm/rpm.go),
[탐지기 필터 코드](https://github.com/aquasecurity/trivy/blob/v0.74.0/pkg/detector/ospkg/detect.go)와
대조했습니다. 향후 Trivy 버전에서는 다시 확인해야 합니다.

## 지금 사용할 수 있는 검사 누락 보고서

`trivy-rpm-coverage.py`는 기존 스캔의 **원본 `os-rpms.json`**을 읽어 공급자·버전·PURL과
검사 제외 대상을 CSV로 표시합니다. Python 3.6 이상 표준 라이브러리만 사용하며,
재검사·네트워크 접속·RPM 변경 없이 동작합니다. 취약점 탐지기나 수정 판정기는 아닙니다.

RHEL에서 스크립트가 있는 폴더 기준으로 실행합니다. `REPORT_DIR`만 실제 결과 폴더로 바꾸세요.

```bash
REPORT_DIR=/실제/스캔/결과폴더
/usr/libexec/platform-python trivy-rpm-coverage.py \
  "$REPORT_DIR/os-rpms.json" --output-dir "$REPORT_DIR/rpm-coverage"
```

개발기에서도 `python trivy-rpm-coverage.py 경로/os-rpms.json --output-dir 새폴더`로 동일하게 실행합니다.
출력 폴더는 기존 결과를 덮어쓰지 않도록 새 경로여야 합니다.

- `rpm-coverage.csv`: 입력에 있는 RHEL RPM 전체와 검사 범위 상태.
- `rpm-coverage-gaps.csv`: third-party 제외, 공급자 정보 누락, SBOM 재검사 등 확인 필요 항목.
- `coverage-summary.json`: 개수, 원본 JSON SHA-256, 검사 시각, 한계.

현재 컨테이너 원본 결과에서 **52개 전부 누락 목록으로 출력**됐습니다.
실제 서버의 스캔이 아니므로 서버 설치 상태는 서버에서 생성한 JSON으로 확인해야 합니다.
`vendor-feed-eligible`은 공식 피드에 전달될 수 있다는 뜻이며 완전한 탐지나 안전 판정이 아닙니다.
`--fail-on-gap`을 추가하면 결과를 저장한 뒤 누락이 있을 때 종료 코드 3을 반환합니다.
입력 오류는 2, 보고서 생성 성공은 0입니다. 코드 0도 취약점 해결을 뜻하지 않습니다.
패키지 목록이 없는 JSON은 오류로 처리합니다. 입력 목록 자체의 완전성이나 DB 최신성은
이 도구가 검증하지 않으므로 기존 스캔 로그와 RPM 인벤토리도 보관해야 합니다.

## 자체 RPM까지 연결하는 방법

권장 방식은 **공식 RPM용 Trivy 검사 + 자체 RPM용 upstream 검사 + CVE별 수정 근거**를
하나의 보고 과정에 넣는 것입니다.

1. 기존 Trivy JSON과 취약점 CSV를 그대로 보관합니다. 자체 RPM은 위 누락 CSV로 추적합니다.
2. 자체 RPM마다 실제 upstream 프로젝트, upstream 버전, 소스·패치 SHA-256,
   생성 RPM SHA-256 및 설치된 NEVRA를 연결합니다. 정적 포함 라이브러리도 포함해야 합니다.
   예를 들어 rsync RPM에는 `xxHash 0.8.4`가 정적으로 포함돼 있습니다.
3. upstream 제품 식별자에 맞는 CVE 피드로 추가 검사합니다. 하나의 방법은
   [CVE Binary Tool의 vendor/product/version 입력](https://github.com/ossf/cve-bin-tool/blob/main/doc/MANUAL.md)입니다.
   RPM 패키지명과 NVD 제품명은 다를 수 있으므로 52개 이름을 그대로 넣으면 안 됩니다.
4. 추가 검사 결과를 [SECURITY-EVIDENCE.md](SECURITY-EVIDENCE.md)의 개별 패치·회귀 검사와
   대조합니다. 확인된 CVE만 해당 RPM 아티팩트에 대해 수정 확인으로 기록합니다.
   근거가 없거나 제품 매핑이 불명확한 항목은 미확인 상태로 남깁니다.
5. 최종 보고서에는 원래 탐지 결과, 검사 제외, upstream 추가 검사 결과,
   근거가 확인된 수정, 미확인을 구분합니다. 미검사 항목이 남으면 전체 해결로 표시하지 않습니다.

추가 도구의 **문서상 사용 예시**입니다. 현재 작업에서 CVE Binary Tool 설치·DB 구축·전체
제품 매핑·실제 추가 검사는 수행하지 않았습니다. 다음 예시는 zlib만 포함하며 전체 목록이 아닙니다.
두 제품 별칭은 [CVE Binary Tool의 zlib 체크 코드](https://github.com/ossf/cve-bin-tool/blob/main/cve_bin_tool/checkers/zlib.py)에 있습니다.

```csv
vendor,product,version
gnu,zlib,1.3.2
zlib,zlib,1.3.2
```

위 내용을 `custom-upstream.csv`로 저장하고, 도구와 DB가 준비된 환경에서:

```bash
cve-bin-tool --offline --input-file custom-upstream.csv \
  --format csv --output-file custom-upstream-cves.csv
```

오프라인 실행은 외부에서 다운로드한 해당 도구의 DB가 필요합니다. Trivy DB와 호환되는
DB가 아닙니다. 개발기에서 보유한 자체 소스·RPM을 검사할 수도 있어 Java 애플리케이션
JAR/WAR 반출은 이 절차에 필요하지 않습니다. 최종 설치 버전과의 일치는 별도로 확인합니다.
NVD 제품/버전 검사만으로 추가 backport 패치까지 인식하지 못하므로 CVE별 근거 대조가 필요합니다.

Trivy 결과 안으로 직접 넣으려면 [WASM PostScanner 모듈](https://trivy.dev/docs/dev/advanced/modules/)
또는 자체 탐지기/피드 구현이 가능합니다. 이 경우에도 정확한 제품 매핑, 영향 버전,
추가 패치 반영 여부와 피드 갱신을 직접 유지해야 합니다. 전체 자체 취약점 DB가 구현된
상태는 아닙니다.

후속 작업으로 [native WASM 연계 모듈](native-trivy/README.md)을 구현했습니다.
52개 배포 RPM/SRPM과 설치 파일을 대조하고, 38개 소스 프로젝트의 선택한 NVD CPE 피드,
22개 CVE의 검토된 수정 근거를 같은 Trivy JSON과 CSV에 연결합니다.
기존 RHEL 결과를 보존하며 미등록 제품·범위 부족도 표시합니다. 전체 upstream CVE 범위를 보장하지 않습니다.

[OpenVEX](https://trivy.dev/docs/dev/supply-chain/vex/file/)는 이미 탐지된 CVE에 대해
제품/PURL별 평가를 적용하는 연계 수단입니다. 누락된 RPM을 새로 검사하는 기능이 아닙니다.
따라서 VEX만 추가하거나 Vendor를 Red Hat으로 바꾸는 것으로 문제를 해결할 수 없습니다.
소스 스캔이나 C/C++ 옵션도 일반 자체 RPM 전체를 자동 지원하지 않습니다.
[Trivy C/C++ 범위](https://trivy.dev/docs/dev/guide/coverage/language/c/)는 Conan 등의
지원되는 패키지 메타데이터를 기준으로 합니다.

## 이번 변경의 검증 범위

- 같은 오프라인 DB로 rootfs 기본·comprehensive·CycloneDX 재검사 세 경로 비교.
- 보고 도구: 자체 RPM 누락, SBOM 공급자 손실, 빈 인벤토리 오류, 다중 아키텍처
  결과 분리 및 입력 불변성에 대한 4개 검사 통과.
- 실제 원본 JSON으로 340행/누락 52행, SBOM 재검사 JSON으로 공개키 외 338행 확인 필요 분류.
- RHEL 8 platform-python으로 실행 확인. 실제 서버 실행이나 추가 upstream 탐지기 검증은 아님.

서버의 원본 JSON/CSV/SBOM/인벤토리와 이 도구의 출력은 공개 저장소에 올리지 않습니다.
