Name: curl
Version: 8.22.0
Release: 1.linuxoss%{?dist}
Summary: curl upstream EL8 evaluation build
License: curl
URL: https://curl.se/
Source0: curl-8.22.0.tar.xz
BuildRequires: gcc, make, linuxoss-openssl4, zlib-devel, libssh-devel, libnghttp2-devel, libidn2-devel, libpsl-devel, krb5-devel, openldap-devel, brotli-devel, libzstd-devel
Vendor: Linux OSS local build

Requires: linuxoss-openssl4 >= 4.0.2

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package -n libcurl
Summary: curl transfer library
%description -n libcurl
Shared transfer library.
%package -n libcurl-devel
Summary: curl headers
Requires: libcurl%{?_isa} = %{version}-%{release}
%description -n libcurl-devel
Development files.

%prep
%setup -q -n curl-8.22.0

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now -Wl,-rpath,/opt/linux-oss/openssl-4.0.2/lib64'
export PKG_CONFIG_PATH=/opt/linux-oss/openssl-4.0.2/lib64/pkgconfig

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-openssl=/opt/linux-oss/openssl-4.0.2 --with-ca-bundle=/etc/pki/tls/certs/ca-bundle.crt --with-ca-path=/etc/pki/tls/certs --with-libssh --with-nghttp2 --with-gssapi --enable-versioned-symbols
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} -C tests test TFLAGS="-a -p !flaky"

%post -n libcurl -p /sbin/ldconfig
%postun -n libcurl -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/curl
/usr/bin/wcurl
/usr/share/man/man1/wcurl.1*
/usr/share/man/man1/curl.1*
%files -n libcurl
%license COPYING
/usr/lib64/libcurl.so.*
%files -n libcurl-devel
/usr/bin/curl-config
/usr/include/curl/
/usr/lib64/libcurl.so
/usr/lib64/pkgconfig/libcurl.pc
/usr/share/man/man1/curl-config.1*
/usr/share/man/man3/*
/usr/share/aclocal/*
