Name: libtiff
Version: 4.7.2
Release: 1.linuxoss%{?dist}
Summary: libtiff upstream EL8 evaluation
License: libtiff
URL: https://libtiff.gitlab.io/libtiff/
Source0: tiff-4.7.2.tar.xz
BuildRequires: gcc, gcc-c++, cmake, zlib-devel, libjpeg-turbo-devel, xz-devel, libzstd-devel, libwebp-devel, jbigkit-devel
Vendor: Linux OSS local build

%description
Upstream source build. Target ABI and runtime qualification are separate.

%package devel
Summary: devel files from libtiff
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files from libtiff.

%package tools
Summary: tools files from libtiff
Requires: %{name}%{?_isa} = %{version}-%{release}
%description tools
tools files from libtiff.

%prep
%setup -q -n tiff-4.7.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
export CXX=/usr/bin/g++
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_SHARED_LIBS=ON -Dtiff-tests=ON -Dtiff-docs=OFF -Dtiff-tools=ON
cmake --build build --parallel %{?_smp_build_ncpus}


%install
DESTDIR=%{buildroot} cmake --install build
find %{buildroot} -name "*.la" -delete


%check
ctest --test-dir build --output-on-failure --parallel 2

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE.md
%{_libdir}/libtiff*.so.*

%files devel
%{_includedir}/tiff*.h
%{_includedir}/tiffio.hxx
%{_libdir}/libtiff*.so
%{_libdir}/pkgconfig/libtiff-4.pc
%{_libdir}/cmake/tiff/

%files tools
%{_bindir}/*
