Name: xmlrpc-c
Version: 1.64.03
Release: 1.linuxoss%{?dist}
Summary: xmlrpc-c upstream EL8 evaluation build
License: BSD and MIT
URL: https://xmlrpc-c.sourceforge.io/
Source0: xmlrpc-1.64.03.tgz
BuildRequires: gcc, gcc-c++, make, libcurl-devel, libxml2-devel, readline-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package client
Summary: client files
%description client
client files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n xmlrpc-1.64.03

# Upstream's C test link rule omits external XML/TLS/curl libraries when using a system XML parser.
sed -i '/$(TEST_OBJS) $(LDADD_CLIENT) $(LDADD_ABYSS_SERVER) $(CASPRINTF)$/s/$/ -lxml2 -lssl -lcrypto -lcurl/' test/Makefile
sed -i '/$(CCLD) -o $@ $(CGITEST1_OBJS) $(LDFLAGS_ALL) $(LDADD_CGI_SERVER)$/s/$/ -lxml2/' test/Makefile
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -fPIC'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --enable-libxml2-backend --enable-curl-client --disable-wininet-client --disable-libwww-client
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check LIBS="-lxml2 -lssl -lcrypto -lcurl"

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%post client -p /sbin/ldconfig
%postun client -p /sbin/ldconfig

%files
%license doc/COPYING
/usr/bin/*
%exclude /usr/bin/xmlrpc-c-config
/usr/lib64/lib*.so.*
%exclude /usr/lib64/libxmlrpc_client*.so.*
%files client
/usr/lib64/libxmlrpc_client*.so.*
%files devel
/usr/bin/xmlrpc-c-config
/usr/include/xmlrpc-c/
/usr/include/*.h
/usr/lib64/*.so
/usr/lib64/*.a
/usr/lib64/pkgconfig/*
