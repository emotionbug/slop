Name: freetype
Version: 2.14.3
Release: 1.linuxoss%{?dist}
Summary: freetype upstream EL8 evaluation
License: FTL or GPLv2+
URL: https://freetype.org/
Source0: freetype-2.14.3.tar.xz
BuildRequires: gcc, make, zlib-devel, bzip2-devel, libpng-devel, harfbuzz-devel, brotli-devel
Vendor: Linux OSS local build
Requires: harfbuzz >= 2.0.0

%description
Upstream source build. Target ABI and runtime qualification are separate.

%package devel
Summary: devel files from freetype
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files from freetype.

%prep
%setup -q -n freetype-2.14.3

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-harfbuzz=yes
make %{?_smp_mflags}


%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name "*.la" -delete


%check
make check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE.TXT docs/FTL.TXT docs/GPLv2.TXT
%{_libdir}/libfreetype.so.*

%files devel
%{_includedir}/freetype2/
%{_libdir}/libfreetype.so
%{_libdir}/pkgconfig/freetype2.pc
%{_datadir}/aclocal/freetype2.m4
