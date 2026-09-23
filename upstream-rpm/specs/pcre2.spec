Name:           pcre2
Version:        10.48
Release:        1.linuxoss%{?dist}
Summary:        Perl-compatible regular expression libraries
License:        BSD-3-Clause
URL:            https://github.com/PCRE2Project/pcre2
Vendor:         Linux OSS local build
Source0:        pcre2-10.48.tar.bz2
BuildRequires:  gcc, make

%description
Upstream 8-bit PCRE2 and POSIX wrapper for EL8 evaluation.

%package utf16
Summary:        PCRE2 16-bit library
%description utf16
PCRE2 16-bit library.

%package utf32
Summary:        PCRE2 32-bit library
%description utf32
PCRE2 32-bit library.

%package devel
Summary:        Development headers and metadata for PCRE2
Requires:       %{name}%{?_isa} = %{version}-%{release}
Requires:       %{name}-utf16%{?_isa} = %{version}-%{release}
Requires:       %{name}-utf32%{?_isa} = %{version}-%{release}
%description devel
PCRE2 headers, link metadata and API documentation.

%package tools
Summary:        PCRE2 regular expression tools
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description tools
PCRE2 grep and test utilities.

%prep
%setup -q

%build
%configure --enable-pcre2-16 --enable-pcre2-32 --enable-jit --enable-unicode --disable-static
make %{?_smp_mflags}

%check
make %{?_smp_mflags} check

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%post utf16 -p /sbin/ldconfig
%postun utf16 -p /sbin/ldconfig
%post utf32 -p /sbin/ldconfig
%postun utf32 -p /sbin/ldconfig

%files
%license LICENCE.md
%doc README NEWS ChangeLog
%{_libdir}/libpcre2-8.so.*
%{_libdir}/libpcre2-posix.so.*

%files utf16
%license LICENCE.md
%{_libdir}/libpcre2-16.so.*

%files utf32
%license LICENCE.md
%{_libdir}/libpcre2-32.so.*

%files devel
%{_includedir}/pcre2.h
%{_includedir}/pcre2posix.h
%{_libdir}/libpcre2*.so
%{_libdir}/pkgconfig/libpcre2*.pc
%{_bindir}/pcre2-config
%{_mandir}/man3/*
%{_mandir}/man1/pcre2-config.1*
%{_datadir}/doc/pcre2/*

%files tools
%{_bindir}/pcre2grep
%{_bindir}/pcre2test
%{_mandir}/man1/pcre2grep.1*
%{_mandir}/man1/pcre2test.1*

%changelog
* Wed Sep 23 2026 Linux OSS local build - 10.48-1.linuxoss
- Build all three character widths and JIT; run upstream checks.
