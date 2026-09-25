Name: graphviz
Version: 12.2.1
Release: 2.linuxoss%{?dist}
Summary: graphviz upstream EL8 evaluation build
License: EPL-1.0
URL: https://graphviz.org/
Source0: graphviz-12.2.1.tar.gz
BuildRequires: gcc, gcc-c++, make, cmake, bison, flex, gd-devel, zlib-devel, libpng-devel, libjpeg-turbo-devel, expat-devel, cairo-devel
BuildRequires: libtool-ltdl-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%package gd
Summary: GD image output plugin for Graphviz
Requires: %{name}%{?_isa} = %{version}-%{release}
%description gd
PNG, JPEG and GIF output plugin using the GD library.

%prep
%setup -q -n graphviz-12.2.1
%build
export CC=/usr/bin/gcc CXX=/usr/bin/g++ PKG_CONFIG_PATH= LD_LIBRARY_PATH=
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --disable-static --disable-swig --disable-man-pdfs --without-gvedit --without-smyrna
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
%check
printf 'digraph G { a -> b; }\n' > sample.dot
export GVBINDIR=%{buildroot}/usr/lib64/graphviz
export LD_LIBRARY_PATH=%{buildroot}/usr/lib64
%{buildroot}/usr/bin/dot -c
%{buildroot}/usr/bin/dot -Tsvg sample.dot > sample.svg
grep -q '<svg' sample.svg

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%posttrans
/usr/bin/dot -c

%posttrans gd
/usr/bin/dot -c

%files
%license COPYING
/usr/bin/*
/usr/lib64/lib*.so.*
/usr/lib64/graphviz/
%exclude /usr/lib64/graphviz/libgvplugin_gd.so*
/usr/share/graphviz/
/usr/share/man/*/*
%doc /usr/share/doc/graphviz/
%files devel
/usr/include/graphviz/
/usr/lib64/*.so
/usr/lib64/pkgconfig/*

%files gd
/usr/lib64/graphviz/libgvplugin_gd.so*
