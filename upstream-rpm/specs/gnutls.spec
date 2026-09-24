Name: gnutls
Version: 3.8.13
Release: 1.linuxoss%{?dist}
Summary: gnutls upstream EL8 evaluation build
License: LGPLv2+
URL: https://gnutls.org/
Source0: gnutls-3.8.13.tar.xz
BuildRequires: gcc, make, linuxoss-nettle4, gmp-devel, libtasn1-devel, p11-kit-devel, libunistring-devel, zlib-devel, libidn2-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%package utils
Summary: utils files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description utils
utils files.

%prep
%setup -q -n gnutls-3.8.13

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-L/opt/linux-oss/nettle-4.0/lib64 -Wl,--build-id -Wl,-z,relro,-z,now -Wl,-rpath,/opt/linux-oss/nettle-4.0/lib64'
export PKG_CONFIG_PATH=/opt/linux-oss/nettle-4.0/lib64/pkgconfig

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-guile --without-tpm --disable-doc
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
# This test includes gnulib's free replacement on glibc 2.28; link its provider.
make %{?_smp_mflags} check 'mini_dtls_fragments_LDADD=$(LDADD) ../gl/libgnu.la'

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING COPYING.LESSERv2
/usr/lib64/libgnutls*.so.*
/usr/share/locale/*/LC_MESSAGES/gnutls.mo
%files devel
/usr/include/gnutls/
/usr/lib64/libgnutls*.so
/usr/lib64/pkgconfig/*
%files utils
/usr/bin/*
