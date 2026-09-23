Name: tcpdump
Version: 4.99.7
Release: 1.linuxoss%{?dist}
Epoch: 14
Summary: tcpdump upstream EL8 candidate
License: BSD
URL: https://www.tcpdump.org/
Source0: tcpdump-4.99.7.tar.xz
BuildRequires: gcc, make, libpcap-devel, openssl-devel, perl
Vendor: Linux OSS local build
Requires: libpcap >= 14:1.11.0

%description
Upstream source build for EL8 compatibility evaluation.

%prep
%setup -q -n tcpdump-4.99.7

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --with-system-libpcap
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%files
%license LICENSE
%doc README.md
%{_bindir}/tcpdump
%{_bindir}/tcpdump.%{version}
%{_mandir}/man1/tcpdump.1*
