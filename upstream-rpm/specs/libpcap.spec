Name: libpcap
Version: 1.11.0
Release: 1.linuxoss%{?dist}
Epoch: 14
Summary: libpcap upstream EL8 candidate
License: BSD
URL: https://www.tcpdump.org/
Source0: libpcap-1.11.0.tar.xz
BuildRequires: gcc, make, flex, bison, dbus-devel, libnl3-devel, libusb1-devel
Vendor: Linux OSS local build

%description
Upstream source build for EL8 compatibility evaluation.

%package devel
Summary: devel files for libpcap
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
%description devel
devel files for libpcap.

%prep
%setup -q -n libpcap-1.11.0

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --enable-shared
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
rm -f %{buildroot}%{_libdir}/libpcap.a
%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE
%doc README.md
%{_libdir}/libpcap.so.*

%files devel
%{_includedir}/pcap*
%{_libdir}/libpcap.so
%{_libdir}/pkgconfig/libpcap.pc
%{_bindir}/pcap-config
%{_mandir}/man1/pcap-config.1*
%{_mandir}/man3/*
%{_mandir}/man5/*
%{_mandir}/man7/*
