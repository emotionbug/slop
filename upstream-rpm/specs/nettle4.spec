%global prefix /opt/linux-oss/nettle-4.0
Name: linuxoss-nettle4
Version: 4.0
Release: 1.linuxoss%{?dist}
Summary: Private Nettle 4 dependency for upstream migration
License: LGPLv3+ or GPLv2+
URL: https://www.lysator.liu.se/~nisse/nettle/
Source0: nettle-4.0.tar.gz
Vendor: Linux OSS local build
BuildRequires: gcc, make, gmp-devel, m4

%description
Parallel dependency for rebuilding newer TLS libraries on EL8. Does not replace
the existing system Nettle library or imply its vulnerabilities are remediated.

%prep
%setup -q -n nettle-4.0
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now -Wl,-rpath,%{prefix}/lib64'
./configure --prefix=%{prefix} --libdir=%{prefix}/lib64 --disable-static
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
chmod 0755 %{buildroot}%{prefix}/lib64/libnettle.so.* %{buildroot}%{prefix}/lib64/libhogweed.so.*
%check
make %{?_smp_mflags} check
%files
%license COPYING.LESSERv3 COPYINGv2 COPYINGv3
%{prefix}/
