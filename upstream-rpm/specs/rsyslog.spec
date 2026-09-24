Name: rsyslog
Version: 8.2608.0
Release: 1.linuxoss%{?dist}
Summary: rsyslog upstream EL8 evaluation build
License: GPLv3+ and ASL 2.0
URL: https://www.rsyslog.com/
Source0: rsyslog-8.2608.0.tar.gz
Source1: rsyslog-local-test.py
BuildRequires: gcc, make, libestr-devel, libfastjson-devel, librelp-devel, gnutls-devel, krb5-devel, libgcrypt-devel, libuuid-devel, libcurl-devel, zlib-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package gnutls
Summary: gnutls files
%description gnutls
gnutls files.

%package gssapi
Summary: gssapi files
%description gssapi
gssapi files.

%package relp
Summary: relp files
%description relp
relp files.

%prep
%setup -q -n rsyslog-8.2608.0

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --enable-gnutls --enable-gssapi-krb5 --enable-relp --enable-imfile --enable-imjournal --enable-libsystemd
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
python3.11 %{SOURCE1} %{buildroot}

%files
%license COPYING COPYING.ASL20 COPYING.LESSER
/usr/sbin/*
/usr/lib64/rsyslog/
%exclude /usr/lib64/rsyslog/lmnsd_gtls.so
%exclude /usr/lib64/rsyslog/lmgssutil.so
%exclude /usr/lib64/rsyslog/imgssapi.so
%exclude /usr/lib64/rsyslog/omgssapi.so
%exclude /usr/lib64/rsyslog/imrelp.so
%exclude /usr/lib64/rsyslog/omrelp.so
/usr/share/man/*/*
%files gnutls
/usr/lib64/rsyslog/lmnsd_gtls.so
%files gssapi
/usr/lib64/rsyslog/lmgssutil.so
/usr/lib64/rsyslog/imgssapi.so
/usr/lib64/rsyslog/omgssapi.so
%files relp
/usr/lib64/rsyslog/imrelp.so
/usr/lib64/rsyslog/omrelp.so
