//go:build wasip1

// Minimal implementation of Trivy 0.74.0's experimental module API v1.
// JSON ABI reference: aquasecurity/trivy pkg/module/{api,wasm} at v0.74.0.
// This module uses only Go's standard library; no scanner fork or runtime network.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"unsafe"
)

var buffers = map[uint32][]byte{}

//go:wasmimport env error
func hostError(p uint32, n uint32)

func moduleError(message string) {
	b := []byte(message)
	p := reserve(uint32(len(b)))
	copy(buffers[p], b)
	hostError(p, uint32(len(b)))
	release(p, uint32(len(b)))
}

func main() {}

//go:wasmexport malloc
func reserve(n uint32) uint32 {
	// post_scan receives the complete Trivy result, including all installed
	// fallback kernels. A single EL8 kernel can exceed the former 64 MiB cap.
	if n == 0 || n > 512*1024*1024 {
		moduleError(fmt.Sprintf("linuxoss WASM allocation rejected: %d bytes (limit 512 MiB)", n))
		panic("invalid WASM allocation")
	}
	b := make([]byte, n)
	p := uint32(uintptr(unsafe.Pointer(&b[0])))
	buffers[p] = b
	return p
}

//go:wasmexport free
func release(p uint32, n uint32) { delete(buffers, p) }

func send(b []byte) uint64 {
	p := reserve(uint32(len(b)))
	copy(buffers[p], b)
	return uint64(p)<<32 | uint64(len(b))
}
func response(v interface{}) uint64 {
	b, err := json.Marshal(v)
	if err != nil {
		panic(err)
	}
	return send(b)
}
func input(p, n uint32) []byte {
	b, ok := buffers[p]
	if !ok || n > uint32(len(b)) {
		panic("invalid WASM input buffer")
	}
	return b[:n]
}

//go:wasmexport name
func name() uint64 { return send([]byte("linuxoss-artifact-evidence")) }

//go:wasmexport api_version
func apiVersion() uint32 { return 1 }

//go:wasmexport version
func version() uint32 { return 4 }

//go:wasmexport is_analyzer
func isAnalyzer() uint64 { return 1 }

//go:wasmexport is_post_scanner
func isPostScanner() uint64 { return 1 }

//go:wasmexport required
func required() uint64 {
	return response([]string{`(^|/)run/linuxoss-trivy/[^/]+/linuxoss-installed-evidence\.json$`})
}

//go:wasmexport analyze
func analyze(p, n uint32) uint64 {
	b, err := os.ReadFile(string(input(p, n)))
	if err != nil {
		panic(err)
	}
	var snapshot Snapshot
	if err = json.Unmarshal(b, &snapshot); err != nil {
		panic(err)
	}
	if _, err = scanSnapshot(snapshot); err != nil {
		panic(err)
	}
	return response(map[string]interface{}{"CustomResources": []interface{}{
		map[string]interface{}{"Type": "linuxoss-installed-evidence", "FilePath": string(input(p, n)), "Data": snapshot}}})
}

//go:wasmexport post_scan_spec
func postScanSpec() uint64 { return response(map[string]string{"Action": "INSERT"}) }

//go:wasmexport post_scan
func postScan(p, n uint32) uint64 {
	defer func() {
		if err := recover(); err != nil {
			moduleError(fmt.Sprintf("linuxoss post_scan failed (%d input bytes): %v", n, err))
			panic(err)
		}
	}()
	var results []struct {
		CustomResources []struct {
			Type string
			Data json.RawMessage
		}
	}
	if err := json.Unmarshal(input(p, n), &results); err != nil {
		panic(err)
	}
	var snapshots []Snapshot
	for _, result := range results {
		for _, resource := range result.CustomResources {
			if resource.Type == "linuxoss-installed-evidence" {
				var s Snapshot
				if err := json.Unmarshal(resource.Data, &s); err != nil {
					panic(err)
				}
				snapshots = append(snapshots, s)
			}
		}
	}
	if len(snapshots) != 1 {
		panic("exactly one freshly collected linuxoss snapshot is required")
	}
	rows, err := scanSnapshot(snapshots[0])
	if err != nil {
		panic(err)
	}
	resources := []interface{}{}
	vulns := []interface{}{}
	for _, row := range rows {
		resources = append(resources, map[string]interface{}{"Type": "linuxoss-cve-assessment", "Data": row})
		if row.CVE != "" && row.Status == "under-investigation" {
			vulns = append(vulns, map[string]interface{}{
				"VulnerabilityID": row.CVE, "PkgName": row.Name,
				"InstalledVersion": row.Version + "-" + row.Release,
				"Status":           "under_investigation", "Severity": severity(row),
				"Title":       "Custom RPM upstream advisory requires review: " + row.Project,
				"Description": row.Reason, "PrimaryURL": row.Advisory,
				"DataSource": map[string]string{"ID": "linuxoss-upstream", "Name": "Linux OSS NVD and reviewed artifact evidence (partial)", "URL": "https://github.com/emotionbug/slop/tree/main/upstream-rpm/native-trivy"}})
		}
	}
	return response([]interface{}{map[string]interface{}{
		"Target": "Linux OSS custom RPM evidence (incomplete CVE coverage)",
		"Class":  "lang-pkgs", "Type": "linuxoss-native",
		"CustomResources": resources, "Vulnerabilities": vulns}})
}

func severity(row Row) string {
	if row.Severity == "" {
		return "UNKNOWN"
	}
	return row.Severity
}
