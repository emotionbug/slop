"""Normalize only the disposable VM identity and its fixture BLS entries."""
from pathlib import Path
import subprocess

state=Path('/var/lib/linuxoss-fixture')
assert (state/'old-kernel').is_file()
assert Path('/etc/hostname').read_text().strip()=='linuxoss-kernel-fixture'
machine='112233445566778899aabbccddeeff00'
assert len(machine)==32
Path('/etc/machine-id').write_text(machine+'\n')
for path in Path('/boot/loader/entries').glob('*.conf'):
    lines=path.read_text().splitlines()
    linux=next(line.split(None,1)[1] for line in lines if line.startswith('linux '))
    kver=linux.split('/vmlinuz-',1)[1]
    entry_id=machine+'-'+kver
    new=path.with_name(entry_id+'.conf')
    text='\n'.join('id '+entry_id if line.startswith('id ') else line for line in lines)+'\n'
    if new != path:
        assert not new.exists()
        path.rename(new)
    new.write_text(text)
subprocess.check_call(['grub2-editenv','-','set','saved_entry='+machine+'-'+(state/'old-kernel').read_text().strip()])
subprocess.check_call(['grub2-editenv','-','unset','next_entry'])
