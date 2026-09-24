Name: krb5
Version: 1.22.2
Release: 1.linuxoss%{?dist}
Summary: krb5 upstream EL8 evaluation build
License: MIT
URL: https://web.mit.edu/kerberos/
Source0: krb5-1.22.2.tar.gz
BuildRequires: gcc, make, bison, libcom_err-devel, libverto-devel, openssl-devel, python3.11
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package -n libkadm5
Summary: Kerberos administration libraries
%description -n libkadm5
Kerberos administration libraries.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n krb5-1.22.2
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

cd src
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --localstatedir=/var --with-system-et --with-system-verto --enable-shared --disable-static PYTHON=python3.11
make %{?_smp_mflags}
%install
make -C src DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
%check
# Client/library and ASN.1 suites. Full server replication t_iprop.py hung in the isolated container; retained as unresolved evidence.
make -C src runenv.py
PYTHONUNBUFFERED=1 make -C src/lib %{?_smp_mflags} check
make -C src/tests/asn.1 %{?_smp_mflags} check

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%post -n libkadm5 -p /sbin/ldconfig
%postun -n libkadm5 -p /sbin/ldconfig

%files
%license NOTICE
/usr/bin/*
/usr/sbin/*
/usr/share/man/*/*
/usr/share/man/man5/.k5identity.5*
/usr/share/man/man5/.k5login.5*
/usr/share/examples/krb5/
%files libs
%license NOTICE
/usr/lib64/libgssapi_krb5.so.*
/usr/lib64/libgssrpc.so.*
/usr/lib64/libk5crypto.so.*
/usr/lib64/libkdb5.so.*
/usr/lib64/libkrb5*.so.*
/usr/lib64/libkrad.so.*
/usr/lib64/krb5/
/usr/share/locale/*/LC_MESSAGES/mit-krb5.mo
%files -n libkadm5
/usr/lib64/libkadm5*.so.*
%files devel
/usr/include/*
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
