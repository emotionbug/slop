#!/usr/bin/env python3
"""Export official findings and module assessments from ONE Trivy JSON."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


def cell(value):
    value = str(value if value is not None else "")
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--fail-on-gap", action="store_true")
    args = parser.parse_args()
    raw = args.report.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if (data.get("Trivy") or {}).get("Version") != "0.74.0":
        raise ValueError("This integration is verified only for Trivy 0.74.0")
    native = [r for r in data["Results"] if r.get("Type") == "linuxoss-native"]
    if len(native) != 1:
        raise ValueError("Native module output missing/duplicated; do not treat as clean")
    assessments = [r["Data"] for r in native[0].get("CustomResources", [])
                   if r["Type"] == "linuxoss-cve-assessment"]
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    def key(p):
        return (p["name"], str(p["epochnum"]), p["version"], p["release"], p["arch"])
    expected = {key(p) for p in snapshot["packages"]}
    observed = {key(p) for p in assessments}
    packages = [p for r in data["Results"] if r.get("Class") == "os-pkgs" for p in r.get("Packages", [])]
    actual = {(p["Name"], str(p.get("Epoch", 0)), p["Version"], p.get("Release", ""), p.get("Arch", ""))
              for p in packages if p.get("Maintainer") == "Linux OSS local build" or "linuxoss" in p.get("Release", "")}
    if expected != observed or actual != expected:
        raise ValueError("RPM snapshot, Trivy RPM inventory and module output disagree; re-scan")
    fields = ["source", "package", "installed_version", "CVE", "severity", "status",
              "fixed_version", "reason", "reference", "rpm_sha256", "srpm_sha256", "coverage",
              "upstream_project", "component_version", "feed_state", "feed_sha256"]
    rows = []
    for result in data["Results"]:
        if result.get("Type") == "linuxoss-native":
            continue  # Custom findings are represented once, via their assessment records.
        for v in result.get("Vulnerabilities", []):
            rows.append(["trivy:" + result.get("Type", ""), v["PkgName"], v["InstalledVersion"],
                         v["VulnerabilityID"], v.get("Severity", "UNKNOWN"), v.get("Status", "unknown"),
                         v.get("FixedVersion", ""), v.get("Title", ""), v.get("PrimaryURL", ""), "", "", "vendor-feed", "", "", "", ""])
    for a in assessments:
        rows.append(["linuxoss-artifact-evidence", a["name"],
                     a["epochnum"] + ":" + a["version"] + "-" + a["release"] + "." + a["arch"],
                     a.get("cve", ""), a.get("severity") or "UNKNOWN", a["assessment_status"], "", a["reason"],
                     a.get("advisory", ""), a.get("rpm_sha256", ""), a.get("srpm_sha256", ""), a["coverage"],
                     a.get("project", ""), a.get("component_version", ""), a.get("feed_state", ""), a.get("feed_sha256", "")])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / "integrated.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows([cell(value) for value in row] for row in rows)
    actionable = [r for r in rows if r[3] and r[5] != "fixed-evidence-matched"]
    with (args.output_dir / "actionable.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows([cell(value) for value in row] for row in actionable)
    summary = {"trivy_version": "0.74.0", "report_sha256": hashlib.sha256(raw).hexdigest(),
               "custom_packages": len(expected), "assessment_rows": len(assessments),
               "assessments": dict(Counter(a["assessment_status"] for a in assessments)),
               "actionable_rows": len(actionable),
               "native_cve_candidates": sum(bool(a.get("cve")) and a["assessment_status"] == "under-investigation" for a in assessments),
               "selected_feed_states": dict(Counter(a.get("feed_state", "") for a in assessments if not a.get("cve"))),
               "feed_sha256": snapshot["feed_sha256"],
               "custom_packages_without_complete_cve_coverage": len(expected),
               "complete_upstream_feed": False, "all_cves_fixed": False,
               "scope": "Selected NVD CPE version ranges and artifact-pinned reviews; mapping, feed and live-process gaps remain"}
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 3 if args.fail_on_gap and expected else 0


if __name__ == "__main__":
    raise SystemExit(main())
