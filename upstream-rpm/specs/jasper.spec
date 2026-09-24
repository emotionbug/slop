Name: jasper
Version: 4.2.9
Release: 1.linuxoss%{?dist}
Summary: jasper upstream EL8 evaluation build
License: JasPer-2.0
URL: https://jasper-software.github.io/jasper/
Source0: jasper-4.2.9.tar.gz
BuildRequires: gcc, make, cmake, libjpeg-turbo-devel
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
%description devel
devel files.

%prep
%setup -q -n jasper-4.2.9
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

cmake -S . -B ../jasper-build -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 -DJAS_ENABLE_SHARED=ON -DJAS_ENABLE_DOC=OFF -DJAS_ENABLE_OPENGL=OFF
cmake --build ../jasper-build -j 2
%install
DESTDIR=%{buildroot} cmake --install ../jasper-build
%check
ctest --test-dir ../jasper-build --output-on-failure -j 2

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license LICENSE.txt
/usr/bin/*
/usr/share/man/man1/*
/usr/share/doc/JasPer/
%files libs
/usr/lib64/libjasper.so.*
%files devel
/usr/include/jasper/
/usr/lib64/libjasper.so
/usr/lib64/pkgconfig/*
