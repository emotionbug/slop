Name: bison
Version: 3.8.2
Release: 2.linuxoss%{?dist}
Summary: GNU parser generator, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/bison/
Source0: bison-3.8.2.tar.xz
Patch0: bison-CVE-2026-56389.patch
BuildRequires: gcc, gcc-c++, make, m4, perl
Requires: m4
Vendor: Linux OSS local build
%description
GNU Bison parser generator with its upstream language and parser tests.
%prep
%setup -q
patch --fuzz=0 -p1 < %{PATCH0}
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2'
export CXXFLAGS="$CFLAGS"
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_infodir}/dir
%check
make %{?_smp_mflags} check
%files
%license COPYING
%doc NEWS README
%{_bindir}/bison
%{_bindir}/yacc
%{_libdir}/liby.a
%{_datadir}/bison/
%{_datadir}/aclocal/bison-i18n.m4
%{_datadir}/locale/*/LC_MESSAGES/bison*.mo
%{_docdir}/bison/
%{_mandir}/man1/*
%{_infodir}/bison.info*
