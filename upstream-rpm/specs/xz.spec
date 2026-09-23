Name:           xz
Version:        5.8.4
Release:        1.linuxoss%{?dist}
Summary:        XZ compression utilities, upstream EL8 candidate
License:        0BSD AND LGPL-2.1-or-later AND GPL-2.0-or-later
URL:            https://tukaani.org/xz/
Vendor:         Linux OSS local build
Source0:        xz-5.8.4.tar.xz
BuildRequires:  gcc, make, gettext
Requires:       %{name}-libs%{?_isa} = %{version}-%{release}
%description
XZ utilities built with the upstream regression tests.
%package libs
Summary:        LZMA compression shared library
%description libs
Shared liblzma library.
%package devel
Summary:        Development files for liblzma
Requires:       %{name}-libs%{?_isa} = %{version}-%{release}
%description devel
Headers and link metadata for liblzma.
%prep
%setup -q
%build
%configure --disable-static --enable-shared
make %{?_smp_mflags}
%check
make %{?_smp_mflags} check
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -rf %{buildroot}%{_docdir}/xz
# The target has no xz-lzma-compat. Keep its paths in a separate optional RPM
# rather than silently changing ownership when used on other EL8 hosts.
%package lzma-compat
Summary:        Legacy LZMA command aliases
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description lzma-compat
LZMA compatibility commands and manual pages.
%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig
%files
%license COPYING COPYING.*
%doc README NEWS AUTHORS THANKS
%{_bindir}/xz*
%{_bindir}/unxz
%{_mandir}/man1/xz*
%{_mandir}/man1/unxz*
%{_mandir}/*/man1/xz*
%{_mandir}/*/man1/unxz*
%{_datadir}/locale/*/LC_MESSAGES/xz.mo
%files libs
%license COPYING COPYING.*
%{_libdir}/liblzma.so.5*
%files devel
%{_includedir}/lzma.h
%{_includedir}/lzma/
%{_libdir}/liblzma.so
%{_libdir}/pkgconfig/liblzma.pc
%files lzma-compat
%{_bindir}/lz*
%{_bindir}/unlzma
%{_mandir}/man1/lz*
%{_mandir}/man1/unlzma*
%{_mandir}/*/man1/lz*
%{_mandir}/*/man1/unlzma*
%changelog
* Thu Sep 24 2026 Linux OSS local build - 5.8.4-1.linuxoss
- Build upstream security release and run regression tests.
