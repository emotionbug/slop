#!/usr/bin/env python3
"""Check the actual 7.2.7 SMB function, without altering kernel source."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
source = args.source / 'fs/smb/client/smb2inode.c'
text = source.read_text()
start = text.index('static struct reparse_data_buffer *reparse_buf_ptr(')
end = text.index('\n}\n', start) + 3
function = text[start:end]
early_check = ('\tif (count < len)\n'
               '\t\treturn ERR_PTR(smb_EIO2(smb_eio_trace_reparse_rdlen, count, 0));\n')
read_length = '\trdlen = le16_to_cpu(buf->ReparseDataLength);'
assert function.count(early_check) == 1
assert function.index(early_check) < function.index(read_length)
assert 'if (count < rdlen + len)' in function
args.output.mkdir(parents=True, exist_ok=False)
harness = Path(__file__).with_suffix('.c')
logs = []
for variant, code in [('fixed', function), ('vulnerable-control', function.replace(early_check, ''))]:
    folder = args.output / variant
    folder.mkdir()
    (folder / 'smb-reparse-extracted.h').write_text(code)
    exe = folder / 'test'
    command = ['gcc-15', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(folder), str(harness), '-o', str(exe)]
    if variant == 'vulnerable-control':
        command.insert(1, '-DNEGATIVE_CONTROL')
        command[2] = '-O0'
    subprocess.run(command, check=True)
    logs.append(subprocess.check_output([str(exe)], text=True).strip())
result = {'cve': 'CVE-2026-89632', 'source_file': 'fs/smb/client/smb2inode.c',
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'tested_function_sha256': hashlib.sha256(function.encode()).hexdigest(),
          'tests': logs, 'kernel_source_modified': False,
          'scope': 'Actual source function with type/trace shims; not a live SMB transport or whole-kernel test.'}
(args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
