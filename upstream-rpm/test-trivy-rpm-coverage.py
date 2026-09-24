"""Coverage loss must not become a clean or fixed verdict."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("coverage_report", Path(__file__).with_name("trivy-rpm-coverage.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CoverageTests(unittest.TestCase):
    def test_custom_rpm_is_not_clean_even_when_findings_are_empty(self):
        pkg = {"Name": "rsync", "Version": "3.5.1", "Release": "1.linuxoss.el8",
               "Repository": {"Class": "third-party"}}
        self.assertEqual(module.classify(pkg, 0, "filesystem")[0], "excluded-third-party")
        self.assertEqual(module.classify(pkg, 2, "filesystem")[0], "third-party-findings-review-required")

    def test_sbom_missing_vendor_is_not_assumed_official(self):
        pkg = {"Name": "rsync", "Version": "3.5.1", "Release": "1.linuxoss.el8"}
        self.assertEqual(module.classify(pkg, 10, "cyclonedx")[0], "sbom-origin-review-required")
        self.assertEqual(module.classify(pkg, 0, "filesystem")[0], "custom-feed-review-required")
        self.assertEqual(module.classify({"Name": "other"}, 0, "filesystem")[0], "origin-unknown")

    def test_missing_inventory_fails_instead_of_zero_gaps(self):
        for report in ({"bomFormat": "CycloneDX"}, {"SchemaVersion": 2, "Results": []},
                       {"SchemaVersion": 2, "Results": [{"Class": "os-pkgs", "Type": "redhat"}]}):
            with self.assertRaises(ValueError):
                module.make_report(report)

    def test_multiarch_findings_do_not_bleed_between_packages_or_modify_input(self):
        packages = [{"Name": "lib", "Version": "1", "Arch": arch, "ID": arch,
                     "Repository": {"Class": "official"}} for arch in ("i686", "x86_64")]
        report = {"SchemaVersion": 2, "ArtifactType": "filesystem", "Results": [
            {"Class": "os-pkgs", "Type": "redhat", "Packages": packages,
             "Vulnerabilities": [{"PkgID": "i686", "VulnerabilityID": "CVE-TEST"}]}]}
        original = copy.deepcopy(report)
        rows, gaps, summary = module.make_report(report)
        self.assertEqual([r["reported_finding_count"] for r in rows], [1, 0])
        self.assertEqual(gaps, [])
        self.assertEqual(summary["statuses"], {"vendor-feed-eligible": 2})
        self.assertEqual(report, original)


if __name__ == "__main__":
    unittest.main()
