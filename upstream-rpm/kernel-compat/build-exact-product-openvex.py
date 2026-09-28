#!/usr/bin/env python3
"""Bind reviewed kernel OpenVEX statements to PURLs emitted by one Trivy scan.

The semantic input records the reviewed CVE disposition.  It is deliberately
not used as-is for filtering: this program replaces its product list with the
exact PURL Trivy emitted for the expected custom runtime RPM.  Other installed
kernels, headers, devel packages, and older custom builds are never included.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import unquote


ALLOWED_STATUSES = {"fixed", "not_affected"}


def die(message: str) -> "NoReturn":
    raise SystemExit(f"ERROR: {message}")


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read JSON {path}: {exc}")
    if not isinstance(value, dict):
        die(f"top-level JSON value must be an object: {path}")
    return value


def purl_name_version(value: str) -> tuple[str, str]:
    if not value.startswith("pkg:rpm/") or "@" not in value:
        die(f"expected a versioned RPM PURL, got {value!r}")
    body = value[len("pkg:rpm/"):].split("#", 1)[0]
    path_and_version = body.split("?", 1)[0]
    path, version = path_and_version.rsplit("@", 1)
    name = unquote(path.rsplit("/", 1)[-1])
    if not name or not version:
        die(f"incomplete RPM PURL: {value!r}")
    return name, unquote(version)


def semantic_identity(document: dict, package_name: str) -> tuple[str, list[dict]]:
    statements = document.get("statements")
    if not isinstance(statements, list) or not statements:
        die("semantic OpenVEX has no statements")
    versions: set[str] = set()
    seen_cves: set[str] = set()
    selected: list[dict] = []
    for index, statement in enumerate(statements):
        if not isinstance(statement, dict):
            die(f"semantic statement {index} is not an object")
        vulnerability = statement.get("vulnerability") or {}
        cve = vulnerability.get("name")
        if not isinstance(cve, str) or not cve:
            die(f"semantic statement {index} has no vulnerability name")
        if cve in seen_cves:
            die(f"duplicate semantic statement for {cve}")
        seen_cves.add(cve)
        status = statement.get("status")
        if status not in ALLOWED_STATUSES:
            continue
        matching_product = False
        for product in statement.get("products") or []:
            purl = product.get("@id") if isinstance(product, dict) else None
            if not isinstance(purl, str):
                continue
            name, version = purl_name_version(purl)
            if name == package_name:
                matching_product = True
                versions.add(version)
        if not matching_product:
            die(f"semantic statement {cve} has no product for {package_name}")
        selected.append(statement)
    if len(versions) != 1:
        die(f"semantic OpenVEX must identify one {package_name} version; found {sorted(versions)}")
    if not selected:
        die("semantic OpenVEX has no suppressible fixed/not_affected statements")
    return next(iter(versions)), selected


def exact_package_purls(report: dict, package_name: str, expected_version: str) -> list[str]:
    if report.get("SchemaVersion") != 2:
        die(f"unsupported Trivy schema version {report.get('SchemaVersion')!r}; expected 2")
    found_versions: set[str] = set()
    purls: set[str] = set()
    for result in report.get("Results") or []:
        if not isinstance(result, dict):
            continue
        for package in result.get("Packages") or []:
            if not isinstance(package, dict) or package.get("Name") != package_name:
                continue
            version = str(package.get("Version") or "")
            release = str(package.get("Release") or "")
            installed = version + (f"-{release}" if release else "")
            found_versions.add(installed)
            identifier = package.get("Identifier") or {}
            purl = identifier.get("PURL")
            if installed != expected_version:
                continue
            if not isinstance(purl, str) or not purl:
                die(f"Trivy package {package_name}@{installed} has no PURL")
            purl_name, purl_version = purl_name_version(purl)
            if purl_name != package_name or purl_version != expected_version:
                die(f"Trivy package metadata/PURL mismatch: {package_name}@{installed} vs {purl}")
            purls.add(purl)
    if not purls:
        versions = ", ".join(sorted(found_versions)) if found_versions else "none"
        die(f"exact package {package_name}@{expected_version} is absent from the Trivy report "
            f"(installed versions seen: {versions})")
    return sorted(purls)


def build_document(semantic: dict, statements: list[dict], purls: list[str], report: Path) -> dict:
    output_statements = []
    for statement in statements:
        copied = json.loads(json.dumps(statement))
        copied["products"] = [{"@id": purl} for purl in purls]
        output_statements.append(copied)
    counts = collections.Counter(s["status"] for s in output_statements)
    seed = json.dumps(output_statements, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(seed).hexdigest()
    return {
        "@context": semantic.get("@context", "https://openvex.dev/ns/v0.2.0"),
        "@id": f"https://github.com/emotionbug/slop/security/vex/exact-{digest}",
        "author": semantic.get("author", "Linux OSS local build"),
        "timestamp": semantic.get("timestamp"),
        "version": semantic.get("version", 1),
        "statements": output_statements,
        "x_linuxoss_binding": {
            "source_report": report.name,
            "package_purls": purls,
            "statement_counts": dict(sorted(counts.items())),
            "policy": "exact custom runtime RPM only; fallback and unrelated RPMs excluded",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trivy-report", required=True, type=Path)
    parser.add_argument("--semantic-openvex", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--package-name", default="kernel-linuxoss-el8-compat")
    args = parser.parse_args()
    if args.output.exists():
        die(f"refusing to overwrite output: {args.output}")
    semantic = load_json(args.semantic_openvex)
    report = load_json(args.trivy_report)
    expected_version, statements = semantic_identity(semantic, args.package_name)
    purls = exact_package_purls(report, args.package_name, expected_version)
    output = build_document(semantic, statements, purls, args.trivy_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = collections.Counter(s["status"] for s in statements)
    print(json.dumps({
        "package": args.package_name,
        "version": expected_version,
        "purls": purls,
        "statements": len(statements),
        "statuses": dict(sorted(counts.items())),
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
