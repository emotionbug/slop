Name: pam
Version: 1.7.2
Release: 1.linuxoss%{?dist}
Summary: pam upstream EL8 evaluation build
License: BSD and GPLv2+
URL: https://github.com/linux-pam/linux-pam
Source0: Linux-PAM-1.7.2.tar.xz
BuildRequires: gcc, ninja-build, libselinux-devel, audit-libs-devel, libxcrypt-devel, gdbm-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
Requires: pam%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n Linux-PAM-1.7.2
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Ddocs=disabled -Deconf=disabled -Dpam_lastlog=enabled -Dsecuredir=/usr/lib64/security -Dsconfigdir=/etc/security
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/lib64/libpam*.so.*
/usr/lib64/security/
/usr/sbin/*
/usr/share/pam/
/usr/lib/systemd/system/pam_namespace.service
/usr/share/locale/*/LC_MESSAGES/Linux-PAM.mo
%config(noreplace) /etc/security/*
%files devel
/usr/include/security/
/usr/lib64/libpam*.so
/usr/lib64/pkgconfig/*
