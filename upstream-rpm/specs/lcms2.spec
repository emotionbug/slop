Name:           lcms2
Version:        2.19.1
Release:        1.linuxoss%{?dist}
Summary:        Little CMS color management library, upstream EL8 candidate
License:        MIT
URL:            https://www.littlecms.com/
Vendor:         Linux OSS local build
Source0:        lcms2-2.19.1.tar.gz
BuildRequires:  gcc, make, libjpeg-turbo-devel, libtiff-devel, zlib-devel

%description
ICC color management library with upstream tests enabled.

%package devel
Summary:        Little CMS development files
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description devel
Headers and linking metadata for Little CMS.

%package utils
Summary:        Little CMS color conversion utilities
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description utils
ICC profile utilities and JPEG/TIFF color converters.

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
%doc README.md
%{_libdir}/liblcms2.so.2*
%files devel
%{_includedir}/lcms2*.h
%{_libdir}/liblcms2.so
%{_libdir}/pkgconfig/lcms2.pc
%files utils
%{_bindir}/*
%{_mandir}/man1/*

%changelog
* Thu Sep 24 2026 Linux OSS local build - 2.19.1-1.linuxoss
- Build pinned upstream release and run regression tests.
