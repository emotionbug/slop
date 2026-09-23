Name:           libjpeg-turbo
Version:        3.2.0
Release:        1.linuxoss%{?dist}
Summary:        JPEG image library, upstream EL8 candidate
License:        IJG AND BSD-3-Clause AND Zlib
URL:            https://libjpeg-turbo.org/
Vendor:         Linux OSS local build
Source0:        libjpeg-turbo-3.2.0.tar.gz
BuildRequires:  gcc, make, cmake, nasm, zlib-devel

%description
JPEG library built with the libjpeg v6b ABI and SIMD regression tests.
The optional TurboJPEG library and tools use the upstream bundled libspng
and dynamically link the system zlib; those components are tracked separately.

%package devel
Summary:        JPEG development files
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description devel
Headers and linking metadata for the libjpeg v6b ABI.

%package -n turbojpeg
Summary:        TurboJPEG API library
Provides:       bundled(libspng) = 0.7.4
%description -n turbojpeg
TurboJPEG API from the same upstream source release.

%package -n turbojpeg-devel
Summary:        TurboJPEG development files
Requires:       turbojpeg%{?_isa} = %{version}-%{release}
%description -n turbojpeg-devel
Headers and linking metadata for TurboJPEG.

%package utils
Summary:        JPEG image conversion utilities
Requires:       %{name}%{?_isa} = %{version}-%{release}
Provides:       bundled(libspng) = 0.7.4
%description utils
JPEG encoding, decoding, transformation and inspection tools.

%prep
%setup -q
%build
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_STATIC=OFF -DENABLE_SHARED=ON \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DWITH_JPEG7=OFF -DWITH_JPEG8=OFF -DREQUIRE_SIMD=ON \
  -DWITH_TESTS=ON -DWITH_SYSTEM_ZLIB=ON
cmake --build build -- %{?_smp_mflags}
%check
ctest --test-dir build --output-on-failure
%install
DESTDIR=%{buildroot} cmake --install build

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%post -n turbojpeg -p /sbin/ldconfig
%postun -n turbojpeg -p /sbin/ldconfig
%files
%license LICENSE.md
%{_libdir}/libjpeg.so.62*
%doc %{_docdir}/libjpeg-turbo/
%files devel
%{_includedir}/j*.h
%{_libdir}/libjpeg.so
%{_libdir}/pkgconfig/libjpeg.pc
%{_libdir}/cmake/libjpeg-turbo/
%files -n turbojpeg
%license LICENSE.md src/spng/LICENSE
%{_libdir}/libturbojpeg.so.0*
%files -n turbojpeg-devel
%{_includedir}/turbojpeg.h
%{_libdir}/libturbojpeg.so
%{_libdir}/pkgconfig/libturbojpeg.pc
%files utils
%{_bindir}/*
%{_mandir}/man1/*

%changelog
* Thu Sep 24 2026 Linux OSS local build - 3.2.0-1.linuxoss
- Preserve libjpeg v6b ABI and run upstream SIMD image tests.
