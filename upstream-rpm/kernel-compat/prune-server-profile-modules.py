#!/usr/bin/python3
"""Keep only the target server's reviewed loadable-module closure."""

import argparse
import json
import os
import subprocess
from pathlib import Path


def normalized(name):
    return name.replace('-', '_')


def module_name(path):
    name = path.name
    for suffix in ('.ko.xz', '.ko.gz', '.ko.zst', '.ko'):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    return normalized(name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--release', required=True)
    parser.add_argument('--allowlist', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    args = parser.parse_args()

    module_root = args.root / 'lib/modules' / args.release
    kernel_root = module_root / 'kernel'
    if not kernel_root.is_dir():
        raise SystemExit('missing module tree: {}'.format(kernel_root))

    all_modules = {}
    for path in kernel_root.rglob('*.ko*'):
        all_modules.setdefault(module_name(path), []).append(path)

    requested = []
    for raw in args.allowlist.read_text(encoding='utf-8').splitlines():
        value = raw.split('#', 1)[0].strip()
        if value:
            requested.append(normalized(value))

    missing = sorted(set(requested) - set(all_modules))
    if missing:
        raise SystemExit('allowlisted modules missing: {}'.format(', '.join(missing)))

    subprocess.run(['depmod', '-b', str(args.root), args.release], check=True)
    keep = set()
    dependency_output = {}
    env = dict(os.environ)
    for name in requested:
        result = subprocess.run(
            ['modprobe', '-d', str(args.root), '-S', args.release,
             '--show-depends', name], check=True, universal_newlines=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        dependency_output[name] = result.stdout.splitlines()
        for line in result.stdout.splitlines():
            fields = line.split(None, 1)
            if len(fields) != 2 or fields[0] not in ('insmod', 'install'):
                continue
            candidate = Path(fields[1].split()[0])
            if candidate.name.endswith(('.ko', '.ko.xz', '.ko.gz', '.ko.zst')):
                keep.add(module_name(candidate))

    keep.update(requested)
    removed = []
    kept_paths = []
    for name, paths in sorted(all_modules.items()):
        for path in paths:
            relative = str(path.relative_to(module_root))
            if name in keep:
                kept_paths.append(relative)
            else:
                path.unlink()
                removed.append(relative)

    for directory in sorted(kernel_root.rglob('*'), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()

    order = module_root / 'modules.order'
    if order.exists():
        lines = []
        for raw in order.read_text(encoding='utf-8').splitlines():
            candidate = module_root / raw
            if candidate.exists():
                lines.append(raw)
        order.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')

    subprocess.run(['depmod', '-b', str(args.root), args.release], check=True)
    manifest = {
        'schema_version': 1,
        'release': args.release,
        'policy': 'target-server-runtime-plus-dependency-closure',
        'requested_modules': sorted(set(requested)),
        'kept_module_names': sorted(keep),
        'kept_module_paths': sorted(kept_paths),
        'removed_module_paths': sorted(removed),
        'counts': {
            'requested': len(set(requested)),
            'kept_names': len(keep),
            'kept_paths': len(kept_paths),
            'removed_paths': len(removed),
        },
        'dependency_resolution': dependency_output,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n',
                             encoding='utf-8')
    print(json.dumps(manifest['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
