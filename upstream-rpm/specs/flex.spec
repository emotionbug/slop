Name: flex
Version: 2.6.4
Release: 1.linuxoss%{?dist}
Summary: flex upstream EL8 evaluation build
License: BSD
URL: https://github.com/westes/flex
Source0: flex-2.6.4.tar.gz
BuildRequires: gcc, gcc-c++, make, bison
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n flex-2.6.4

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2 -D_GNU_SOURCE'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
ln -sf flex %{buildroot}/usr/bin/lex
%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
/usr/share/doc/flex/
%license COPYING
/usr/bin/*
/usr/include/*
/usr/lib64/libfl.so*
/usr/share/man/man1/*
/usr/share/info/*
/usr/share/locale/*/LC_MESSAGES/flex.mo
