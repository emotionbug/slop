Name: efivar
Version: 39
Release: 1.linuxoss%{?dist}
Summary: efivar upstream EL8 evaluation build
License: LGPLv2+
URL: https://github.com/rhboot/efivar
Source0: efivar-39.tar.gz
BuildRequires: gcc, make, popt-devel, libuuid-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package devel
Summary: devel files
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n efivar-39
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

make %{?_smp_mflags} ENABLE_DOCS=0 LIBDIR=/usr/lib64
%install
make DESTDIR=%{buildroot} prefix=/usr libdir=/usr/lib64 LIBDIR=/usr/lib64 ENABLE_DOCS=0 install
rm -f %{buildroot}/usr/lib64/*.a
%check
make ENABLE_DOCS=0 test

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/*
%files libs
/usr/lib64/libefi*.so.*
%files devel
/usr/include/efivar/
/usr/lib64/libefi*.so
/usr/lib64/pkgconfig/*
