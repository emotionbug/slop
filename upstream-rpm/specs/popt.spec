Name: popt
Version: 1.19
Release: 1.linuxoss%{?dist}
Summary: popt upstream EL8 candidate
License: MIT
URL: https://github.com/rpm-software-management/popt
Source0: popt-1.19.tar.gz
BuildRequires: gcc, make
Vendor: Linux OSS local build

%description
Upstream source build for EL8 compatibility evaluation.

%package devel
Summary: devel files for popt
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
%description devel
devel files for popt.

%prep
%setup -q -n popt-1.19

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
%doc README
%{_libdir}/libpopt.so.*
%{_datadir}/locale/*/LC_MESSAGES/popt.mo

%files devel
%{_includedir}/popt.h
%{_libdir}/libpopt.so
%{_libdir}/pkgconfig/popt.pc
%{_mandir}/man3/popt.3*
