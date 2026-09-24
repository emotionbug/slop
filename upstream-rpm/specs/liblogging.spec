Name: liblogging
Version: 1.0.8
Release: 1.linuxoss%{?dist}
Summary: liblogging upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://github.com/rsyslog/liblogging
Source0: liblogging-1.0.8.tar.gz
BuildRequires: gcc, make
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n liblogging-1.0.8

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-man-pages
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
/usr/lib64/liblogging-stdlog.so.*
/usr/bin/stdlogctl
%files devel
/usr/include/liblogging/
/usr/lib64/liblogging-stdlog.so
/usr/lib64/pkgconfig/*
