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

func TestEL8BackportEvidenceDoesNotClearUnreviewedCVEs(t *testing.T) {
	_, catalogue := testInput(t)
	cases := []struct{ name, cve, status string }{
		{"kernel-linuxoss-el8-compat", "CVE-2026-52912", "fixed-evidence-matched"},
		{"kernel-linuxoss-el8-compat", "CVE-2019-19339", "under-investigation"},
		{"openssl-libs", "CVE-2026-42768", "fixed-evidence-matched"},
		{"openssl-libs", "CVE-2024-41996", "under-investigation"},
		{"glibc", "CVE-2026-6791", "fixed-evidence-matched"},
		{"glibc", "CVE-2026-89092", "not-affected-evidence-matched"},
	}
	for _, tc := range cases {
		found := false
		for _, a := range catalogue.Artifacts {
			if a.Name != tc.name || (a.Project != "kernel" && a.Release != "17.el8_10.linuxoss.1" && a.Release != "251.el8_10.40.linuxoss.1") {
				continue
			}
			s := Snapshot{Schema: 1, CatalogHash: catalogueHash(), FeedHash: digest(feedBytes),
				CreatedAt: "2026-09-26T12:00:00Z", Packages: []RPM{a.RPM}, Files: map[string]FileCheck{}}
			for path, hash := range a.Files {
				s.Files[path] = FileCheck{Hash: hash}
			}
			rows, err := evaluate(s, catalogue)
			if err != nil {
				t.Fatal(err)
			}
			for _, row := range rows {
				if row.CVE != tc.cve {
					continue
				}
				if row.Status != tc.status {
					t.Fatalf("%s %s: got %s, want %s", tc.name, tc.cve, row.Status, tc.status)
				}
				found = true
			}
		}
		if !found {
			t.Fatalf("missing pinned backport assessment: %s %s", tc.name, tc.cve)
		}
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
		if r.CVE != "" && len(r.Excluded) != 0 {
			t.Fatal("CVE row copied the component exclusion list; response grows quadratically")
		}
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
		expectedCoverage += len(a.Components)
		primaryMapped := false
		for _, component := range a.Components {
			primaryMapped = primaryMapped || component.Project == a.Project
		}
		if !primaryMapped {
			expectedCoverage++
		}
		for _, r := range a.Assessments {
			if r.Status == "fixed" && len(a.Files) > 0 {
				expectedFixed++
			}
		}
	}
	if counts["fixed-evidence-matched"] != expectedFixed || counts["coverage-gap"]+counts["payload-unverified"]+counts["configuration-only"]+counts["filesystem-only"] != expectedCoverage {
		t.Fatal(counts)
	}
}

func TestKernelUsesPinnedUpstreamVersion(t *testing.T) {
	s, c := testInput(t)
	found := false
	for _, a := range c.Artifacts {
		if a.Name != "kernel" || a.Version != "7.2.7_linuxoss+" {
			continue
		}
		found = true
		s.Packages = []RPM{a.RPM}
		s.Files = map[string]FileCheck{}
		for path, hash := range a.Files {
			s.Files[path] = FileCheck{Hash: hash}
		}
		rows, err := evaluate(s, c)
		if err != nil {
			t.Fatal(err)
		}
		summaries := 0
		for _, row := range rows {
			if row.ComponentVersion == a.Version {
				t.Fatal("RPM suffix created a second unparseable kernel version")
			}
			if row.CVE == "" && row.Project == "kernel" {
				summaries++
				if row.ComponentVersion != "7.2.7" || len(row.Excluded) == 0 || row.Coverage != "incomplete" {
					t.Fatal("Lost version-range evaluation or asserted complete coverage", row)
				}
			}
		}
		if summaries != 1 {
			t.Fatal("Kernel source was evaluated more than once", summaries)
		}
	}
	if !found {
		t.Fatal("Pinned kernel artifact missing from test catalogue")
	}
}

func TestComponentReviewNeedsExactPayload(t *testing.T) {
	s, c := testInput(t)
	for i := range c.Artifacts {
		a := &c.Artifacts[i]
		if len(a.Files) == 0 {
			continue
		}
		s.Packages = []RPM{a.RPM}
		for p, h := range a.Files {
			s.Files[p] = FileCheck{Hash: h}
		}
		a.Assessments = []Assessment{{CVE: "CVE-COMPONENT-TEST", Status: "not_affected", Scope: "Reviewed build omits the affected component"}}
		for _, changed := range []bool{false, true} {
			if changed {
				for p := range a.Files {
					s.Files[p] = FileCheck{Hash: "changed"}
					break
				}
			}
			rows, err := evaluate(s, c)
			if err != nil {
				t.Fatal(err)
			}
			found := false
			for _, row := range rows {
				if row.CVE != "CVE-COMPONENT-TEST" {
					continue
				}
				found = true
				want := "not-affected-evidence-matched"
				if changed {
					want = "under-investigation"
				}
				if row.Status != want {
					t.Fatalf("changed=%v status=%s", changed, row.Status)
				}
			}
			if !found {
				t.Fatal("review disappeared")
			}
		}
		return
	}
	t.Fatal("no immutable artifact fixture")
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

func TestOpenSSLVersionRules(t *testing.T) {
	for _, c := range []struct {
		a, b string
		want int
	}{
		{"4.0.2", "1.1.1l", 1}, {"1.1.1k", "1.1.1l", -1}, {"1.0.2z", "1.0.2za", -1},
		{"1.1.1", "1.1.1a", -1}, {"1.1.1za", "1.1.1za", 0},
	} {
		if got, ok := compareProjectVersions("openssl", c.a, c.b); !ok || got != c.want {
			t.Fatal(c, got, ok)
		}
	}
	if _, ok := compareProjectVersions("openssl", "4.0.2", "1.1.1-pre9"); ok {
		t.Fatal("prerelease guessed")
	}
	if _, ok := compareProjectVersions("other", "4.0.2", "1.1.1l"); ok {
		t.Fatal("OpenSSL policy leaked")
	}
}

func TestConfigurationPackageDoesNotDuplicateLibraryCVEs(t *testing.T) {
	s, c := testInput(t)
	rows, err := evaluate(s, c)
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, r := range rows {
		if r.Name == "libssh-config" {
			if r.CVE != "" || r.Status != "configuration-only" {
				t.Fatalf("config treated as code: %+v", r)
			}
			found = true
		}
	}
	if !found {
		t.Fatal("configuration evidence disappeared")
	}
}

func TestSQLiteEnvironmentCVEIsNotSQLiteCodeButTamperingStaysOpen(t *testing.T) {
	s, c := testInput(t)
	check := func(want string) {
		rows, err := evaluate(s, c)
		if err != nil {
			t.Fatal(err)
		}
		for _, r := range rows {
			if r.Name == "sqlite-libs" && r.CVE == "CVE-2022-31631" {
				if r.Status != want {
					t.Fatalf("expected %s: %+v", want, r)
				}
				return
			}
		}
		t.Fatal("PHP/SQLite environment evidence disappeared")
	}
	check("not-affected-component")
	for _, a := range c.Artifacts {
		if a.Name == "sqlite-libs" {
			for path := range a.Files {
				s.Files[path] = FileCheck{Hash: "changed"}
			}
		}
	}
	check("under-investigation")
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
