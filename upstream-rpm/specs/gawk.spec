%global _find_debuginfo_dwz_opts %{nil}
Name: gawk
Version: 5.4.1
Release: 2.linuxoss%{?dist}
Summary: GNU awk, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/gawk/
Source0: gawk-5.4.1.tar.xz
BuildRequires: gcc, make, readline-devel, mpfr-devel, gmp-devel
Vendor: Linux OSS local build
Provides: /bin/awk /bin/gawk
%description
GNU awk with arbitrary precision support, loadable extensions and tests.
%prep
%setup -q
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --sysconfdir=/etc --libdir=/usr/lib64 --enable-extensions --with-readline --with-mpfr
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_infodir}/dir
find %{buildroot} -name '*.la' -delete
%check
make %{?_smp_mflags} check
%files
%license COPYING
%doc NEWS README
%{_bindir}/*
%{_libdir}/gawk/
%{_libexecdir}/awk/
%{_includedir}/gawkapi.h
%{_datadir}/awk/
%{_datadir}/locale/*/LC_MESSAGES/gawk.mo
%{_mandir}/man1/*
%{_mandir}/man3/*.3am*
%{_infodir}/*
%config(noreplace) /etc/profile.d/gawk.sh
%config(noreplace) /etc/profile.d/gawk.csh
