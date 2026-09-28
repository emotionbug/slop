#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "build-exact-product-openvex.py"
NAME = "kernel-linuxoss-el8-compat"
VERSION = "4.18.0-553.168.1.linuxoss6.el8_10"
EXACT_PURL = f"pkg:rpm/redhat/{NAME}@{VERSION}?arch=x86_64&distro=redhat-8.10"
FALLBACK_PURL = "pkg:rpm/redhat/kernel@4.18.0-553.166.1.el8_10?arch=x86_64&distro=redhat-8.10"


def statement(cve, status):
    value = {
        "vulnerability": {"name": cve},
        "products": [{"@id": f"pkg:rpm/{NAME}@{VERSION}?arch=x86_64"}],
        "status": status,
        "impact_statement": "fixture evidence",
    }
    if status == "not_affected":
        value["justification"] = "component_not_present"
    return value


class ExactProductOpenVEXTest(unittest.TestCase):
    def inputs(self, root):
        semantic = {
            "@context": "https://openvex.dev/ns/v0.2.0", "@id": "fixture",
            "author": "fixture", "timestamp": "2026-09-28T00:00:00Z", "version": 1,
            "statements": [
                statement("CVE-TEST-FIXED", "fixed"),
                statement("CVE-TEST-NA", "not_affected"),
                statement("CVE-TEST-AFFECTED", "affected"),
            ],
        }
        report = {
            "SchemaVersion": 2,
            "Results": [{"Packages": [
                {"Name": NAME, "Version": "4.18.0", "Release": "553.168.1.linuxoss6.el8_10",
                 "Identifier": {"PURL": EXACT_PURL}},
                {"Name": "kernel", "Version": "4.18.0", "Release": "553.166.1.el8_10",
                 "Identifier": {"PURL": FALLBACK_PURL}},
            ]}],
        }
        semantic_path, report_path = root / "semantic.json", root / "trivy.json"
        semantic_path.write_text(json.dumps(semantic), encoding="utf-8")
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return semantic_path, report_path

    def test_binds_only_exact_custom_runtime_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            semantic, report = self.inputs(root)
            output = root / "exact.json"
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--trivy-report", str(report),
                "--semantic-openvex", str(semantic), "--output", str(output),
            ], check=True, text=True, capture_output=True)
            summary = json.loads(result.stdout)
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(2, summary["statements"])
            self.assertEqual({"fixed": 1, "not_affected": 1}, summary["statuses"])
            self.assertEqual({"CVE-TEST-FIXED", "CVE-TEST-NA"}, {
                s["vulnerability"]["name"] for s in document["statements"]})
            products = {p["@id"] for s in document["statements"] for p in s["products"]}
            self.assertEqual({EXACT_PURL}, products)
            self.assertNotIn(FALLBACK_PURL, json.dumps(document))

    def test_fails_closed_when_only_fallback_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            semantic, report = self.inputs(root)
            raw = json.loads(report.read_text(encoding="utf-8"))
            raw["Results"][0]["Packages"] = raw["Results"][0]["Packages"][1:]
            report.write_text(json.dumps(raw), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--trivy-report", str(report),
                "--semantic-openvex", str(semantic), "--output", str(root / "exact.json"),
            ], text=True, capture_output=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("exact package", result.stderr)


if __name__ == "__main__":
    unittest.main()
