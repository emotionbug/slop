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


def custom_package(package):
    # Upstream kernel rpm-pkg puts linuxoss in VERSION, with Vendor=The Linux
    # Community and Release=2.el8. Match the collector's identity selection.
    return (package.get('Maintainer') == 'Linux OSS local build' or
            'linuxoss' in package.get('Release', '') or
            'linuxoss' in package.get('Version', ''))


def vendor_review(finding, result, os_info, reviews):
    """Exact vendor fix attestations; never compare modular context hashes as versions."""
    if result.get("Type") != "redhat" or os_info.get("Family") != "redhat" or os_info.get("Name") != "8.10":
        return None
    packages = result.get("Packages", [])
    for item in reviews:
        if (finding.get("PkgName"), finding.get("InstalledVersion"), finding.get("VulnerabilityID")) != (
                item["package"], item["installed_version"], item["cve"]):
            continue
        matches = [p for p in packages if p.get("Name") == item["package"]
                   and p.get("Version") == item["version"] and p.get("Release") == item["release"]
                   and str(p.get("Epoch", 0) or 0) == "0"]
        # A finding without an architecture binding must not clear a multilib sibling.
        if (len(matches) == 1 and matches[0].get("Arch") == item["arch"]
                and matches[0].get("Maintainer") in ("Red Hat, Inc.", "Red Hat, Inc")):
            return item
    return None


def artifact_review(finding, result, assessments):
    """Bind a vendor row to one hash-verified custom RPM/CVE, never by name alone."""
    if result.get('Class') != 'os-pkgs':
        return None
    matches = []
    for package in result.get('Packages', []):
        evr = package.get('Version', '') + '-' + package.get('Release', '')
        epoch = str(package.get('Epoch', 0) or 0)
        if epoch != '0':
            evr = epoch + ':' + evr
        if (package.get('Name'), evr) == (finding.get('PkgName'), finding.get('InstalledVersion')):
            matches.append(package)
    # A finding without an architecture binding cannot resolve multilib siblings.
    if len(matches) != 1:
        return None
    package = matches[0]
    if not custom_package(package):
        return None
    reviewed = [a for a in assessments if a.get('assessment_status') in ('fixed-evidence-matched', 'not-affected-evidence-matched')
                and a.get('cve') == finding.get('VulnerabilityID')
                and a.get('name') == package.get('Name')
                and str(a.get('epochnum')) == str(package.get('Epoch', 0) or 0)
                and a.get('version') == package.get('Version')
                and a.get('release') == package.get('Release')
                and a.get('arch') == package.get('Arch')
                and a.get('vendor') == package.get('Maintainer')
                and len(a.get('rpm_sha256', '')) == 64
                and len(a.get('srpm_sha256', '')) == 64]
    return reviewed[0] if len(reviewed) == 1 else None


