Name:           libpng
Epoch:          2
Version:        1.6.58
Release:        1.linuxoss%{?dist}
Summary:        PNG image library, upstream EL8 candidate
License:        Libpng-2.0
URL:            https://www.libpng.org/pub/png/libpng.html
Vendor:         Linux OSS local build
Source0:        libpng-1.6.58.tar.xz
BuildRequires:  gcc, make, zlib-devel

%description
PNG reference library with upstream regression tests enabled.

%package devel
Summary:        PNG development files
Requires:       %{name}%{?_isa} = %{epoch}:%{version}-%{release}
Requires:       zlib-devel
%description devel
Headers and linking metadata for libpng.

%package tools
Summary:        PNG inspection and repair utilities
Requires:       %{name}%{?_isa} = %{epoch}:%{version}-%{release}
%description tools
Upstream pngfix and png-fix-itxt utilities.

%prep
%setup -q
%build
%configure --disable-static
make %{?_smp_mflags}
%check
make %{?_smp_mflags} check
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license LICENSE
%doc README CHANGES
%{_libdir}/libpng16.so.16*
%files devel
%{_includedir}/png*.h
%{_includedir}/libpng16/
%{_libdir}/libpng*.so
%{_libdir}/pkgconfig/libpng*.pc
%{_bindir}/libpng*-config
%{_mandir}/man3/libpng*.3*
%{_mandir}/man5/png.5*
%files tools
%{_bindir}/pngfix
%{_bindir}/png-fix-itxt

%changelog
* Thu Sep 24 2026 Linux OSS local build - 1.6.58-1.linuxoss
- Build pinned upstream release and run regression tests.
