%global debug_package %{nil}
%global __strip /bin/true
%global prefix /opt/linux-oss/grub-2.14
Name: linuxoss-grub2-evaluation
Version: 2.14
Release: 1.linuxoss%{?dist}
Summary: Private unsigned GRUB EFI tools and modules for offline evaluation
License: GPLv3+
URL: https://www.gnu.org/software/grub/
Source0: grub-2.14.tar.xz
BuildRequires: gcc, make, bison, flex, gettext, freetype-devel, libtasn1-devel, device-mapper-devel
Vendor: Linux OSS local build
%description
Private unsigned EFI build. Does not install a bootloader, write EFI variables,
alter boot configuration or claim Secure Boot compatibility.
%prep
%setup -q -n grub-2.14
%build
CC=/usr/bin/gcc ./configure --prefix=%{prefix} --libdir=%{prefix}/lib64 --sysconfdir=%{prefix}/etc --target=x86_64 --with-platform=efi --disable-werror
make -j2
%install
make DESTDIR=%{buildroot} install
%check
# Offline image construction and parser checks; boot and Secure Boot remain untested.
./grub-mkimage -d grub-core -O x86_64-efi -p /boot/grub -o evaluation.efi normal configfile linux
test -s evaluation.efi
printf 'set timeout=5\nmenuentry "test" { echo test; }\n' > evaluation.cfg
./grub-script-check evaluation.cfg
%files
%license COPYING
%{prefix}/
