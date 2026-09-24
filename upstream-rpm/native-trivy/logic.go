package main

import (
	"crypto/sha256"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
)

//go:embed catalog.json
var catalogBytes []byte

type RPM struct {
	Name    string `json:"name"`
	Epoch   string `json:"epochnum"`
	Version string `json:"version"`
	Release string `json:"release"`
	Arch    string `json:"arch"`
	Vendor  string `json:"vendor"`
	Source  string `json:"sourcerpm"`
	Header  string `json:"sha256header"`
}
type Assessment struct {
	CVE          string `json:"cve"`
	Status       string `json:"status"`
	Scope        string `json:"scope"`
	Advisory     string `json:"advisory"`
	Patch        string `json:"patch_commit"`
	Evidence     string `json:"evidence"`
	Verification string `json:"verification"`
}
type Artifact struct {
	RPM
	RPMHash     string            `json:"rpm_sha256"`
	SourceHash  string            `json:"srpm_sha256"`
	Files       map[string]string `json:"files"`
	Assessments []Assessment      `json:"assessments"`
}
type Catalog struct {
	Schema    int        `json:"schema_version"`
	Artifacts []Artifact `json:"artifacts"`
}
type FileCheck struct {
	Hash  string `json:"sha256"`
	Error string `json:"error"`
}
type Snapshot struct {
	Schema      int                  `json:"schema_version"`
	CatalogHash string               `json:"catalog_sha256"`
	CreatedAt   string               `json:"created_at"`
	Packages    []RPM                `json:"packages"`
	Files       map[string]FileCheck `json:"checked_files"`
}
type Row struct {
	RPM
	Status     string `json:"assessment_status"`
	CVE        string `json:"cve,omitempty"`
	Reason     string `json:"reason"`
	RPMHash    string `json:"rpm_sha256,omitempty"`
	SourceHash string `json:"srpm_sha256,omitempty"`
	Advisory   string `json:"advisory,omitempty"`
	Evidence   string `json:"evidence,omitempty"`
	Patch      string `json:"patch_commit,omitempty"`
	Coverage   string `json:"coverage"`
}

func catalogueHash() string {
	digest := sha256.Sum256(catalogBytes)
	return hex.EncodeToString(digest[:])
}

func evaluate(s Snapshot, c Catalog) ([]Row, error) {
	if s.Schema != 1 || c.Schema != 1 || s.CatalogHash != catalogueHash() || s.CreatedAt == "" {
		return nil, fmt.Errorf("snapshot/catalog mismatch; collect new evidence with the matching catalogue")
	}
	rows := []Row{}
	for _, pkg := range s.Packages {
		row := Row{RPM: pkg, Status: "unassessed", Coverage: "incomplete",
			Reason: "No complete upstream advisory feed; no clean verdict"}
		var match *Artifact
		for i := range c.Artifacts {
			if pkg == c.Artifacts[i].RPM && pkg.Header != "" {
				match = &c.Artifacts[i]
				break
			}
		}
		if match == nil {
			row.Status = "artifact-mismatch"
			row.Reason = "Installed NEVRA/vendor/source/header does not match the release catalogue"
			rows = append(rows, row)
			continue
		}
		row.RPMHash, row.SourceHash = match.RPMHash, match.SourceHash
		if len(match.Assessments) == 0 {
			row.Reason = "Release RPM and SRPM linked by metadata; CVE assessment remains incomplete"
			rows = append(rows, row)
			continue
		}
		for _, assessment := range match.Assessments {
			r := row
			r.CVE, r.Advisory, r.Evidence, r.Patch = assessment.CVE, assessment.Advisory, assessment.Evidence, assessment.Patch
			r.Status = "under-investigation"
			r.Reason = "Security-relevant executable hash missing or different; patch evidence cannot be applied"
			verified := len(match.Files) > 0
			for path, expected := range match.Files {
				actual, found := s.Files[path]
				verified = verified && found && actual.Error == "" && actual.Hash == expected && len(expected) == 64
			}
			if verified && assessment.Status == "fixed" {
				r.Status = "fixed-evidence-matched"
				r.Reason = "Reviewed patch plus exact RPM header and executable SHA-256 match; " + assessment.Scope
			}
			rows = append(rows, r)
		}
	}
	return rows, nil
}

func scanSnapshot(s Snapshot) ([]Row, error) {
	var c Catalog
	if err := json.Unmarshal(catalogBytes, &c); err != nil {
		return nil, err
	}
	return evaluate(s, c)
}
