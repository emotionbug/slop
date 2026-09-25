package main

import (
	"bytes"
	"crypto/sha256"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"
)

//go:embed catalog.json
var catalogBytes []byte

//go:embed advisories.json
var feedBytes []byte

//go:embed project-map.json
var mappingBytes []byte

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
	Project       string            `json:"project"`
	Components    []Component       `json:"components"`
	RPMHash       string            `json:"rpm_sha256"`
	SourceHash    string            `json:"srpm_sha256"`
	Files         map[string]string `json:"files"`
	Assessments   []Assessment      `json:"assessments"`
	ComponentRole string            `json:"component_role,omitempty"`
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
	FeedHash    string               `json:"feed_sha256"`
	CreatedAt   string               `json:"created_at"`
	Packages    []RPM                `json:"packages"`
	Files       map[string]FileCheck `json:"checked_files"`
}
type Row struct {
	RPM
	Status           string   `json:"assessment_status"`
	CVE              string   `json:"cve,omitempty"`
	Reason           string   `json:"reason"`
	RPMHash          string   `json:"rpm_sha256,omitempty"`
	SourceHash       string   `json:"srpm_sha256,omitempty"`
	Advisory         string   `json:"advisory,omitempty"`
	Evidence         string   `json:"evidence,omitempty"`
	Patch            string   `json:"patch_commit,omitempty"`
	Coverage         string   `json:"coverage"`
	Project          string   `json:"project"`
	ComponentVersion string   `json:"component_version,omitempty"`
	Severity         string   `json:"severity,omitempty"`
	FeedHash         string   `json:"feed_sha256"`
	FeedState        string   `json:"feed_state"`
	Excluded         []string `json:"range_excluded_cves,omitempty"`
}

func catalogueHash() string {
	digest := sha256.Sum256(catalogBytes)
	return hex.EncodeToString(digest[:])
}
func digest(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }

// Git may convert LF to CRLF on Windows. Mapping identity ignores only that conversion.
func mappingDigest(b []byte) string { return digest(bytes.ReplaceAll(b, []byte("\r\n"), []byte("\n"))) }

func evaluate(s Snapshot, c Catalog) ([]Row, error) {
	// The full feed includes kernel advisories. Hash it once per evaluation,
	// rather than re-reading tens of megabytes for every installed package.
	feedHash := digest(feedBytes)
	if s.Schema != 1 || c.Schema != 1 || s.CatalogHash != catalogueHash() || s.FeedHash != feedHash {
		return nil, fmt.Errorf("snapshot/catalog mismatch; collect new evidence with the matching catalogue")
	}
	now, err := time.Parse(time.RFC3339Nano, s.CreatedAt)
	if err != nil {
		return nil, fmt.Errorf("invalid snapshot date: %w", err)
	}
	var feed Feed
	if err = json.Unmarshal(feedBytes, &feed); err != nil {
		return nil, err
	}
	if feed.Schema != 1 || feed.MappingHash != mappingDigest(mappingBytes) {
		return nil, fmt.Errorf("feed/mapping mismatch")
	}
	rows := []Row{}
	for _, pkg := range s.Packages {
		row := Row{RPM: pkg, Status: "coverage-gap", Coverage: "incomplete", FeedHash: feedHash,
			Reason: "Selected product identifiers only; no complete upstream advisory coverage"}
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
		row.Project = match.Project
		if (match.ComponentRole == "configuration-only" || match.ComponentRole == "filesystem-only") && len(match.Files) == 0 {
			row.Status = match.ComponentRole
			row.Reason = "Reviewed exact RPM contains configuration only; code CVEs are assessed on its library package. Configuration content is not verified."
			if match.ComponentRole == "filesystem-only" {
				row.Reason = "Reviewed exact RPM owns directory layout only; executable/library CVEs belong to the code packages. Directory permissions are not verified."
			}
			rows = append(rows, row)
			continue
		}
		verified := len(match.Files) > 0
		for path, expected := range match.Files {
			actual, found := s.Files[path]
			verified = verified && found && actual.Error == "" && actual.Hash == expected && len(expected) == 64
		}
		reviewed := map[string]bool{}
		for _, assessment := range match.Assessments {
			r := row
			reviewed[assessment.CVE] = true
			r.CVE, r.Advisory, r.Evidence, r.Patch = assessment.CVE, assessment.Advisory, assessment.Evidence, assessment.Patch
			r.Status = "under-investigation"
			r.Reason = "Security-relevant executable hash missing or different; patch evidence cannot be applied"
			if assessment.Status != "fixed" {
				r.Reason = assessment.Scope
			}
			if verified && assessment.Status == "fixed" {
				r.Status = "fixed-evidence-matched"
				r.Reason = "Reviewed patch plus exact RPM header and executable SHA-256 match; " + assessment.Scope
			}
			rows = append(rows, r)
		}
		components := append([]Component{{Project: match.Project, Version: pkg.Version}}, match.Components...)
		for _, component := range components {
			summary := row
			summary.Project = component.Project
			summary.ComponentVersion = component.Version
			project, found := feed.Projects[component.Project]
			summary.FeedState = project.state(now)
			if !found {
				summary.FeedState = "unmapped"
			}
			if !verified {
				summary.Reason = "Immutable payload missing or changed; installed upstream version cannot be trusted"
				summary.Status = "payload-mismatch"
				if len(match.Files) == 0 {
					summary.Status = "payload-unverified"
					summary.Reason = "Package contains no hashable immutable files; source-project applicability requires review"
				}
			}
			for _, advisory := range project.Advisories {
				if advisory.Status == "Rejected" {
					continue
				}
				if component.Project == match.Project && reviewed[advisory.CVE] {
					continue
				}
				if advisory.ContextOnly && verified {
					r := summary
					r.CVE, r.Advisory, r.Severity = advisory.CVE, advisory.Advisory, advisory.Severity
					r.Status = "not-affected-component"
					r.Reason = "Queried CPE is only a non-vulnerable environment/dependency in NVD; the vulnerable product must be assessed separately"
					rows = append(rows, r)
					continue
				}
				result := advisory.matchProject(component.Project, component.Version)
				if result == excluded && verified {
					summary.Excluded = append(summary.Excluded, advisory.CVE)
					continue
				}
				r := summary
				r.Excluded = nil
				r.CVE = advisory.CVE
				r.Advisory = advisory.Advisory
				r.Severity = advisory.Severity
				r.Status = "under-investigation"
				r.Reason = "NVD selected-CPE affected-version candidate; component/exposure applicability needs review"
				if result == uncertain {
					r.Reason = "NVD version or environment constraints cannot be fully evaluated"
				}
				if !verified {
					r.Reason = "Payload mismatch prevents reliable installed-version exclusion"
					if len(match.Files) == 0 {
						r.Reason = "No immutable files to verify; source-project applicability requires review"
					}
				}
				rows = append(rows, r)
			}
			rows = append(rows, summary)
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
