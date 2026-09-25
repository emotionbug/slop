"""Boot only a newly created, disposable EL8 disk in unprivileged QEMU/TCG."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import time
import urllib.request

assert os.geteuid() != 0
assert Path('/run/.containerenv').exists() or Path('/.dockerenv').exists()
out=Path('/next/'+os.environ.get('VALIDATION_DIR','boot-validation'))
baseout=out
attempt=0
while out.exists():
    attempt+=1
    out=baseout.with_name(baseout.name+'-retry'+str(attempt))
out.mkdir(exist_ok=False)
print('Validation output: '+str(out), flush=True)
resume=os.environ.get('RESUME_DISK')=='1'
work=Path('/tmp/kernel-el8-fixture');work.mkdir(exist_ok=resume)
disk=work/'el8.qcow2'
if not resume:
    subprocess.run(['qemu-img','create','-f','qcow2',str(disk),'10G'],check=True)
commands='''run
part-init /dev/sda gpt
part-add /dev/sda p 2048 264191
part-set-gpt-type /dev/sda 1 C12A7328-F81F-11D2-BA4B-00A0C93EC93B
part-add /dev/sda p 264192 2361343
part-add /dev/sda p 2361344 -34
pvcreate /dev/sda3
vgcreate linuxoss /dev/sda3
lvcreate-free root linuxoss 100
mkfs vfat /dev/sda1 label:EFI
mkfs ext4 /dev/sda2 label:BOOT features:^metadata_csum_seed,^orphan_file
debug sh "/sbin/mkfs.xfs -f -m crc=1,bigtime=0,inobtcount=0,reflink=0 -i sparse=0 /dev/linuxoss/root"
mount /dev/linuxoss/root /
mkdir-p /boot
mount /dev/sda2 /boot
mkdir-p /boot/efi
mount /dev/sda1 /boot/efi
tar-in /next/guest-root.tar / xattrs:true selinux:true
-rm /run/.containerenv
-rm /.dockerenv
write /etc/hostname "linuxoss-kernel-fixture\\n"
write /etc/hosts "127.0.0.1 localhost linuxoss-kernel-fixture\\n"
command "/sbin/setfiles -F -e /proc -e /sys -e /dev -e /run -e /boot/efi /etc/selinux/targeted/contexts/files/file_contexts /"
sync
umount-all
'''
if resume:
    commands='''run
mount /dev/linuxoss/root /
mount /dev/sda2 /boot
mount /dev/sda1 /boot/efi
command "/sbin/setfiles -F -e /proc -e /sys -e /dev -e /run -e /boot/efi /etc/selinux/targeted/contexts/files/file_contexts /"
sync
umount-all
'''
(out/'guestfish-commands.txt').write_text(commands)
if os.environ.get('SKIP_RELABEL') != '1':
    with (out/'disk-create.log').open('w') as log:
        p=subprocess.run(['guestfish','--rw','-a',str(disk)],input=commands,universal_newlines=True,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    assert p.returncode==0, 'guestfish: see disk-create.log'
# OVMF lacks VMware firmware's PVSCSI boot driver. Put only EFI and /boot on
# a virtio disk; keep the root LVM/XFS volume on PVSCSI for the real driver test.
bootdisk=work/'boot.qcow2'
if not bootdisk.exists():
    subprocess.run(['qemu-img','create','-f','qcow2',str(bootdisk),'1300M'],check=True)
    split='''run
part-init /dev/sdb gpt
part-add /dev/sdb p 2048 264191
part-set-gpt-type /dev/sdb 1 C12A7328-F81F-11D2-BA4B-00A0C93EC93B
part-add /dev/sdb p 264192 2361343
copy-device-to-device /dev/sda1 /dev/sdb1
copy-device-to-device /dev/sda2 /dev/sdb2
part-del /dev/sda 2
part-del /dev/sda 1
sync
'''
    with (out/'boot-disk-create.log').open('w') as log:
        p=subprocess.run(['guestfish','--rw','-a',str(disk),'-a',str(bootdisk)],input=split,universal_newlines=True,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    assert p.returncode==0, 'guestfish boot split failed'
# Container kernel scriptlets need not populate /boot. Copy the distribution
# fixture image explicitly and supply the serial-only BLS helper function.
repair='''run
mount /dev/linuxoss/root /
mount /dev/sdb2 /boot
mount /dev/sdb1 /boot/efi
'''
if os.environ.get('KIT_TAR'):
    kit_tar=Path(os.environ['KIT_TAR'])
    assert kit_tar.parent==Path('/next') and kit_tar.is_file()
    repair+='rm-rf /opt/kernel-fixture/kit\nmkdir /opt/kernel-fixture/kit\ntar-in '+str(kit_tar)+' /opt/kernel-fixture/kit\n'
repair+='''
sh "old=$(cat /var/lib/linuxoss-fixture/old-kernel); cp /lib/modules/$old/vmlinuz /boot/vmlinuz-$old"
sh "sed -i '/^function load_video /d' /boot/efi/EFI/rocky/grub.cfg /boot/efi/EFI/BOOT/grub.cfg"
sh "sed -i '1i function load_video { set linuxoss_video=serial; }' /boot/efi/EFI/rocky/grub.cfg /boot/efi/EFI/BOOT/grub.cfg"
command "/usr/bin/systemctl unmask systemd-remount-fs.service systemd-logind.service dbus-org.freedesktop.login1.service"
upload /recipe/fixture-run.sh /usr/local/sbin/linuxoss-kernel-fixture
upload /recipe/kernel.py /opt/kernel-fixture/kit/kernel.py
upload /recipe/fixture-repair.py /opt/kernel-fixture/fixture-repair.py
command "/usr/libexec/platform-python /opt/kernel-fixture/fixture-repair.py"
sh "cd /opt/kernel-fixture/kit && sha256sum kernel.py kernel.sh kernel-manifest.json rpms/*.rpm > SHA256SUMS"
command "/sbin/setfiles -F -e /boot/efi /etc/selinux/targeted/contexts/files/file_contexts /boot"
sync
umount-all
'''
with (out/'boot-repair.log').open('w') as log:
    p=subprocess.run(['guestfish','--rw','-a',str(disk),'-a',str(bootdisk)],input=repair,universal_newlines=True,stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0, 'fixture boot repair failed'
shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd',work/'vars.fd')
key=work/'fixture-key';shutil.copyfile('/next/fixture-key',key);key.chmod(0o600)
ssh=['ssh','-i',str(key),'-p','2222','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','-o','ConnectTimeout=3','root@127.0.0.1']
markers=['KERNEL_EL8_INSTALL_AND_BOOT_ONCE_PASSED','KERNEL_EL8_UEFI_LVM_XFS_SSH_JAVA_SELINUX_NFT_PASSED','KERNEL_EL8_OLD_DEFAULT_BOOT_PASSED']
results=[]
for phase,marker in enumerate(markers):
    path=out/('boot-'+str(phase)+'.log');verified=False
    cmd=['qemu-system-x86_64','-accel','tcg','-machine','q35,smm=on','-cpu','max','-smp','2','-m','3072',
         '-global','driver=cfi.pflash01,property=secure,value=on',
         '-nodefaults','-display','none','-monitor','none','-serial','stdio','-no-reboot',
         '-drive','if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd',
         '-drive','if=pflash,format=raw,file='+str(work/'vars.fd'),
         '-drive','file='+str(bootdisk)+',if=none,id=boot0,format=qcow2',
         '-device','virtio-blk-pci,drive=boot0,bootindex=1',
         '-device','pvscsi,id=scsi0','-drive','file='+str(disk)+',if=none,id=disk0,format=qcow2',
         '-device','scsi-hd,drive=disk0,bus=scsi0.0',
         '-netdev','user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22,hostfwd=tcp:127.0.0.1:18080-:8080',
         '-device','vmxnet3,netdev=net0']
    with path.open('w') as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+1200
            while p.poll() is None:
                if time.monotonic()>deadline:
                    raise TimeoutError('Guest phase '+str(phase))
                if phase==1 and not verified and 'KERNEL_EL8_WAITING_HOST_SSH_HTTP' in path.read_text(errors='replace'):
                    response=urllib.request.urlopen('http://127.0.0.1:18080',timeout=5).read()
                    assert response==b'JAVA8_KERNEL_HTTP_OK\n'
                    check=subprocess.run(ssh+['uname -r; touch /var/lib/linuxoss-fixture/host-verified'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=15)
                    (out/'host-ssh-http.log').write_text(check.stdout)
                    assert check.returncode==0 and '7.2.7-linuxoss+' in check.stdout
                    verified=True
                time.sleep(2)
        finally:
            if p.poll() is None:
                p.terminate();p.wait(timeout=10)
    text=path.read_text(errors='replace')
    result={'phase':phase,'exit_code':p.returncode,'marker':marker,'passed':p.returncode==0 and marker in text and 'KERNEL_EL8_FIXTURE_FAILED' not in text}
    results.append(result);(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    assert result['passed'], 'See '+str(path)
with (out/'guest-logs-extract.log').open('w') as log:
    p=subprocess.run(['guestfish','--ro','-a',str(disk),'-m','/dev/linuxoss/root','tar-out','/var/log/linuxoss-kernel',str(out/'installer-logs.tar.gz'),'compress:gzip'],stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0
print('EL8_KERNEL_BOOT_INSTALL_NETWORK_JAVA_FALLBACK_PASSED',flush=True)
