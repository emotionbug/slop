import json, subprocess, sys
from pathlib import Path

paths = ['ld-linux-x86-64.so.2', 'libc.so.6', 'libm.so.6', 'libpthread.so.0',
         'libdl.so.2', 'librt.so.1', 'libresolv.so.2', 'libnss_dns.so.2', 'libnss_files.so.2']
result = {}
for name in paths:
    text = subprocess.check_output(['readelf', '--dyn-syms', '--wide', '/lib64/' + name], universal_newlines=True)
    symbols = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 8 or fields[6] in ('UND', 'ABS') or not fields[0].endswith(':'):
            continue
        typ, binding, visibility, symbol = fields[3], fields[4], fields[5], fields[7]
        if binding not in ('GLOBAL', 'WEAK'):
            continue
        symbols[symbol] = [typ, binding, visibility, int(fields[2]) if typ in ('OBJECT', 'TLS') else None]
    result[name] = symbols
out = Path('/out')
if sys.argv[1] == 'before':
    (out / 'glibc-exports-before.json').write_text(json.dumps(result, indent=2))
else:
    old = json.loads((out / 'glibc-exports-before.json').read_text())
    changes = {name: {sym: [details, result[name].get(sym)] for sym, details in symbols.items()
                      if result[name].get(sym) != details} for name, symbols in old.items()}
    (out / 'glibc-abi-comparison.json').write_text(json.dumps(changes, indent=2))
    assert not any(changes.values()), changes
    print('GLIBC_EXPORT_ABI_PASSED', sum(len(x) for x in result.values()), 'symbols', len(paths), 'libraries')
