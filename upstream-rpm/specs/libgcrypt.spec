Name: libgcrypt
Version: 1.12.4
Release: 1.linuxoss%{?dist}
Summary: GNU cryptographic library
License: LGPLv2+ and GPLv2+
URL: https://gnupg.org/software/libgcrypt/
Source0: libgcrypt-1.12.4.tar.bz2
BuildRequires: gcc, make, libgpg-error-devel >= 1.56, texinfo
Requires: libgpg-error >= 1.56
Vendor: Linux OSS local build
%description
Upstream cryptographic library for EL8 compatibility evaluation.
This custom build is not a Red Hat FIPS-validated cryptographic module.
%package devel
Summary: Cryptographic library development files
Requires: %{name}%{?_isa} = %{version}-%{release}
Requires: libgpg-error-devel >= 1.56
%description devel
Libgcrypt headers and build metadata.
%prep
%setup -q
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --disable-static
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
%license COPYING COPYING.LIB LICENSES
%{_libdir}/libgcrypt.so.*
%{_bindir}/dumpsexp
%{_bindir}/hmac256
%{_bindir}/mpicalc
%{_mandir}/man1/hmac256.1*
%files devel
%{_includedir}/gcrypt.h
%{_libdir}/libgcrypt.so
%{_libdir}/pkgconfig/libgcrypt.pc
%{_bindir}/libgcrypt-config
%{_datadir}/aclocal/libgcrypt.m4
%{_infodir}/gcrypt.info*
