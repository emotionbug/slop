# 자체 RPM 제작과 Trivy 통합 검사

배포 RPM/SRPM → 설치 파일 대조 → upstream CVE 평가 → **한 번의 Trivy 검사와 CSV**로 연결합니다.
Trivy 0.74.0의 WASM 모듈을 사용하며 공식 RHEL 결과는 보존합니다.

[실행 번들](https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-6)

## 연결 범위

- 확장 평가 묶음의 자체 RPM 전체의 RPM/SRPM/헤더/비설정 일반 파일 SHA-256을 대조합니다.
- Source RPM별로 출처가 있는 NVD CPE 식별자를 선택합니다. GNU tar와 npm/Rust tar를 합치지 않습니다.
- NVD 응답 해시, 조회 시각, 페이지 수, 실패를 보존합니다. 선택한 영향 버전 범위 후보는 실제 Trivy `Vulnerabilities`의 `under_investigation`으로 들어갑니다.
- `reviewed-evidence.json`의 명시적 CVE 수정 근거를 정확히 일치하는 RPM과 파일에만 적용합니다. 20260925-5의 Wget/patch/tar/jq 근거를 유지하고, 20260925-6에서 ABI를 유지한 보안 백포트와 split RPM의 구성요소별 비해당 근거를 추가했습니다.
- 공식 결과의 동일 CVE도 이름·epoch·버전·release·아키텍처가 하나로 일치하고 파일 해시 검증을 통과한 경우에만 근거 판정으로 연결합니다. 원래 상태·참조·설명을 별도 열에 남깁니다.
- rsync에 포함된 xxHash 0.8.4도 표시합니다. 검증한 CPE 매핑이 없어 `unmapped`입니다.
- 제외한 과거 CVE는 JSON 평가의 `range_excluded_cves`에 남습니다.
- OpenSSL 공식 문자 버전을 해석합니다. 다른 해석 불가능한 버전 접미사, 환경 조건, 배포판 별칭은 검토 대상으로 유지합니다.
- `vulnerable:false` 환경 CPE와 정확히 확인한 설정/디렉터리 전용 RPM은 코드 CVE와 분리합니다.
- 미등록 RPM, 파일 변경, 조회 실패, 30일 초과 피드, 비정상 미래 조회 시각을 표시합니다.

**전체 CVE 탐지 완료를 보장하지 않습니다.** NVD 매핑·분석 지연이 있어 모든 자체 RPM에
범위 미완료 행을 남깁니다. 수정 판정은 명시된 CVE에만 적용합니다. 파일 검사는 설정·심볼릭 링크·권한·
실행 중 메모리를 포함하지 않으며 실제 서버의 Java 실행·커널 부팅 확인을 대신하지 않습니다.

## 오프라인 실행

별도 폴더에 압축을 풀고 실제 경로로 바꿔 실행합니다. 기존 Trivy 바이너리와 DB를 재사용합니다.
Java DB와 외부 통신은 필요 없습니다. RHEL 8 x86_64, root, platform-python, Trivy **0.74.0**이 필요합니다.

```bash
sudo bash scan-native.sh \
  --trivy /root/trivy/trivy \
  --cache-dir /root/trivy/trivy-proxy-work/cache \
  --output-dir /root/trivy/native-report-20260924
```

먼저 **`reports/actionable.csv`**를 확인하세요.

| 파일 | 내용 |
|---|---|
| `reports/actionable.csv` | 공식 Trivy 취약점과 자체 RPM 검토 필요 CVE |
| `reports/fix-available.csv` | 수정 버전이 있는 vendor 항목 |
| `reports/vendor-actionable.csv`, `reports/native-review.csv` | vendor 취약점 / 자체 RPM 검토 대상 |
| `reports/reviewed-resolutions.csv`, `reports/scan-gaps.csv` | 수정·비해당 근거 / 검사 범위 제한 |
| `reports/integrated.csv` | 위 결과 + 수정 근거 일치 + 제품/피드 범위 부족 |
| `reports/summary.json` | 개수, 피드 상태, 전체 범위 미완료 여부 |
| `integrated.json` | 공식 결과와 추가 평가가 들어 있는 원본 Trivy 출력 |
| `installed-evidence.json`, `scan.log` | 로컬 검사 근거. 공개 업로드 금지 |

