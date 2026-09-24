%global debug_package %{nil}
Name: cups
Version: 2.4.19
Epoch: 1
Release: 1.linuxoss%{?dist}
Summary: cups upstream EL8 evaluation build
License: ASL 2.0
URL: https://openprinting.github.io/cups/
Source0: cups-2.4.19-source.tar.gz
BuildRequires: gcc, gcc-c++, make, gnutls-devel, zlib-devel, pam-devel, dbus-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package devel
Summary: devel files
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n cups-2.4.19

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-tls=gnutls --disable-systemd --disable-launchd --disable-avahi --disable-dnssd
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
# Only library and development artifacts are candidates from this recipe.
rm -rf %{buildroot}/etc %{buildroot}/var %{buildroot}/usr/sbin %{buildroot}/usr/lib %{buildroot}/usr/libexec
find %{buildroot}/usr/bin -type f ! -name cups-config -delete
rm -rf %{buildroot}/usr/share
rm -f %{buildroot}/usr/lib64/*.a
%check
make -C cups unittests

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license LICENSE
%files libs
%license LICENSE
/usr/lib64/libcups*.so.*
%files devel
/usr/include/cups/
/usr/lib64/libcups*.so
/usr/bin/cups-config
