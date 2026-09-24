Name: procps-ng
Version: 4.0.6
Release: 1.linuxoss%{?dist}
Summary: procps-ng upstream EL8 evaluation build
License: GPLv2+ and LGPLv2+
URL: https://gitlab.com/procps-ng/procps
Source0: procps-ng-4.0.6.tar.xz
BuildRequires: gcc, make, ncurses-devel, systemd-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n procps-ng-4.0.6

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --enable-watch8bit --with-systemd --disable-kill
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
%license COPYING COPYING.LIB
/usr/bin/*
/usr/sbin/sysctl
/usr/share/doc/procps-ng/
/usr/lib64/libproc2.so.*
/usr/share/man/*/*
/usr/share/locale/*/LC_MESSAGES/procps-ng.mo
%files devel
/usr/include/libproc2/
/usr/lib64/libproc2.so
/usr/lib64/pkgconfig/*
