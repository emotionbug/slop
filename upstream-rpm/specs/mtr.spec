Name: mtr
Version: 0.96
Epoch: 2
Release: 1.linuxoss%{?dist}
Summary: mtr upstream EL8 evaluation build
License: GPLv2+
URL: https://www.bitwizard.nl/mtr/
Source0: mtr-0.96.tar.gz
BuildRequires: gcc, make, ncurses-devel, jansson-devel, libcap-devel, python3
Vendor: Linux OSS local build
%bcond_with network_tests

%description
Upstream build for EL8 evaluation. Target deployment requires separate review.

%prep
%setup -q -n mtr-0.96

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --without-gtk
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
chmod 0755 %{buildroot}/usr/sbin/mtr-packet
%check
%if %{with network_tests}
make %{?_smp_mflags} check
%else
# The upstream suite requires raw sockets and DNS during import. It is run
# separately against the installed RPM in an isolated loopback container.
make mtr-packet-listen
echo 'MTR network tests deferred to the combined installed-RPM validation'
%endif

%files
%license COPYING BSDCOPYING
%doc README.md NEWS SECURITY
%{_sbindir}/mtr
%caps(cap_net_raw=ep) %{_sbindir}/mtr-packet
%{_mandir}/man8/*
%{_datadir}/bash-completion/completions/mtr
