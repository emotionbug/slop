Name: libgpg-error
Version: 1.61
Release: 1.linuxoss%{?dist}
Summary: GnuPG error and runtime support library
License: LGPLv2+ and GPLv2+
URL: https://gnupg.org/software/libgpg-error/
Source0: libgpg-error-1.61.tar.bz2
BuildRequires: gcc, make, gettext, texinfo
Vendor: Linux OSS local build
%description
Error handling and portability runtime needed by current Libgcrypt.
%package devel
Summary: GnuPG error runtime development files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
Headers and build metadata.
%prep
%setup -q
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --disable-static --enable-install-gpg-error-config
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
%check
make %{?_smp_mflags} check
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license COPYING COPYING.LIB
%{_libdir}/libgpg-error.so.*
%{_bindir}/gpg-error
%{_bindir}/gpgrt-config
%{_bindir}/gpg-error-config
%{_bindir}/yat2m
%{_datadir}/libgpg-error/errorref.txt
%{_datadir}/locale/*/LC_MESSAGES/libgpg-error.mo
%{_datadir}/common-lisp/source/gpg-error/
%{_infodir}/gpgrt.info*
%{_mandir}/man1/*
%files devel
%{_includedir}/gpg-error.h
%{_includedir}/gpgrt.h
%{_libdir}/libgpg-error.so
%{_libdir}/pkgconfig/gpg-error.pc
%{_datadir}/aclocal/gpg-error.m4
%{_datadir}/aclocal/gpgrt.m4
