Name: libsoup3
Version: 3.6.6
Release: 1.linuxoss%{?dist}
Summary: libsoup3 upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://gitlab.gnome.org/GNOME/libsoup
Source0: libsoup-3.6.6.tar.xz
BuildRequires: gcc, ninja-build, glib2-devel, libnghttp2-devel, sqlite-devel, brotli-devel, krb5-devel, libpsl-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n libsoup-3.6.6
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Dintrospection=disabled -Dvapi=disabled -Ddocs=disabled -Dsysprof=disabled -Dtls_check=false -Dpkcs11_tests=disabled -Dautobahn=disabled
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/lib64/libsoup-3.0.so.*
/usr/share/locale/*/LC_MESSAGES/libsoup-3.0.mo
%files devel
/usr/include/libsoup-3.0/
/usr/lib64/libsoup-3.0.so
/usr/lib64/pkgconfig/*
