BuildRequires: polkit-devel
Name: NetworkManager
Epoch: 1
Version: 1.58.1
Release: 1.linuxoss%{?dist}
Summary: NetworkManager upstream EL8 evaluation build
License: GPLv2+ and LGPLv2+
URL: https://networkmanager.dev/
Source0: NetworkManager-1.58.1.tar.xz
BuildRequires: linuxoss-kernel-uapi, gcc, ninja-build, glib2-devel, libnl3-devel, libndp-devel, newt-devel, libcurl-devel, libselinux-devel, audit-libs-devel, systemd-devel, gnutls-devel, readline-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libnm
Summary: libnm files
%description libnm
libnm files.

%package tui
Summary: tui files
%description tui
tui files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%if 0%{?reuse_prepared}
%setup -q -D -T -n NetworkManager-1.58.1
%else
%setup -q -n NetworkManager-1.58.1
%endif
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2 -I/opt/linux-oss/kernel-uapi-7.2.7/include'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup %{?reuse_prepared:--reconfigure} build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Dintrospection=false -Ddocs=false -Dppp=false -Dwifi=false -Dmodem_manager=false -Dbluez5_dun=false -Dlibpsl=false -Dcrypto=gnutls -Dsession_tracking=systemd -Dsystem_ca_path=/etc/pki/tls/certs -Dtests=yes -Dclat=false -Dnbft=false
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3

%post libnm -p /sbin/ldconfig
%postun libnm -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/nmcli
/usr/bin/nm-online
/usr/libexec/*
/usr/share/bash-completion/*
/usr/share/doc/NetworkManager/*
/usr/share/man/*/*
/usr/sbin/*
/usr/lib/NetworkManager/
/usr/lib/firewalld/zones/nm-shared.xml
/usr/lib64/NetworkManager/
/usr/lib/systemd/*
/usr/lib/udev/*
/usr/share/dbus-1/*
/usr/share/polkit-1/*
/usr/share/locale/*/LC_MESSAGES/NetworkManager.mo
%config(noreplace) /etc/*
%files libnm
/usr/lib64/libnm.so.*
%files tui
/usr/bin/nmtui*
%files devel
/usr/include/libnm/
/usr/lib64/libnm.so
/usr/lib64/pkgconfig/*
