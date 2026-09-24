%global debug_package %{nil}
Name: openldap
Version: 2.7.1
Release: 1.linuxoss%{?dist}
Summary: openldap upstream EL8 evaluation build
License: OpenLDAP
URL: https://openldap.org/
Source0: openldap-2.7.1.tgz
BuildRequires: gcc, make, openssl-devel, cyrus-sasl-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package clients
Summary: clients files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description clients
clients files.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n openldap-2.7.1

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-slapd --with-tls=openssl --with-cyrus-sasl
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
rm -f %{buildroot}/usr/lib64/*.a
%check
make %{?_smp_mflags} -C tests test

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE
/usr/lib64/libldap.so.*
/usr/lib64/liblber.so.*
%config(noreplace) /etc/openldap/*
/usr/share/man/man5/*
/usr/share/man/man8/*
%files clients
/usr/bin/*
/usr/share/man/man1/*
%files devel
/usr/include/*
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
/usr/share/man/man3/*
