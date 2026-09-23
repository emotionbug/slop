Name: harfbuzz
Version: 14.5.0
Release: 1.linuxoss%{?dist}
Summary: HarfBuzz text shaping engine
License: MIT
URL: https://harfbuzz.github.io/
Source0: harfbuzz-14.5.0.tar.xz
BuildRequires: gcc, gcc-c++, ninja-build, freetype-devel, glib2-devel, cairo-devel, graphite2-devel, libicu-devel
Vendor: Linux OSS local build
Requires: freetype >= 2.14.3

%description
HarfBuzz upstream EL8 compatibility evaluation build.

%package devel
Summary: HarfBuzz development files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
HarfBuzz headers and metadata.

%package icu
Summary: ICU Unicode adapter
Requires: %{name}%{?_isa} = %{version}-%{release}
%description icu
HarfBuzz ICU Unicode adapter.

%package tools
Summary: HarfBuzz font tools
Requires: %{name}%{?_isa} = %{version}-%{release}
%description tools
Font shaping, inspection and subsetting tools.

%prep
%setup -q

%build
export CC=/usr/bin/gcc CXX=/usr/bin/g++
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2'
export CXXFLAGS="$CFLAGS"
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
meson setup build --prefix=/usr --libdir=lib64 --buildtype=debugoptimized --wrap-mode=nodownload \
  -Ddefault_library=shared -Dglib=enabled -Dgobject=enabled -Dfreetype=enabled \
  -Dgraphite2=enabled -Dicu=enabled -Dcairo=enabled -Dtests=enabled \
  -Dintrospection=disabled -Ddocs=disabled
meson compile -C build -j 2

%install
DESTDIR=%{buildroot} meson install -C build --no-rebuild

%check
meson test -C build --no-rebuild --print-errorlogs --num-processes 2

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
%{_libdir}/libharfbuzz.so.*
%{_libdir}/libharfbuzz-gobject.so.*
%{_libdir}/libharfbuzz-subset.so.*
%{_libdir}/libharfbuzz-raster.so.*
%{_libdir}/libharfbuzz-vector.so.*
%{_libdir}/libharfbuzz-gpu.so.*
%{_libdir}/libharfbuzz-cairo.so.*

%files icu
%{_libdir}/libharfbuzz-icu.so.*

%files devel
%{_includedir}/harfbuzz/
%{_libdir}/libharfbuzz*.so
%{_libdir}/pkgconfig/harfbuzz*.pc
%{_libdir}/cmake/harfbuzz/

%files tools
%{_bindir}/hb-*
