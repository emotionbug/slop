Name: net-snmp
Epoch: 1
Version: 5.9.5.2
Release: 1.linuxoss%{?dist}
Summary: net-snmp upstream EL8 evaluation build
License: BSD
URL: https://www.net-snmp.org/
Source0: net-snmp-5.9.5.2.tar.gz
BuildRequires: gcc, make, linuxoss-openssl4, libnl3-devel, rpm-devel, lm_sensors-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package agent-libs
Summary: agent-libs files
%description agent-libs
agent-libs files.

%package utils
Summary: utils files
%description utils
utils files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n net-snmp-5.9.5.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-L/opt/linux-oss/openssl-4.0.2/lib64 -Wl,-rpath,/opt/linux-oss/openssl-4.0.2/lib64 -Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-default-snmp-version=3 --with-sys-contact=root@localhost --with-sys-location=unspecified --with-logfile=/var/log/snmpd.log --with-persistent-directory=/var/lib/net-snmp --with-openssl=/opt/linux-oss/openssl-4.0.2 --disable-embedded-perl --without-perl-modules
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make test

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%post agent-libs -p /sbin/ldconfig
%postun agent-libs -p /sbin/ldconfig

%files
%license COPYING
/usr/sbin/*
/usr/share/snmp/
/usr/share/man/man5/*
/usr/share/man/man8/*
%files libs
/usr/lib64/libnetsnmp.so.*
/usr/lib64/libnetsnmphelpers.so.*
%files agent-libs
/usr/lib64/libnetsnmpagent.so.*
/usr/lib64/libnetsnmpmibs.so.*
/usr/lib64/libnetsnmptrapd.so.*
%files utils
/usr/bin/*
%exclude /usr/bin/net-snmp-config
/usr/share/man/man1/*
%files devel
/usr/include/*
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
/usr/bin/net-snmp-config
/usr/share/man/man3/*
