Name: gd
Version: 2.3.3
Release: 1.linuxoss%{?dist}
Summary: gd upstream EL8 evaluation build
License: MIT
URL: https://libgd.github.io/
Source0: libgd-2.3.3.tar.xz
BuildRequires: gcc, make, libpng-devel, libjpeg-turbo-devel, libtiff-devel, freetype-devel, fontconfig-devel, libwebp-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%package progs
Summary: progs files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description progs
progs files.

%prep
%setup -q -n libgd-2.3.3

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-png --with-jpeg --with-tiff --with-freetype --with-fontconfig --with-webp --enable-gd-formats
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
export TMPDIR=$(mktemp -d)
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/lib64/libgd.so.*
%files devel
/usr/include/*
/usr/lib64/libgd.so
/usr/lib64/pkgconfig/gdlib.pc
%files progs
/usr/bin/*
