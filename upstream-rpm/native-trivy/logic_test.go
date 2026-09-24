package main

import (
	"encoding/json"
	"testing"
)

func testInput(t *testing.T) (Snapshot, Catalog) {
	t.Helper()
	var c Catalog
	if err := json.Unmarshal(catalogBytes, &c); err != nil {
		t.Fatal(err)
	}
	s := Snapshot{Schema: 1, CatalogHash: catalogueHash(), CreatedAt: "2026-09-24T00:00:00Z", Files: map[string]FileCheck{}}
	for _, a := range c.Artifacts {
		s.Packages = append(s.Packages, a.RPM)
		for p, h := range a.Files {
			s.Files[p] = FileCheck{Hash: h}
		}
	}
	return s, c
}
func TestKnownPatchAndUnknownCoverage(t *testing.T) {
	s, c := testInput(t)
	rows, err := evaluate(s, c)
	if err != nil {
		t.Fatal(err)
	}
	counts := map[string]int{}
	for _, r := range rows {
		counts[r.Status]++
		if r.Coverage != "incomplete" {
			t.Fatal("false complete verdict")
		}
	}
	if counts["fixed-evidence-matched"] != 1 || counts["unassessed"] != 51 {
		t.Fatal(counts)
	}
}
func TestChangedExecutableRequiresInvestigation(t *testing.T) {
	s, c := testInput(t)
	s.Files["/usr/bin/bzip2recover"] = FileCheck{Hash: "changed"}
	rows, err := evaluate(s, c)
	if err != nil {
		t.Fatal(err)
	}
	for _, r := range rows {
		if r.CVE == "CVE-2026-42250" && r.Status == "under-investigation" {
			return
		}
	}
	t.Fatal("modified file was not flagged")
}
func TestSameVersionDifferentArtifactIsNotFixed(t *testing.T) {
	s, c := testInput(t)
	for i := range s.Packages {
		if s.Packages[i].Name == "bzip2" {
			s.Packages[i].Header = "changed"
		}
	}
	rows, err := evaluate(s, c)
	if err != nil {
		t.Fatal(err)
	}
	for _, r := range rows {
		if r.Name == "bzip2" && r.Status == "artifact-mismatch" {
			return
		}
	}
	t.Fatal("unknown artifact accepted")
}
func TestMismatchedCatalogueFails(t *testing.T) {
	s, c := testInput(t)
	s.CatalogHash = "changed"
	if _, err := evaluate(s, c); err == nil {
		t.Fatal("mismatched catalogue accepted")
	}
}
