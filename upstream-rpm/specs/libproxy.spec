Name: libproxy
Version: 0.5.12
Release: 1.linuxoss%{?dist}
Summary: libproxy upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://github.com/libproxy/libproxy
Source0: libproxy-0.5.12.tar.gz
BuildRequires: gcc, ninja-build, glib2-devel, libcurl-devel, duktape-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n libproxy-0.5.12
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Dintrospection=false -Dvapi=false -Ddocs=false -Drelease=true
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/*
/usr/lib64/libproxy.so.*
/usr/lib64/libproxy/
/usr/share/man/man8/*
%files devel
/usr/include/*
/usr/lib64/libproxy.so
/usr/lib64/libproxy.a
/usr/lib64/pkgconfig/*