def kernel_execution_state(package, version, snapshot):
    runtime_names = {'kernel', 'kernel-core', 'kernel-modules', 'kernel-modules-extra', 'kernel-linuxoss-el8-compat'}
    if package not in runtime_names:
        if package.startswith('kernel-') or package in ('bpftool', 'perf', 'python3-perf'):
            return 'kernel-development-or-userspace'
        return 'not-a-kernel-package'
    matches = []
    for image in snapshot.get('kernel_images', []):
        owner = image.get('owner', {})
        if owner.get('name') not in runtime_names or not owner.get('arch'):
            continue
        evr = owner.get('version', '') + '-' + owner.get('release', '')
        epoch = str(owner.get('epochnum', '0'))
        variants = {evr, epoch + ':' + evr, epoch + ':' + evr + '.' + owner['arch']}
        if version in variants:
            matches.append(image['kernel_release'])
    if len(set(matches)) != 1 or not snapshot.get('running_kernel'):
        return 'kernel-image-or-running-version-unidentified'
    return 'running-kernel-files' if matches[0] == snapshot['running_kernel'] else 'installed-other-kernel-files'


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
              for p in packages if custom_package(p)}
    if expected != observed or actual != expected:
        raise ValueError("RPM snapshot, Trivy RPM inventory and module output disagree; re-scan")
    fields = ["source", "package", "installed_version", "CVE", "severity", "status",
              "fixed_version", "reason", "reference", "rpm_sha256", "srpm_sha256", "coverage",
              "upstream_project", "component_version", "feed_state", "feed_sha256",
              "original_status", "original_reference", "original_reason", "kernel_execution_state"]
    rows = []
    reviews = json.loads(Path(__file__).with_name("vendor-reviews.json").read_text(encoding="utf-8"))["reviews"]
    os_info = data.get("Metadata", {}).get("OS", {})
    for result in data["Results"]:
        if result.get("Type") == "linuxoss-native":
            continue  # Custom findings are represented once, via their assessment records.
        for v in result.get("Vulnerabilities", []):
            row = ["trivy:" + result.get("Type", ""), v["PkgName"], v["InstalledVersion"],
                         v["VulnerabilityID"], v.get("Severity", "UNKNOWN"), v.get("Status", "unknown"),
                         v.get("FixedVersion", ""), v.get("Title", ""), v.get("PrimaryURL", ""), "", "", "vendor-feed", "", "", "", "", "", "", ""]
            review = vendor_review(v, result, os_info, reviews)
            if review:
                row[16:19] = [row[5], row[8], row[7]]
                row[5], row[7], row[8] = "vendor-fixed-version-confirmed", review["reason"], review["reference"]
            exact = artifact_review(v, result, assessments)
            if exact:
                row[16:19] = [row[5], row[8], row[7]]
                row[5], row[7], row[8] = exact['assessment_status'], exact['reason'], exact.get('advisory', '')
                row[9:12] = [exact['rpm_sha256'], exact['srpm_sha256'], exact['coverage']]
            rows.append(row)
    for a in assessments:
        rows.append(["linuxoss-artifact-evidence", a["name"],
                     a["epochnum"] + ":" + a["version"] + "-" + a["release"] + "." + a["arch"],
                     a.get("cve", ""), a.get("severity") or "UNKNOWN", a["assessment_status"], "", a["reason"],
                     a.get("advisory", ""), a.get("rpm_sha256", ""), a.get("srpm_sha256", ""), a["coverage"],
                     a.get("project", ""), a.get("component_version", ""), a.get("feed_state", ""), a.get("feed_sha256", ""), "", "", ""])
    for row in rows:
        row.append(kernel_execution_state(row[1], row[2], snapshot))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / "integrated.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows([cell(value) for value in row] for row in rows)
    resolved_statuses = {"fixed-evidence-matched", "not-affected-component", "not-affected-evidence-matched", "vendor-fixed-version-confirmed"}
    actionable = [r for r in rows if r[3] and r[5] not in resolved_statuses]
    with (args.output_dir / "actionable.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows([cell(value) for value in row] for row in actionable)
    groups = {
        "vendor-actionable.csv": [r for r in actionable if r[0].startswith("trivy:")],
        "native-review.csv": [r for r in actionable if r[0] == "linuxoss-artifact-evidence"],
        "fix-available.csv": [r for r in actionable if r[6]],
        "reviewed-resolutions.csv": [r for r in rows if r[3] and r[5] in resolved_statuses],
        "scan-gaps.csv": [r for r in rows if not r[3]],
        "running-kernel-actionable.csv": [r for r in actionable if r[19] == 'running-kernel-files'],
        "other-installed-kernel-actionable.csv": [r for r in actionable if r[19] == 'installed-other-kernel-files'],
    }
    for name, selected in groups.items():
        with (args.output_dir / name).open("x", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream); writer.writerow(fields)
            writer.writerows([cell(value) for value in row] for row in selected)
    summary = {"trivy_version": "0.74.0", "report_sha256": hashlib.sha256(raw).hexdigest(),
               "running_kernel": snapshot.get("running_kernel", "not-collected"),
               "kernel_scope": "Installed package files only; a fixed RPM does not establish that its kernel is running",
               "custom_packages": len(expected), "assessment_rows": len(assessments),
               "assessments": dict(Counter(a["assessment_status"] for a in assessments)),
               "actionable_rows": len(actionable),
               "actionable_unique_cves": len({r[3] for r in actionable}),
               "actionable_rows_by_kernel_execution_state": dict(Counter(r[19] for r in actionable)),
               "vendor_reviews_applied": sum(r[5] == "vendor-fixed-version-confirmed" for r in rows),
               "vendor_rows_matched_to_custom_patch_evidence": sum(r[0].startswith('trivy:') and r[5] == 'fixed-evidence-matched' for r in rows),
               "vendor_rows_matched_to_component_evidence": sum(r[0].startswith('trivy:') and r[5] == 'not-affected-evidence-matched' for r in rows),
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
