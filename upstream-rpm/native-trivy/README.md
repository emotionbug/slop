# Trivy native RPM evidence module — integration PoC

RPM 제작 기록을 **한 번의 Trivy 스캔 → 한 JSON → 통합 CSV**로 연결하는 실증입니다.
Trivy 0.74.0의 WASM Analyzer/PostScanner API를 사용하며 Trivy 바이너리는 수정하지 않습니다.

[실행 번들 다운로드](https://github.com/emotionbug/slop/releases/tag/trivy-native-rpm-poc-20260924-1)

## 현재 구현한 범위

```text
배포 RPM / SRPM / manifest.json
             ↓ 빌드 시 SHA-256 확인 및 catalog.json 생성
설치 RPM의 NEVRA + Vendor + Source RPM + 헤더 SHA-256
             ↓ 검사 시 읽기 전용 수집 / 특정 CVE 관련 실행파일 SHA-256 대조
Trivy: 공식 RHEL 탐지기 + linuxoss-artifact-evidence WASM 모듈
             ↓
integrated.json → integrated.csv + summary.json
```

| 기능 | 현재 상태 |
|---|---|
| 자체 RPM과 배포 RPM·SRPM 연결 | 후보 52개 카탈로그 생성 및 실제 설치 상태 대조 통과 |
| Trivy JSON 내부 추가 결과 | `linuxoss-native` 결과에 패키지별 평가 삽입 |
| 특정 CVE 수정 근거 연결 | bzip2의 **CVE-2026-42250 한 건** |
| 실제 실행파일 대조 | `/usr/bin/bzip2recover` SHA-256 일치 필요 |
| 파일 변경 시 수정 판정 취소 | 격리 컨테이너 대조 시험에서 `under_investigation` 취약점 추가 |
| 기존 RHEL 취약점 결과 | 보존; 삭제·억제·심각도 변경 없음 |
| 나머지 CVE 자동 탐지 | 미구현. 모든 자체 패키지의 전체 CVE 범위는 `incomplete` |

패키지 52개 중 1개에 해당 CVE의 `fixed-evidence-matched`, 51개에 `unassessed`가 기록됩니다.
**bzip2의 모든 CVE를 해결했다는 뜻이 아닙니다.** RPM/실행파일에 대한 수정 근거 연결이며
실행 중 프로세스, 전체 payload, 커널 부팅이나 실제 운영 서버 검증은 아닙니다.
같은 버전이라도 다른 RPM 헤더이면 `artifact-mismatch`로 남깁니다.

PoC는 2026-09-24에 로컬 EL8 컨테이너, Trivy 0.74.0 및 2026-09-22 DB로 검사했습니다.
새 DB의 전체 취약점 현황을 확인한 작업은 아닙니다.

## 한 명령으로 실행

배포용 압축 파일에는 모듈, 카탈로그, 수집기, 보고서 변환기, 실행 스크립트와 SHA256SUMS가
포함됩니다. WASM은 약 3.6 MiB이며 압축 시 더 작아집니다. 별도 실행기 설치는 필요 없습니다.
**Trivy 실행파일과 취약점 DB는 기존 것을 재사용**합니다. Java DB는 필요 없습니다.

번들을 별도 폴더에 풀고 아래 경로를 실제 경로로 바꿔 실행합니다.

```bash
sudo bash scan-native.sh \
  --trivy /root/trivy/trivy \
  --cache-dir /root/trivy/trivy-proxy-work/cache \
  --output-dir /root/trivy/native-report-20260924
```

- RHEL 8 x86_64, root, platform-python, RPM, Trivy **0.74.0** 필요.
- 패키지 변경·재부팅 없이 읽기 전용 수집과 파일 출력만 수행합니다.
- `/run/linuxoss-trivy/`에 보호된 일회성 입력을 만들고 종료 시 제거합니다.
- 출력 폴더는 새 경로여야 합니다. 패키지 변경 작업이나 다른 native 스캔과 동시에 실행하지 마세요.
- DB 다운로드는 수행하지 않습니다. 프록시 갱신이나 DB 파일 반입은 기존 절차를 사용합니다.
- `--fail-on-gap`을 추가하면 자체 패키지의 전체 CVE 범위 미완료 시 CSV 저장 후 종료 코드 3.
  기본 종료 코드 0은 실행 성공만 뜻하며, `SCAN_COMPLETED_COVERAGE_INCOMPLETE`를 기록합니다.

결과:

- `integrated.json`: 기존 RHEL 취약점과 모듈 결과가 들어 있는 **원본 Trivy 출력**.
- `reports/integrated.csv`: 기존 취약점, 개별 수정 근거 일치, 미평가/불일치를 한 파일로 표시.
- `reports/summary.json`: 평가 개수와 전체 범위 미완료 여부.
- `installed-evidence.json`, `db-metadata.json`, `scan.log`: 로컬 검사 근거. 공개 업로드 금지.

일반 Trivy 취약점 CSV 템플릿은 `Vulnerabilities`만 순회하므로 수정 근거와 미평가 행이
빠집니다. 이 번들의 `report.py`를 사용해야 한 CSV에서 모두 볼 수 있습니다.
기존 `run-trivy-proxy.sh`는 변경하지 않았습니다. 위 스크립트가 모듈 경로를 명시적으로 설정합니다.

## 빌드에 연결

EL8에서 배포 번들을 검증해 카탈로그를 만듭니다.

```bash
python3 build-catalog.py /path/to/candidate-bundle --output catalog.json
```

`manifest.json`의 RPM/SRPM 해시와 실제 파일을 대조합니다. 현재 수동 검토를 마친 bzip2
RPM 해시에만 특정 CVE 평가가 들어가며, 새 RPM은 자동으로 수정 완료 처리되지 않습니다.
다른 패키지에는 기본적으로 `unassessed`를 부여합니다.

Go 1.26으로 테스트/컴파일합니다. 추가 Go 모듈 의존성은 없습니다.

```bash
go test ./...
GOOS=wasip1 GOARCH=wasm go build -trimpath -ldflags='-s -w' \
  -buildmode=c-shared -o modules/linuxoss-artifact-evidence.wasm .
```

Windows에서는 `GOOS`/`GOARCH`를 해당 프로세스의 환경 변수로 지정합니다.
카탈로그는 WASM 내부에 포함됩니다. 배포 카탈로그의 SHA-256이 내장 카탈로그와 다르면
중단하므로 모듈과 카탈로그를 함께 배포해야 합니다.
이 PoC의 모듈과 카탈로그는 미서명입니다. 신뢰할 수 있는 경로로 전달한 체크섬을 전제로
하며 운영 배포에는 서명된 릴리스/카탈로그를 연결할 수 있습니다.

## 전체 패키지로 확장할 때

확장 지점은 `build-catalog.py`의 수동 bzip2 평가 부분입니다. 다음 데이터를 생성하는
빌드 단계로 교체하면 수동 CSV 결합 없이 동일한 모듈 흐름을 유지할 수 있습니다.

1. Source RPM별 upstream 제품/CPE/PURL과 정적 포함 라이브러리 매핑.
2. 실제 제품을 지원하는 upstream/CNA/NVD/OSV 등의 CVE·영향 버전·조회 시각.
3. 해당 빌드의 추가 패치 커밋·소스 해시·회귀 결과를 연결한 개별 CVE 평가.
4. 미수정은 Trivy `Vulnerabilities`, 검토 완료 근거와 미확인은 모듈 평가로 출력.
5. 새 피드가 나오면 RPM을 다시 만들지 않고 평가 데이터와 모듈을 갱신해 재검사.

**연결 구조를 검증한 PoC**입니다. 같은 Trivy 결과에 합치는 기능은 구현됐지만,
323종 전체 제품 매핑·피드 운영·평가 규칙은 남아 있습니다. 현재 52개도 전체 CVE 탐지가
완성된 것은 아닙니다.

공식 근거:

- [Trivy WASM Analyzer/PostScanner](https://trivy.dev/docs/dev/advanced/modules/)
- [0.74.0 모듈 호스트 API](https://github.com/aquasecurity/trivy/blob/v0.74.0/pkg/module/module.go)
- [CVE-2026-42250 CNA 공지](https://cert.pl/en/posts/2026/05/CVE-2026-42250/)

Trivy 모듈 API는 실험 기능입니다. 버전 변경 시 입력 구조·ABI와 결과 보존 여부를 확인해야 합니다.
