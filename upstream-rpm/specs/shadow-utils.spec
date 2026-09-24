Name: shadow-utils
Version: 4.20.3
Epoch: 2
Release: 1.linuxoss%{?dist}
Summary: shadow-utils upstream EL8 evaluation build
License: BSD and GPLv2+
URL: https://github.com/shadow-maint/shadow
Source0: shadow-4.20.3.tar.xz
BuildRequires: gcc, make, pam-devel, libselinux-devel, libsemanage-devel, audit-libs-devel, libxcrypt-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n shadow-4.20.3

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2 -D_GNU_SOURCE'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-libpam --with-selinux --without-libbsd --without-su --disable-man --disable-account-tools-setuid --disable-nls
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
# These programs belong to other EL8 source packages; preserve their owners.
mkdir -p %{buildroot}/usr/bin %{buildroot}/usr/sbin
if test -d %{buildroot}/bin; then mv %{buildroot}/bin/* %{buildroot}/usr/bin/; rmdir %{buildroot}/bin; fi
if test -d %{buildroot}/sbin; then mv %{buildroot}/sbin/* %{buildroot}/usr/sbin/; rmdir %{buildroot}/sbin; fi
rm -f %{buildroot}/usr/bin/login %{buildroot}/usr/bin/su %{buildroot}/usr/bin/passwd %{buildroot}/usr/sbin/nologin
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%files
%license COPYING
/usr/bin/*
/usr/sbin/*
/usr/lib64/*
/usr/include/*
%config(noreplace) /etc/*
