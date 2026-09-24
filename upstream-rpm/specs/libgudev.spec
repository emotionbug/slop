Name: libgudev
Version: 238
Release: 1.linuxoss%{?dist}
Summary: libgudev upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://gitlab.gnome.org/GNOME/libgudev
Source0: libgudev-238.tar.xz
BuildRequires: gcc, ninja-build, glib2-devel, systemd-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n libgudev-238
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --wrap-mode=nodownload -Dintrospection=disabled -Dvapi=disabled -Dtests=auto
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs
test -f build/gudev/libgudev-1.0.so.0.3.0

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/lib64/libgudev-1.0.so.*
%files devel
/usr/include/gudev-1.0/
/usr/lib64/libgudev-1.0.so
/usr/lib64/pkgconfig/*
