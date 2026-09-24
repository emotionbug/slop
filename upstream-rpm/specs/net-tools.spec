Name: net-tools
Version: 2.10
Release: 1.linuxoss%{?dist}
Summary: net-tools upstream EL8 evaluation build
License: GPLv2+
URL: https://sourceforge.net/projects/net-tools/
Source0: net-tools-2.10.tar.xz
BuildRequires: gcc, make, gettext-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n net-tools-2.10
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

yes '' | make config
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} BINDIR=/usr/bin SBINDIR=/usr/sbin install
# hostname is a separate EL8 package.
rm -f %{buildroot}/usr/bin/hostname %{buildroot}/usr/bin/domainname %{buildroot}/usr/bin/dnsdomainname %{buildroot}/usr/bin/nisdomainname %{buildroot}/usr/bin/ypdomainname
find %{buildroot}/usr/share/man -type f   \( -name 'hostname.*' -o -name 'domainname.*' -o -name 'dnsdomainname.*' -o -name 'nisdomainname.*' -o -name 'ypdomainname.*' \) -delete
# Preserve EL8 command locations for programs still shipped upstream.
for tool in ifconfig route ether-wake; do
  if test -f %{buildroot}/usr/bin/$tool; then ln -s ../bin/$tool %{buildroot}/usr/sbin/$tool; fi
done
%check
./netstat -rn
./ifconfig -a

%files
%license COPYING
/usr/bin/*
/usr/sbin/*
/usr/share/man/*/*
