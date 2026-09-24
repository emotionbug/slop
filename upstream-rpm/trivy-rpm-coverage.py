#!/usr/bin/env python3
"""Report RHEL RPM advisory-coverage gaps without changing Trivy findings.

Python 3.6+ / standard library only. Input is a Trivy JSON report generated with
--list-all-pkgs. This is an inventory/coverage report, NOT a vulnerability scanner.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys


FIELDS = ["package", "epoch", "version", "release", "arch", "source_package",
          "source_version", "source_release", "vendor", "repository_class",
          "purl", "reported_finding_count", "coverage_status", "meaning"]


def classify(package, finding_count, artifact_type):
    repo_class = (package.get("Repository") or {}).get("Class", "")
    custom = ("linuxoss" in package.get("Release", "") or
              package.get("Maintainer", "") == "Linux OSS local build")
    if package.get("Name") == "gpg-pubkey":
        return "not-a-software-package", "RPM public key record; not a software CVE target."
    if artifact_type in ("cyclonedx", "spdx"):
        return "sbom-origin-review-required", (
            "SBOM re-scan may lose RPM repository/vendor classification; use the original rootfs JSON.")
    if repo_class == "third-party":
        if finding_count:
            return "third-party-findings-review-required", (
                "Findings exist, but an applicable custom advisory feed has not been verified.")
        return "excluded-third-party", (
            "Default RHEL detector excludes third-party RPMs; zero findings do not mean fixed.")
    if custom:
        return "custom-feed-review-required", (
            "Custom build identified; Red Hat fixed-version comparisons are not sufficient evidence.")
    if repo_class == "official":
        return "vendor-feed-eligible", (
            "Eligible for the RHEL feed; this does not prove complete coverage or absence of CVEs.")
    return "origin-unknown", "Missing repository classification; coverage cannot be confirmed."


def make_report(report):
    if not isinstance(report, dict) or report.get("SchemaVersion") != 2:
        raise ValueError("Expected Trivy SchemaVersion 2 JSON, not CSV or a CycloneDX SBOM.")
    results = [r for r in (report.get("Results") or [])
               if r.get("Class") == "os-pkgs" and r.get("Type") == "redhat"]
    if not results or any(not r.get("Packages") for r in results):
        raise ValueError("RHEL package inventory is absent; re-scan with --list-all-pkgs.")
    rows = []
    for result in results:
        findings = result.get("Vulnerabilities") or []
        by_id = Counter(v["PkgID"] for v in findings if v.get("PkgID"))
        by_purl = Counter((v.get("PkgIdentifier") or {}).get("PURL")
                          for v in findings if (v.get("PkgIdentifier") or {}).get("PURL"))
        for pkg in result["Packages"]:
            if not pkg.get("Name") or not pkg.get("Version"):
                raise ValueError("Package inventory contains a record without name/version.")
            purl = (pkg.get("Identifier") or {}).get("PURL", "")
            count = by_id[pkg["ID"]] if pkg.get("ID") else by_purl[purl]
            status, meaning = classify(pkg, count, report.get("ArtifactType", ""))
            rows.append(dict(zip(FIELDS, [
                pkg["Name"], pkg.get("Epoch", 0), pkg["Version"], pkg.get("Release", ""),
                pkg.get("Arch", ""), pkg.get("SrcName", ""), pkg.get("SrcVersion", ""),
                pkg.get("SrcRelease", ""), pkg.get("Maintainer", ""),
                (pkg.get("Repository") or {}).get("Class", ""), purl, count, status, meaning])))
    rows.sort(key=lambda r: (r["package"], r["arch"], str(r["epoch"]), r["version"], r["release"]))
    gaps = [r for r in rows if r["coverage_status"] not in
            ("vendor-feed-eligible", "not-a-software-package")]
    summary = {
        "schema_version": 1,
        "trivy_version": (report.get("Trivy") or {}).get("Version", "unknown"),
        "artifact_type": report.get("ArtifactType", "unknown"),
        "scan_created_at": report.get("CreatedAt", "unknown"),
        "os": (report.get("Metadata") or {}).get("OS"),
        "package_rows": len(rows), "coverage_gap_rows": len(gaps),
        "statuses": dict(Counter(r["coverage_status"] for r in rows)),
        "scope": "Default RHEL OS advisory feed; not a custom/upstream CVE detector.",
        "limitations": ["Only packages listed in the input are assessed.",
                        "No scan log, installed file, DB freshness or feed completeness verification.",
                        "No existing finding is removed or marked fixed.",
                        "Zero findings and zero gaps are not a security attestation."]}
    return rows, gaps, summary


def csv_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({key: csv_cell(value) for key, value in row.items()} for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Original os-rpms.json with --list-all-pkgs")
    parser.add_argument("--output-dir", required=True, type=Path, help="New output directory")
    parser.add_argument("--fail-on-gap", action="store_true", help="Exit 3 when coverage gaps exist")
    args = parser.parse_args()
    try:
        raw = args.report.read_bytes()
        rows, gaps, summary = make_report(json.loads(raw.decode("utf-8-sig")))
        summary["input_sha256"] = hashlib.sha256(raw).hexdigest()
        # Refuse an existing directory so previous reports and inputs stay intact.
        args.output_dir.mkdir(parents=True, exist_ok=False)
        write_csv(args.output_dir / "rpm-coverage.csv", rows)
        write_csv(args.output_dir / "rpm-coverage-gaps.csv", gaps)
        (args.output_dir / "coverage-summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2
    print("Package rows: {}; coverage gaps requiring review: {}".format(len(rows), len(gaps)))
    print("Reports: {}".format(args.output_dir))
    print("This report does not mark any CVE fixed or supply a custom vulnerability feed.")
    return 3 if gaps and args.fail_on_gap else 0


if __name__ == "__main__":
    sys.exit(main())
