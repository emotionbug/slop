#!/usr/bin/env python3
"""Record the compiled source dependency set for later CVE reachability review.

An absent filename is not an unaffected verdict: paths can be renamed or code
backported into a different file. This inventory never changes Trivy status.
"""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tree', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
sources, checked, commands = set(), set(), 0
for f in a.tree.rglob('.*.cmd'):
    text = f.read_text(errors='replace')
    commands += 1
    for token in text.replace('\\\n', ' ').split():
        token = token.strip('()\\,;')
        if not token.endswith(('.c', '.h', '.S')) or token in checked:
            continue
        checked.add(token)
        if not token.startswith('/') and (a.tree / token).is_file():
            sources.add(token)
out = {
    'scope': 'Build dependency inventory only, not a CVE exemption',
    'config_sha256': hashlib.sha256((a.tree / '.config').read_bytes()).hexdigest(),
    'symvers_sha256': hashlib.sha256((a.tree / 'Module.symvers').read_bytes()).hexdigest(),
    'command_files': commands,
    'source_inputs': sorted(sources),
}
a.output.write_text(json.dumps(out, indent=2) + '\n')
print('Recorded {} dependency files from {} commands'.format(len(sources), commands))
