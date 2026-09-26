%define debug_package %{nil}
%define __spec_install_post %{nil}
%global krel 4.18.0-553.168.1.linuxoss1.el8_10.x86_64
%global source_dir linux-4.18.0-553.168.1.el8_10
%{!?linuxoss_tree:%global linuxoss_tree %{_builddir}/%{source_dir}}

Name: kernel-linuxoss-el8-compat
Version: 4.18.0
Release: 553.168.1.linuxoss1.el8_10
Summary: EL8 .168 kernel with NFQUEUE ABI preservation (evaluation)
License: GPLv2
URL: https://github.com/emotionbug/slop/tree/main/upstream-rpm/kernel-compat
Vendor: Linux OSS local build
Source0: linux-4.18.0-553.168.1.el8_10.tar.xz
Source1: kernel-compat.config
Patch0: el8-168-nfqueue-kabi.patch
BuildRequires: gcc, make, binutils >= 2.30, binutils < 2.31, bc, bison, flex, elfutils-libelf-devel
BuildRequires: openssl-devel, perl, dwarves, python3, cpio, xz
Requires: kmod
Provides: kernel-uname-r = %{krel}
Provides: installonlypkg(kernel)
ExclusiveArch: x86_64

%description
Parallel, locally built EL8 kernel. Keeps the old NFQUEUE public structure
layout while retaining the saved-device reference fix in private tail storage.
Installation stages kernel files only. It does not generate an initramfs,
select a boot entry, reboot, or certify third-party security agents.

%package devel
Summary: Module development files for the Linux OSS EL8 compatibility kernel
AutoReqProv: no
Requires: make, gcc, /usr/bin/perl, elfutils-libelf-devel

%description devel
Headers, generated configuration, host tools and exported symbol versions for
this exact kernel. This does not replace the system kernel-headers package.

%prep
%if 0%{?linuxoss_payload_repack}
test -s %{linuxoss_payload_tar}
%else
%if 0%{?linuxoss_prebuilt}
test -f %{linuxoss_tree}/vmlinux
test -f %{linuxoss_tree}/Module.symvers
cmp %{SOURCE1} %{linuxoss_tree}/.config
%else
%setup -q -n %{source_dir}
%patch0 -p1
cp %{SOURCE1} .config
%endif
%endif

%build
%if !0%{?linuxoss_payload_repack}
cd %{linuxoss_tree}
test "$(make -s kernelrelease)" = '%{krel}'
%if !0%{?linuxoss_prebuilt}
make olddefconfig
make %{?_smp_mflags} KCFLAGS=-gz=zlib-gnu bzImage modules
%endif
%endif

%install
%if 0%{?linuxoss_payload_repack}
mkdir -p %{buildroot}
tar xf %{linuxoss_payload_tar} -C %{buildroot}
%else
cd %{linuxoss_tree}
mkdir -p %{buildroot}/boot
install -m 0644 arch/x86/boot/bzImage %{buildroot}/boot/vmlinuz-%{krel}
install -m 0644 System.map %{buildroot}/boot/System.map-%{krel}
install -m 0644 .config %{buildroot}/boot/config-%{krel}
make INSTALL_MOD_PATH=%{buildroot} INSTALL_MOD_STRIP=1 modules_install
devel=%{buildroot}/usr/src/kernels/%{krel}
mkdir -p "$devel"
tar cf - Makefile Makefile.rhelver Kconfig .config Module.symvers System.map include scripts arch/x86/include arch/x86/Makefile arch/x86/Makefile_32.cpu arch/x86/Kbuild arch/x86/Kconfig arch/x86/Kconfig.cpu tools/objtool/objtool tools/bpf/resolve_btfids/resolve_btfids | tar xf - -C "$devel"
rm -f %{buildroot}/lib/modules/%{krel}/build %{buildroot}/lib/modules/%{krel}/source
ln -s /usr/src/kernels/%{krel} %{buildroot}/lib/modules/%{krel}/build
ln -s /usr/src/kernels/%{krel} %{buildroot}/lib/modules/%{krel}/source
find "$devel" -name '*.o' -delete
%endif

%post
/usr/sbin/depmod -a %{krel}

%preun
if [ "$1" = 0 ] && [ "$(uname -r)" = '%{krel}' ]; then
    echo 'Refusing to remove the running kernel' >&2
    exit 1
fi

%files
/boot/vmlinuz-%{krel}
/boot/System.map-%{krel}
/boot/config-%{krel}
%dir /lib/modules/%{krel}
/lib/modules/%{krel}/kernel
/lib/modules/%{krel}/modules.order
/lib/modules/%{krel}/modules.builtin
# depmod regenerates these when an external security module is installed.
# Their contents are not immutable kernel payloads.
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.alias
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.alias.bin
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.builtin.bin
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.dep
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.dep.bin
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.devname
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.softdep
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.symbols
%ghost %attr(0644,root,root) /lib/modules/%{krel}/modules.symbols.bin

%files devel
/usr/src/kernels/%{krel}
/lib/modules/%{krel}/build
/lib/modules/%{krel}/source
%if 0%{?linuxoss_payload_repack}
%dir /usr/lib/.build-id/*
%endif
