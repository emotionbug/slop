Name: libxml2
Version: 2.15.4
Release: 1.linuxoss%{?dist}
Summary: libxml2 upstream EL8 evaluation build
License: MIT
URL: https://gitlab.gnome.org/GNOME/libxml2
Source0: libxml2-2.15.4.tar.xz
BuildRequires: gcc, make, zlib-devel, xz-devel
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
%setup -q -n libxml2-2.15.4

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --without-python
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
%license Copyright
/usr/lib64/libxml2.so.*
/usr/bin/*

%files devel
/usr/include/*
/usr/lib64/pkgconfig/*
/usr/lib64/libxml2.so
/usr/lib64/cmake/*
