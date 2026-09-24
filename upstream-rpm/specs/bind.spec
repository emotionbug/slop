Name: bind
Epoch: 32
Version: 9.20.29
Release: 1.linuxoss%{?dist}
Summary: bind upstream EL8 evaluation build
License: MPL-2.0
URL: https://www.isc.org/bind/
Source0: bind-9.20.29.tar.xz
BuildRequires: gcc, make, libuv-devel, userspace-rcu-devel, libnghttp2-devel, linuxoss-openssl4, libcap-devel, libcmocka-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package utils
Summary: utils files
%description utils
utils files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%if 0%{?reuse_prepared}
%setup -q -D -T -n bind-9.20.29
%else
%setup -q -n bind-9.20.29
%endif
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

export PKG_CONFIG_PATH=/opt/linux-oss/openssl-4.0.2/lib64/pkgconfig
export LDFLAGS="$LDFLAGS -L/opt/linux-oss/openssl-4.0.2/lib64 -Wl,-rpath,/opt/linux-oss/openssl-4.0.2/lib64"
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --localstatedir=/var --disable-static --disable-geoip --without-json-c
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
%check
make -C tests %{?_smp_mflags} check
bin/dig/dig -v
bin/named/named -V

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license LICENSE
/usr/sbin/*
/usr/share/man/man5/*
/usr/share/man/man8/*
%files libs
/usr/lib64/lib*-9.20.29.so
/usr/lib64/bind/
%files utils
/usr/bin/*
/usr/share/man/man1/*
%files devel
/usr/include/*
/usr/lib64/libdns.so
/usr/lib64/libisc.so
/usr/lib64/libisccc.so
/usr/lib64/libisccfg.so
/usr/lib64/libns.so
