%global debug_package %{nil}
Name: sysstat
Version: 12.8.0
Release: 1.linuxoss%{?dist}
Summary: sysstat upstream EL8 evaluation build
License: GPLv2+
URL: https://sysstat.github.io/
Source0: sysstat-12.8.0.tar.gz
BuildRequires: gcc, make, gettext-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n sysstat-12.8.0

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-sensors --disable-pcp --enable-install-cron=no --enable-copy-only --enable-debuginfo
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} IGNORE_FILE_ATTRIBUTES=y install
mkdir -p %{buildroot}/etc/profile.d %{buildroot}/var/log/sa
cat > %{buildroot}/etc/profile.d/colorsysstat.sh <<'EOF'
# Color sysstat output
export S_COLORS=${S_COLORS-auto}
EOF
cat > %{buildroot}/etc/profile.d/colorsysstat.csh <<'EOF'
# Color sysstat output
if ( "$?S_COLORS" == 0 ) setenv S_COLORS auto
EOF
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
./iostat -c 1 1
./mpstat 1 1
./pidstat -p SELF 1 1

%files
%license COPYING
/usr/bin/*
/usr/lib64/sa/
/usr/share/man/*/*
/usr/share/locale/*/LC_MESSAGES/sysstat.mo
/usr/lib/systemd/system/sysstat*
/usr/lib/systemd/system-sleep/sysstat.sleep
/usr/share/doc/sysstat-12.8.0/
%config(noreplace) /etc/sysconfig/*

%config(noreplace) /etc/profile.d/colorsysstat.*
%dir /var/log/sa
