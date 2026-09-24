Name: libndp
Version: 1.9
Release: 1.linuxoss%{?dist}
Summary: libndp upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://github.com/jpirko/libndp
Source0: libndp-1.9.tar.gz
BuildRequires: gcc, make, autoconf, automake, libtool
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n libndp-1.9
ACLOCAL_PATH=/usr/share/aclocal autoreconf -fi
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/ndptool
/usr/lib64/libndp.so.*
/usr/share/man/man8/*
%files devel
/usr/include/ndp.h
/usr/lib64/libndp.so
/usr/lib64/pkgconfig/*
