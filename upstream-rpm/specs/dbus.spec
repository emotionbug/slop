Name: dbus
Version: 1.16.2
Epoch: 1
Release: 1.linuxoss%{?dist}
Summary: dbus upstream EL8 evaluation build
License: AFL and GPLv2+
URL: https://dbus.freedesktop.org/
Source0: dbus-1.16.2.tar.xz
BuildRequires: gcc, ninja-build, expat-devel, glib2-devel, libselinux-devel, systemd-devel, audit-libs-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package common
Summary: common files
%description common
common files.

%package daemon
Summary: daemon files
%description daemon
daemon files.

%package libs
Summary: libs files
%description libs
libs files.

%package tools
Summary: tools files
%description tools
tools files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n dbus-1.16.2
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Ddoxygen_docs=disabled -Dducktype_docs=disabled -Dxml_docs=disabled -Dmodular_tests=enabled -Dx11_autolaunch=disabled -Dsystemd=enabled -Dselinux=enabled -Ddbus_user=dbus -Druntime_dir=/run
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
find %{buildroot}/usr/share/doc -type f -name '*.py' -exec chmod 0644 {} +
%check
meson test -C build --print-errorlogs --num-processes 2

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license COPYING
%files common
/usr/share/dbus-1/
/usr/share/xml/dbus-1/
/etc/dbus-1/
/usr/share/doc/dbus/
%files daemon
/usr/bin/dbus-daemon
/usr/libexec/dbus-daemon-launch-helper
/usr/lib/systemd/
/usr/lib/sysusers.d/dbus.conf
/usr/lib/tmpfiles.d/dbus.conf
%files libs
/usr/lib64/libdbus-1.so.*
%files tools
/usr/bin/dbus-*
%exclude /usr/bin/dbus-daemon
%files devel
/usr/include/dbus-1.0/
/usr/lib64/dbus-1.0/
/usr/lib64/libdbus-1.so
/usr/lib64/pkgconfig/*
/usr/lib64/cmake/DBus1/
