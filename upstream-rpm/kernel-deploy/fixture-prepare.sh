#!/usr/bin/env bash
# Prepare only the named disposable EL8 container before exporting its rootfs.
set -Eeuo pipefail
[[ -f /run/.containerenv && $EUID == 0 && -d /next/install-kit ]] || exit 2
mkdir -p /opt/kernel-fixture /var/lib/linuxoss-fixture /root/.ssh /boot/loader/entries /boot/efi/EFI/BOOT
cp -a /next/install-kit /opt/kernel-fixture/kit
cp /recipe/fixture-run.sh /usr/local/sbin/linuxoss-kernel-fixture
chmod 755 /usr/local/sbin/linuxoss-kernel-fixture
cp /next/fixture-key.pub /root/.ssh/authorized_keys
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys
# An unlocked test-only root account accepts the ephemeral SSH public key.
# Password login remains disabled. The test key is never shipped in a release.
usermod -p '*' root
printf '%s\n' '112233445566778899aabbccddeeff00' > /etc/machine-id
printf '%s\n' 'linuxoss-kernel-fixture' > /etc/hostname
printf '%s\n' '127.0.0.1 localhost linuxoss-kernel-fixture' > /etc/hosts
cat > /etc/fstab <<'EOF'
/dev/mapper/linuxoss-root / xfs defaults 0 0
LABEL=BOOT /boot ext4 defaults 0 2
LABEL=EFI /boot/efi vfat umask=0077 0 2
EOF
cat > /etc/default/grub <<'EOF'
GRUB_TIMEOUT=1
GRUB_DEFAULT=saved
GRUB_ENABLE_BLSCFG=true
GRUB_TERMINAL=serial
GRUB_SERIAL_COMMAND="serial --unit=0 --speed=115200"
GRUB_CMDLINE_LINUX="root=/dev/mapper/linuxoss-root ro rd.lvm.lv=linuxoss/root console=ttyS0,115200 net.ifnames=0 biosdevname=0"
EOF
cat > /etc/ssh/sshd_config <<'EOF'
Port 22
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
UsePAM yes
AuthorizedKeysFile .ssh/authorized_keys
Subsystem sftp /usr/libexec/openssh/sftp-server
EOF
ssh-keygen -A
sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config
cat > /opt/kernel-fixture/KernelHttp.java <<'EOF'
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.file.*;
public class KernelHttp {
 public static void main(String[] args) throws Exception {
  HttpServer h=HttpServer.create(new InetSocketAddress(8080),0);
  h.createContext("/", e -> {byte[] b="JAVA8_KERNEL_HTTP_OK\n".getBytes("UTF-8");e.sendResponseHeaders(200,b.length);e.getResponseBody().write(b);e.close();});
  h.start();
 }
}
EOF
javac /opt/kernel-fixture/KernelHttp.java
cat > /etc/systemd/system/linuxoss-fixture-network.service <<'EOF'
[Unit]
After=systemd-udev-settle.service
Wants=systemd-udev-settle.service
Before=sshd.service firewalld.service linuxoss-fixture-java.service
[Service]
Type=oneshot
ExecStart=/usr/sbin/ip link set eth0 up
ExecStart=/usr/sbin/ip addr add 10.0.2.15/24 dev eth0
ExecStart=/usr/sbin/ip route add default via 10.0.2.2
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/linuxoss-fixture-java.service <<'EOF'
[Unit]
After=linuxoss-fixture-network.service
[Service]
Type=simple
ExecStart=/usr/bin/java -cp /opt/kernel-fixture KernelHttp
User=nobody
Restart=no
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/linuxoss-kernel-fixture.service <<'EOF'
[Unit]
After=sshd.service firewalld.service linuxoss-fixture-java.service
Wants=sshd.service firewalld.service linuxoss-fixture-java.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/linuxoss-kernel-fixture
StandardOutput=journal+console
StandardError=journal+console
TimeoutStartSec=20min
[Install]
WantedBy=multi-user.target
EOF
systemctl unmask systemd-remount-fs.service systemd-logind.service dbus-org.freedesktop.login1.service
systemctl enable sshd firewalld linuxoss-fixture-network linuxoss-fixture-java linuxoss-kernel-fixture
systemctl set-default multi-user.target
firewall-offline-cmd --add-port=8080/tcp
old=$(rpm -q kernel-core --qf '%{VERSION}-%{RELEASE}.%{ARCH}\n' | head -n1)
printf '%s\n' "$old" > /var/lib/linuxoss-fixture/old-kernel
cp "/lib/modules/$old/vmlinuz" "/boot/vmlinuz-$old"
depmod "$old"
dracut --force --no-hostonly --omit 'fips' --kver "$old" --add 'lvm' --add-drivers 'vmw_pvscsi vmxnet3 sd_mod xfs dm_mod ext4 vfat' "/boot/initramfs-$old.img"
cat > "/boot/loader/entries/112233445566778899aabbccddeeff00-$old.conf" <<EOF
title EL8 fixture fallback
version $old
linux /vmlinuz-$old
initrd /initramfs-$old.img
options root=/dev/mapper/linuxoss-root ro rd.lvm.lv=linuxoss/root console=ttyS0,115200 net.ifnames=0 biosdevname=0
id 112233445566778899aabbccddeeff00-$old
EOF
grub2-editenv - create
grub2-editenv - set "saved_entry=112233445566778899aabbccddeeff00-$old" 'kernelopts=root=/dev/mapper/linuxoss-root ro rd.lvm.lv=linuxoss/root console=ttyS0,115200 net.ifnames=0 biosdevname=0'
cp /boot/efi/EFI/rocky/grubx64.efi /boot/efi/EFI/BOOT/BOOTX64.EFI
# Native EL8 grub BLS and grubenv, selected through a removable-media EFI path.
cat > /boot/efi/EFI/rocky/grub.cfg <<'EOF'
function load_video { set linuxoss_video=serial; }
serial --unit=0 --speed=115200
terminal_input serial
terminal_output serial
search --no-floppy --label BOOT --set=root
set prefix=($root)/grub2
load_env -f ($root)/efi/EFI/rocky/grubenv
if [ "${next_entry}" ]; then
 set default="${next_entry}"
 set next_entry=
 save_env -f ($root)/efi/EFI/rocky/grubenv next_entry
 set boot_once=true
else
 set default="${saved_entry}"
fi
set timeout=1
insmod blscfg
blscfg
EOF
# EFI is mounted separately: GRUB uses its own device for the persistent env.
sed -i 's|load_env -f ($root)/efi/EFI/rocky/grubenv|search --no-floppy --label EFI --set=efidev\nload_env -f ($efidev)/EFI/rocky/grubenv|;s|save_env -f ($root)/efi/EFI/rocky/grubenv|save_env -f ($efidev)/EFI/rocky/grubenv|' /boot/efi/EFI/rocky/grub.cfg
cp /boot/efi/EFI/rocky/grub.cfg /boot/efi/EFI/BOOT/grub.cfg
# Exported container markers would incorrectly identify the VM as a container.
rm -f /.dockerenv /etc/hostname.rpmnew
# /run/.containerenv is a Podman bind mount; remove any exported marker later
# through guestfish inside the disposable disk image.
echo FIXTURE_ROOT_PREPARED
