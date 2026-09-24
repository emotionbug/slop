Name: mariadb-connector-c
Version: 3.4.10
Release: 1.linuxoss%{?dist}
Summary: mariadb-connector-c upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://github.com/mariadb-corporation/mariadb-connector-c
Source0: mariadb-connector-c-3.4.10.tar.gz
BuildRequires: gcc, gcc-c++, cmake, openssl-devel, zlib-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n mariadb-connector-c-3.4.10
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_INSTALL_PREFIX=/usr -DINSTALL_LIBDIR=lib64 -DINSTALL_PLUGINDIR=lib64/mariadb/plugin -DINSTALL_MANDIR=share/man -DINSTALL_PCDIR=lib64/pkgconfig -DWITH_UNIT_TESTS=OFF -DWITH_SSL=OPENSSL
cmake --build build -j 2
%install
DESTDIR=%{buildroot} cmake --install build
find %{buildroot} -name '*.a' -delete
%check
build/mariadb_config/mariadb_config --cc_version | grep '3.4.10'

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING.LIB
/usr/lib64/libmariadb.so.*
/usr/lib64/mariadb/plugin/
%files devel
/usr/bin/*
/usr/include/mariadb/
/usr/lib64/libmariadb.so
/usr/lib64/pkgconfig/*
/usr/share/man/*/*