출력 경로는 새 디렉터리여야 합니다. 검사 중 RPM 변경이나 다른 native 검사를 함께 실행하지 마세요.
종료 코드 0은 실행 성공이며 취약점 0개를 뜻하지 않습니다. `--fail-on-gap`을 추가하면 자체 RPM의
전체 CVE 범위 미완료를 코드 3으로 알립니다. 기본 Trivy CSV 템플릿은 평가 행을 누락하므로 제공한 변환기를 사용합니다.

## 새 RPM과 피드 반영

Windows 개발기의 Go 1.26, Python, Podman으로 실행합니다.

```powershell
./build-integration.ps1 `
  -RpmBundle C:/rpm-builds/full-builds-20260924-7 `
  -OutputDirectory D:/sources/linux-oss/upstream-rpm/output/native-new `
  -RefreshFeed
```

`-RefreshFeed`는 NVD를 6.1초 이상의 요청 간격으로 새로 조회합니다. 대규모 커널 피드를 포함해 시간이 걸릴 수 있습니다. 중단된 조회는 `-ReuseFeedCache`로 재개하며 기존 조회 시각은 유지합니다.
WSL 내부 Podman을 사용할 때는 `-WslDistribution Ubuntu`를 지정할 수 있습니다.
카탈로그와 피드는 WASM 내부에 포함되며 실행 시 해시가 일치해야 합니다.
새 CVE는 **RPM 재빌드 없이 모듈 번들만 갱신**하면 됩니다. 배포물은 미서명이며 신뢰한 릴리스의 체크섬으로 확인합니다.

새 프로젝트는 `project-map.json`에 출처를 확인한 CPE를 추가합니다. 새 수정 판정은
`reviewed-evidence.json`에 정확한 RPM SHA-256과 근거를 넣어야 합니다. 버전 증가만으로 수정 판정을 복사하지 않습니다.
미등록 제품도 결과에서 사라지지 않습니다.

Linux의 개별 빌드 단계:

```bash
python3 refresh-feed.py --cache-dir /work/nvd-cache
python3 build-catalog.py /path/to/rpm-bundle --output catalog.json
python3 -m unittest test_feed.py
go test ./...
GOOS=wasip1 GOARCH=wasm go build -trimpath -ldflags='-s -w' \
  -buildmode=c-shared -o modules/linuxoss-artifact-evidence.wasm .
python3 package-bundle.py --output-dir /work/native-new
```

재개할 때만 `--reuse-cache`를 사용합니다. 캐시 조회 시각은 유지됩니다.
원본 응답 캐시는 개발기에만 두고 배포에는 정규화한 피드만 넣습니다.

## 근거와 한계

- [Trivy third-party 제한](https://trivy.dev/docs/v0.74/guide/scanner/vulnerability/#third-party-packages)
- [Trivy 실험 모듈 API](https://trivy.dev/docs/dev/advanced/modules/): 버전 변경 시 호환성 재검증 필요.
- [NVD API](https://nvd.nist.gov/developers/vulnerabilities)
- 제품 매핑과 개별 수정 근거의 출처는 두 JSON 파일에 기록합니다.
- 기존 Trivy DB와 추가 NVD 피드는 갱신 시각이 다르므로 둘 다 갱신해야 합니다.
- [전체 제작 현황](../ALL-BUILDS.md)과 [개별 산출물](../BUILD-CATALOG.json)을 함께 확인하세요. 설치되지 않은 RPM을 검사한 것으로 계산하지 않습니다.
- 커널은 NVD의 운영체제 제품(`part=o`)으로 매핑하며, UAPI 헤더를 실행 커널로 계산하지 않습니다.
- 설치된 RPM의 정확한 헤더에 해당하는 파일만 해시를 계산합니다.
- 323종 전체 교체 완료나 운영 서버 모든 CVE 해결을 뜻하지 않습니다.

This product uses data from the NVD API but is not endorsed or certified by the NVD.

20260925-5 판정 기준과 검증은 [다음 묶음 변경 내용](../deploy/NEXT-WAVE-20260925-5.md)을 참조하세요.
