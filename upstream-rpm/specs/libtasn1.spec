Name: libtasn1
Version: 4.21.0
Release: 1.linuxoss%{?dist}
Summary: ASN.1 library, upstream EL8 candidate
License: LGPLv2+ and GPLv3+
URL: https://www.gnu.org/software/libtasn1/
Source0: libtasn1-4.21.0.tar.gz
BuildRequires: gcc, make, bison, texinfo
Vendor: Linux OSS local build

%description
ASN.1 DER/BER parsing and encoding library with upstream regression tests.
This release includes the upstream fix for CVE-2025-13151.

%package devel
Summary: Development headers for libtasn1
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
Development files for applications using libtasn1.

%package tools
Summary: ASN.1 command-line tools
Requires: %{name}%{?_isa} = %{version}-%{release}
%description tools
ASN.1 parser, coder and decoder utilities.

%prep
%setup -q

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --disable-static
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_libdir}/*.la %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING COPYING.LESSERv2
%doc AUTHORS NEWS.md README.md
%{_libdir}/libtasn1.so.*

%files devel
%{_includedir}/libtasn1.h
%{_libdir}/libtasn1.so
%{_libdir}/pkgconfig/libtasn1.pc
%{_infodir}/libtasn1.info*
%{_mandir}/man3/*

%files tools
%{_bindir}/asn1Parser
%{_bindir}/asn1Coding
%{_bindir}/asn1Decoding
%{_mandir}/man1/*
