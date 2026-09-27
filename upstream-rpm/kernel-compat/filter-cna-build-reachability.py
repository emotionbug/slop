#!/usr/bin/env python3
"""Split a Linux CNA manifest by exact kernel build dependency inputs."""
import argparse
import hashlib
import json
from pathlib import Path


def normalized(path):
    return path[2:] if path.startswith('./') else path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--build-inputs', type=Path, required=True)
    parser.add_argument('--reachable-output', type=Path, required=True)
    parser.add_argument('--report-output', type=Path, required=True)
    args = parser.parse_args()

    manifest_bytes = args.manifest.read_bytes()
    build_bytes = args.build_inputs.read_bytes()
    manifest = json.loads(manifest_bytes)
    build = json.loads(build_bytes)
    inputs = {normalized(path) for path in build['source_inputs']}
    reachable = []
    report_items = []
    counts = {'built-source-input': 0, 'not-built-in-config': 0}
    for item in manifest['items']:
        built = sorted({path for path in item['program_files']
                        if normalized(path) in inputs})
        status = 'built-source-input' if built else 'not-built-in-config'
        counts[status] += 1
        result = dict(item)
        result['build_status'] = status
        result['built_program_files'] = built
        report_items.append(result)
        if built:
            reachable.append(item)

    reachable_manifest = dict(manifest)
    reachable_manifest['items'] = reachable
    report = {
        'schema_version': 1,
        'scope': ('Exact dependency match against recorded .cmd build inputs. '
                  'This establishes whether named source files contributed to '
                  'the build, not whether a vulnerability is exploitable.'),
        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
        'build_inputs_sha256': hashlib.sha256(build_bytes).hexdigest(),
        'counts': counts,
        'items': report_items,
    }
    for path, value in [(args.reachable_output, reachable_manifest),
                        (args.report_output, report)]:
        with path.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    main()
