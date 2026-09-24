Name: iscsi-initiator-utils
Version: 2.1.13
Release: 1.linuxoss%{?dist}
Summary: iscsi-initiator-utils upstream EL8 evaluation build
License: GPLv2+
URL: https://github.com/open-iscsi/open-iscsi
Source0: open-iscsi-2.1.13.tar.gz
BuildRequires: gcc, ninja-build, systemd-devel, libmount-devel, openssl-devel, kmod-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package iscsiuio
Summary: iscsiuio files
%description iscsiuio
iscsiuio files.

%package devel
Summary: Open iSCSI development files
%description devel
Development headers.

%prep
%setup -q -n open-iscsi-2.1.13
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --wrap-mode=nodownload -Disns=disabled
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs
LD_LIBRARY_PATH=%{buildroot}/usr/lib64 %{buildroot}/usr/sbin/iscsiadm --version

%files
%license README
/usr/sbin/*
%exclude /usr/sbin/iscsiuio
/usr/lib/systemd/*
/usr/share/man/*/*
%config(noreplace) /etc/iscsi/*
/usr/lib64/libopeniscsiusr.so.*
%config(noreplace) /etc/udev/rules.d/*
%files iscsiuio
/usr/sbin/iscsiuio

%config(noreplace) /etc/logrotate.d/iscsiuiolog
%files devel
/usr/include/libopeniscsiusr*
/usr/lib64/libopeniscsiusr.so
/usr/lib64/pkgconfig/*
