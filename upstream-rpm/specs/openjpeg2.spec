Name: openjpeg2
Version: 2.5.4
Release: 1.linuxoss%{?dist}
Summary: JPEG 2000 image codec
License: BSD
URL: https://www.openjpeg.org/
Source0: openjpeg-2.5.4.tar.gz
Source1: openjpeg-data-39524bd3a601d90ed8e0177559400d23945f96a9.tar.gz
NoSource: 1
BuildRequires: gcc, gcc-c++, cmake, libpng-devel, libtiff-devel, lcms2-devel
Vendor: Linux OSS local build
%description
Upstream JPEG 2000 codec, tested with the pinned upstream image corpus.
The large test-only corpus is fetched separately and omitted from the SRPM.
%package devel
Summary: JPEG 2000 development files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
OpenJPEG headers and build metadata.
%package tools
Summary: JPEG 2000 codec tools
Requires: %{name}%{?_isa} = %{version}-%{release}
%description tools
OpenJPEG encoding, decoding and image information tools.
%prep
%setup -q -n openjpeg-2.5.4
mkdir test-corpus
tar -xf %{SOURCE1} -C test-corpus --strip-components=1
%build
export CXX=/usr/bin/g++
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -D_FORTIFY_SOURCE=2'
export CXXFLAGS="$CFLAGS"
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_SHARED_LIBS=ON -DBUILD_STATIC_LIBS=OFF -DBUILD_TESTING=ON -DOPJ_DATA_ROOT="$PWD/test-corpus"
cmake --build build --parallel 2
%install
DESTDIR=%{buildroot} cmake --install build
%check
ctest --test-dir build --output-on-failure --parallel 2
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license LICENSE
%{_libdir}/libopenjp2.so.*
%files devel
%{_includedir}/openjpeg-2.5/
%{_libdir}/libopenjp2.so
%{_libdir}/pkgconfig/libopenjp2.pc
%{_libdir}/openjpeg-2.5/
%files tools
%{_bindir}/opj_*
