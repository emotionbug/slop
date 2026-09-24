Name: cronie
Version: 1.7.2
Release: 1.linuxoss%{?dist}
Summary: cronie upstream EL8 evaluation build
License: ISC and BSD
URL: https://github.com/cronie-crond/cronie
Source0: cronie-1.7.2.tar.gz
BuildRequires: gcc, make, pam-devel, libselinux-devel, audit-libs-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package anacron
Summary: anacron files
%description anacron
anacron files.

%prep
%setup -q -n cronie-1.7.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-pam --with-selinux --with-audit --with-inotify --with-systemdsystemunitdir=/usr/lib/systemd/system --localstatedir=/var
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
install -Dm0644 contrib/cronie.systemd %{buildroot}/usr/lib/systemd/system/crond.service
install -Dm0644 crond.sysconfig %{buildroot}/etc/sysconfig/crond
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
src/crond -V
src/crontab -V
anacron/anacron -V

%files
%license COPYING
/usr/bin/crontab
/usr/bin/cronnext
/usr/sbin/crond
/usr/share/man/man1/*
/usr/share/man/man5/crontab.*
/usr/share/man/man8/cron.*
/usr/share/man/man8/crond.*
%config(noreplace) /etc/pam.d/crond
%config(noreplace) /etc/sysconfig/crond
/usr/lib/systemd/system/crond.service
%files anacron
/usr/sbin/anacron
/usr/share/man/man5/anacrontab.*
/usr/share/man/man8/anacron.*
