Name: graphviz
Version: 16.1.0
Release: 1.linuxoss%{?dist}
Summary: graphviz upstream EL8 evaluation build
License: EPL-1.0
URL: https://graphviz.org/
Source0: graphviz-16.1.0.tar.gz
BuildRequires: gcc, gcc-c++, make, cmake, bison, flex, gd-devel, zlib-devel, libpng-devel, libjpeg-turbo-devel, expat-devel, cairo-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n graphviz-16.1.0
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -Denable_swig=OFF -Dwith_gvedit=OFF -Dwith_smyrna=OFF
cmake --build build -j 2
%install
DESTDIR=%{buildroot} cmake --install build
%check
printf 'digraph G { a -> b; }\n' > sample.dot
export GVBINDIR=%{buildroot}/usr/lib64/graphviz
export LD_LIBRARY_PATH=%{buildroot}/usr/lib64
%{buildroot}/usr/bin/dot -c
%{buildroot}/usr/bin/dot -Tsvg sample.dot > sample.svg
grep -q '<svg' sample.svg

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/*
/usr/lib64/lib*.so.*
/usr/lib64/graphviz/
/usr/share/graphviz/
/usr/share/man/*/*
%files devel
/usr/include/graphviz/
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
/usr/lib64/cmake/graphviz/
