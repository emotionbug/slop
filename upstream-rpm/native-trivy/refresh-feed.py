#!/usr/bin/env python3
"""Fetch selected NVD CPE advisories for offline Trivy integration (Python 3.6+).

No API key required. Requests are spaced by at least six seconds; errors remain
visible in the feed and produce exit code 2. Raw responses are cached locally.
Rebuild the WASM module after refreshing: the feed is embedded and hash pinned.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request


def cpe_parts(value):
    return re.split(r"(?<!\\):", value)


def normalize(cve, alias):
    matches = []
    def walk(node, conditional=False, negated=False):
        negated = negated or node.get("negate", False)
        conditional = conditional or node.get("operator") == "AND"
        for m in node.get("cpeMatch", []):
            p = cpe_parts(m.get("criteria", ""))
            if len(p) != 13 or p[2:5] != [alias["part"], alias["vendor"], alias["product"]] or not m.get("vulnerable"):
                continue
            match = {"criteria": m["criteria"], "version": p[5],
                     "conditional": conditional or any(x not in ("*", "-") for x in p[6:]),
                     "negated": negated,
                     "distro_alias": alias["vendor"] in ("redhat", "gentoo")}
            for k in ("versionStartIncluding", "versionStartExcluding", "versionEndIncluding", "versionEndExcluding"):
                if k in m:
                    match[k] = m[k]
            matches.append(match)
        for child in node.get("nodes", []):
            walk(child, conditional, negated)
    for config in cve.get("configurations", []):
        walk(config)
    severity = "UNKNOWN"
    for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        metrics = cve.get("metrics", {}).get(key, [])
        if metrics:
            selected = next((m for m in metrics if m.get("type") == "Primary"), metrics[0])
            severity = selected.get("cvssData", {}).get("baseSeverity", selected.get("baseSeverity", "UNKNOWN"))
            break
    return {"cve": cve["id"], "severity": severity, "status": cve.get("vulnStatus", "Unknown"),
            "published": cve.get("published", ""), "modified": cve.get("lastModified", ""),
            "advisory": "https://nvd.nist.gov/vuln/detail/" + cve["id"], "matches": matches}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mapping", type=Path, default=Path(__file__).with_name("project-map.json"))
    p.add_argument("--output", type=Path, default=Path(__file__).with_name("advisories.json"))
    p.add_argument("--cache-dir", type=Path, required=True)
    p.add_argument("--reuse-cache", action="store_true", help="Resume a dated snapshot; cached retrieval dates stay unchanged")
    args = p.parse_args()
    raw = args.mapping.read_bytes().replace(b"\r\n", b"\n")
    mapping = json.loads(raw.decode("utf-8"))
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    feed = {"schema_version": 1, "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "mapping_sha256": hashlib.sha256(raw).hexdigest(), "complete_upstream_coverage": False,
            "notice": "Selected NVD CPE identifiers only. NVD analysis and product mappings can be incomplete or delayed. This product uses data from the NVD API but is not endorsed or certified by the NVD.",
            "projects": {}}
    last_request = 0
    failed = False
    for project, config in sorted(mapping["projects"].items()):
        out = {"queries": [], "advisories": [], "mapping_status": config["mapping_status"]}
        by_cve = {}
        for alias in config["aliases"]:
            cpe = "cpe:2.3:{part}:{vendor}:{product}:*:*:*:*:*:*:*:*".format(**alias)
            query = {"cpe": cpe, "pages": [], "status": "ok", "total_results": 0}
            start = 0
            try:
                while True:
                    url = "https://services.nvd.nist.gov/rest/json/cves/2.0?" + urllib.parse.urlencode(
                        {"virtualMatchString": cpe, "resultsPerPage": 2000, "startIndex": start})
                    cache = args.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
                    if args.reuse_cache and cache.is_file():
                        saved = json.loads(cache.read_text(encoding="utf-8"))
                    else:
                        time.sleep(max(0, 6.1 - (time.monotonic() - last_request)))
                        last_request = time.monotonic()
                        req = urllib.request.Request(url, headers={"User-Agent": "linuxoss-trivy-offline-feed/2"})
                        with urllib.request.urlopen(req, timeout=75) as response:
                            body = response.read()
                        saved = {"retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                 "body_sha256": hashlib.sha256(body).hexdigest(), "data": json.loads(body)}
                        cache.write_text(json.dumps(saved), encoding="utf-8")
                    data = saved["data"]
                    if data["startIndex"] != start:
                        raise ValueError("Unexpected NVD pagination")
                    query["pages"].append({"url": url, "retrieved_at": saved["retrieved_at"], "sha256": saved["body_sha256"]})
                    query["total_results"] = data["totalResults"]
                    for entry in data["vulnerabilities"]:
                        item = normalize(entry["cve"], alias)
                        if item["cve"] in by_cve:
                            previous = by_cve[item["cve"]]
                            for match in item["matches"]:
                                if match not in previous["matches"]:
                                    previous["matches"].append(match)
                        else:
                            by_cve[item["cve"]] = item
                    start += len(data["vulnerabilities"])
                    if start >= data["totalResults"]:
                        break
                    if not data["vulnerabilities"]:
                        raise ValueError("Incomplete NVD pagination")
            except Exception as exc:
                query.update(status="error", error=str(exc))
                failed = True
            out["queries"].append(query)
            print("{} {} {} CVEs {}".format(project, alias["vendor"], query["total_results"], query["status"]), flush=True)
        out["advisories"] = [by_cve[k] for k in sorted(by_cve)]
        out["query_complete"] = bool(out["queries"]) and all(q["status"] == "ok" for q in out["queries"])
        feed["projects"][project] = out
    args.output.write_text(json.dumps(feed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote {} projects; failed={}".format(len(feed["projects"]), failed), flush=True)
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
