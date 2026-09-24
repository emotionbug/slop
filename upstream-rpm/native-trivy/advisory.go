package main

import (
	"strconv"
	"strings"
	"time"
)

type Component struct {
	Project string `json:"project"`
	Version string `json:"version"`
}
type Feed struct {
	Schema      int                    `json:"schema_version"`
	MappingHash string                 `json:"mapping_sha256"`
	Projects    map[string]ProjectFeed `json:"projects"`
}
type ProjectFeed struct {
	Complete bool `json:"query_complete"`
	Queries  []struct {
		Status string `json:"status"`
		Pages  []struct {
			Retrieved string `json:"retrieved_at"`
		} `json:"pages"`
	} `json:"queries"`
	Advisories []Advisory `json:"advisories"`
}

func (p ProjectFeed) state(now time.Time) string {
	if len(p.Queries) == 0 {
		return "unmapped"
	}
	if !p.Complete {
		return "query-incomplete"
	}
	for _, q := range p.Queries {
		if q.Status != "ok" || len(q.Pages) == 0 {
			return "query-incomplete"
		}
		for _, page := range q.Pages {
			date, err := time.Parse(time.RFC3339Nano, page.Retrieved)
			if err != nil || now.Sub(date) > 30*24*time.Hour || date.Sub(now) > 24*time.Hour {
				return "stale-or-invalid-date"
			}
		}
	}
	return "selected-cpe-queries-current"
}

type Advisory struct {
	CVE      string         `json:"cve"`
	Severity string         `json:"severity"`
	Status   string         `json:"status"`
	Advisory string         `json:"advisory"`
	Matches  []VersionRange `json:"matches"`
}
type VersionRange struct {
	Version        string `json:"version"`
	StartIncluding string `json:"versionStartIncluding"`
	StartExcluding string `json:"versionStartExcluding"`
	EndIncluding   string `json:"versionEndIncluding"`
	EndExcluding   string `json:"versionEndExcluding"`
	Conditional    bool   `json:"conditional"`
	Distro         bool   `json:"distro_alias"`
	Negated        bool   `json:"negated"`
}
type verdict int

const (
	excluded verdict = iota
	candidate
	uncertain
)

// Numeric dotted upstream versions only. RPM release/epoch are never compared
// against upstream ranges. Unknown suffixes stay reviewable, not lexical guesses.
func compareVersions(a, b string) (int, bool) {
	parse := func(s string) ([]uint64, bool) {
		if s == "" {
			return nil, false
		}
		values := []uint64{}
		for _, part := range strings.Split(s, ".") {
			for _, r := range part {
				if r < '0' || r > '9' {
					return nil, false
				}
			}
			n, e := strconv.ParseUint(part, 10, 64)
			if e != nil {
				return nil, false
			}
			values = append(values, n)
		}
		return values, true
	}
	x, ok := parse(a)
	if !ok {
		return 0, false
	}
	y, ok := parse(b)
	if !ok {
		return 0, false
	}
	for i := 0; i < len(x) || i < len(y); i++ {
		var v, w uint64
		if i < len(x) {
			v = x[i]
		}
		if i < len(y) {
			w = y[i]
		}
		if v < w {
			return -1, true
		}
		if v > w {
			return 1, true
		}
	}
	return 0, true
}
func (v VersionRange) match(version string) verdict {
	// Distribution aliases may encode vendor release semantics, not upstream.
	if v.Distro || v.Negated {
		return uncertain
	}
	unknown := false
	if v.Version != "*" {
		if v.Version == version && version != "-" {
		} else {
			cmp, ok := compareVersions(version, v.Version)
			if !ok {
				unknown = true
			} else if cmp != 0 {
				return excluded
			}
		}
	}
	for _, bound := range []struct {
		value            string
		lower, inclusive bool
	}{
		{v.StartIncluding, true, true}, {v.StartExcluding, true, false},
		{v.EndIncluding, false, true}, {v.EndExcluding, false, false},
	} {
		if bound.value == "" {
			continue
		}
		cmp, ok := compareVersions(version, bound.value)
		if !ok {
			unknown = true
			continue
		}
		if (bound.lower && (cmp < 0 || (cmp == 0 && !bound.inclusive))) || (!bound.lower && (cmp > 0 || (cmp == 0 && !bound.inclusive))) {
			return excluded
		}
	}
	if unknown || v.Conditional {
		return uncertain
	}
	return candidate
}
func (a Advisory) match(version string) verdict {
	if len(a.Matches) == 0 {
		return uncertain
	}
	result := excluded
	for _, m := range a.Matches {
		v := m.match(version)
		if v == candidate {
			return candidate
		}
		if v == uncertain {
			result = uncertain
		}
	}
	return result
}
