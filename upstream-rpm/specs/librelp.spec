Name: librelp
Version: 1.13.0
Release: 1.linuxoss%{?dist}
Summary: librelp upstream EL8 evaluation build
License: GPLv3+
URL: https://www.rsyslog.com/librelp/
Source0: librelp-1.13.0.tar.gz
BuildRequires: gcc, make, gnutls-devel, openssl-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n librelp-1.13.0

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --enable-tls
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
/usr/lib64/librelp.so.*
%files devel
/usr/include/librelp.h
/usr/lib64/librelp.so
/usr/lib64/pkgconfig/*
