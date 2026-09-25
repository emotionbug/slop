package main

import (
	"encoding/json"
	"testing"
)

func TestMappingDigestIgnoresCheckoutLineEndings(t *testing.T) {
	lf := []byte("{\n  \"project\": \"tar\"\n}\n")
	crlf := []byte("{\r\n  \"project\": \"tar\"\r\n}\r\n")
	if mappingDigest(lf) != mappingDigest(crlf) {
		t.Fatal("Windows checkout line endings changed mapping identity")
	}
	if mappingDigest(lf) == mappingDigest([]byte("{\n  \"project\": \"npm-tar\"\n}\n")) {
		t.Fatal("Changed product mapping retained identity")
	}
}

func testInput(t *testing.T) (Snapshot, Catalog) {
	t.Helper()
	var c Catalog
	if err := json.Unmarshal(catalogBytes, &c); err != nil {
		t.Fatal(err)
	}
	s := Snapshot{Schema: 1, CatalogHash: catalogueHash(), FeedHash: digest(feedBytes), CreatedAt: "2026-09-24T00:00:00Z", Files: map[string]FileCheck{}}
	// A catalogue can retain old and rebuilt RPMs; only one non-installonly
	// version of each name/arch is installed in this fixture at a time.
	selected := map[string]int{}
	for i, a := range c.Artifacts {
		selected[a.Name+"."+a.Arch] = i
	}
	for i, a := range c.Artifacts {
		if selected[a.Name+"."+a.Arch] != i {
			continue
		}
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
	expectedFixed, expectedCoverage := 0, 0
	installed := map[RPM]bool{}
	for _, p := range s.Packages {
		installed[p] = true
	}
	for _, a := range c.Artifacts {
		if !installed[a.RPM] {
			continue
		}
		expectedCoverage += 1 + len(a.Components)
		for _, r := range a.Assessments {
			if r.Status == "fixed" && len(a.Files) > 0 {
				expectedFixed++
			}
		}
	}
	if counts["fixed-evidence-matched"] != expectedFixed || counts["coverage-gap"]+counts["payload-unverified"] != expectedCoverage {
		t.Fatal(counts)
	}
}

func TestRetainedLegacyReleasesMatchIndividually(t *testing.T) {
	_, c := testInput(t)
	for _, a := range c.Artifacts {
		if a.Name != "sed" && a.Name != "gawk" && a.Name != "cpio" && a.Name != "tar" && a.Name != "coreutils" && a.Name != "coreutils-common" && a.Name != "bison" {
			continue
		}
		s := Snapshot{Schema: 1, CatalogHash: catalogueHash(), FeedHash: digest(feedBytes), CreatedAt: "2026-09-25T00:00:00Z", Packages: []RPM{a.RPM}, Files: map[string]FileCheck{}}
		for p, h := range a.Files {
			s.Files[p] = FileCheck{Hash: h}
		}
		rows, err := evaluate(s, c)
		if err != nil || len(rows) == 0 {
			t.Fatalf("%s %s: rows=%d err=%v", a.Name, a.Release, len(rows), err)
		}
		for _, row := range rows {
			if row.Status == "artifact-mismatch" || row.Status == "payload-mismatch" || row.Status == "unregistered" {
				t.Fatalf("retained artifact was not matched: %+v", row)
			}
		}
	}
}

func TestRangeBoundariesAndUnknowns(t *testing.T) {
	cases := []struct {
		v    string
		r    VersionRange
		want verdict
	}{
		{"1.2", VersionRange{Version: "*", StartIncluding: "1.2", EndExcluding: "1.3"}, candidate},
		{"1.3", VersionRange{Version: "*", EndExcluding: "1.3"}, excluded},
		{"1.3", VersionRange{Version: "*", EndIncluding: "1.3"}, candidate},
		{"1.3", VersionRange{Version: "*", StartExcluding: "1.3"}, excluded},
		{"3.7c", VersionRange{Version: "*", EndIncluding: "3.7b"}, uncertain},
		{"3.7c", VersionRange{Version: "3.7c"}, candidate},
		{"2.0", VersionRange{Version: "*", EndIncluding: "1.0", Negated: true}, uncertain},
		{"2.0", VersionRange{Version: "*", EndIncluding: "1.0", Distro: true}, uncertain},
		{"1.2", VersionRange{Version: "*", Conditional: true}, uncertain},
	}
	for _, c := range cases {
		if got := c.r.match(c.v); got != c.want {
			t.Fatalf("%+v got %v", c, got)
		}
	}
	if got, ok := compareVersions("1.10", "1.9"); !ok || got != 1 {
		t.Fatal("lexical version ordering")
	}
	if got, ok := compareVersions("1.2.0", "1.2"); !ok || got != 0 {
		t.Fatal("zero padding")
	}
	if (Advisory{}).match("1.0") != uncertain {
		t.Fatal("missing range became clean")
	}
}
func TestFeedDigestMismatchFails(t *testing.T) {
	s, c := testInput(t)
	s.FeedHash = "changed"
	if _, e := evaluate(s, c); e == nil {
		t.Fatal("feed mismatch accepted")
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
