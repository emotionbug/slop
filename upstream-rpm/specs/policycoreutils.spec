%global __requires_exclude ^lib(selinux|sepol|semanage)\.so
Name: policycoreutils
Version: 3.11
Release: 1.linuxoss%{?dist}
Summary: policycoreutils upstream EL8 evaluation build
License: GPLv2+
URL: https://github.com/SELinuxProject/selinux
Source0: policycoreutils-3.11.tar.gz
BuildRequires: gcc, make, linuxoss-libsepol311, linuxoss-libselinux311, linuxoss-libsemanage311, pam-devel, audit-libs-devel, libcap-devel
Requires: linuxoss-libsepol311, linuxoss-libselinux311, linuxoss-libsemanage311
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n policycoreutils-3.11
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

export PKG_CONFIG_PATH=/opt/linux-oss/selinux-3.11/lib64/pkgconfig
export CFLAGS="$CFLAGS -I/opt/linux-oss/selinux-3.11/include"
export LDFLAGS="-L/opt/linux-oss/selinux-3.11/lib64 $LDFLAGS -Wl,-rpath,/opt/linux-oss/selinux-3.11/lib64"
make %{?_smp_mflags} PREFIX=/usr LIBDIR=/usr/lib64
%install
make DESTDIR=%{buildroot} PREFIX=/usr LIBDIR=/usr/lib64 install
mkdir -p %{buildroot}/usr/sbin
mv %{buildroot}/sbin/* %{buildroot}/usr/sbin/
rmdir %{buildroot}/sbin
%check
%{buildroot}/usr/sbin/sestatus > sestatus-smoke.txt
grep -q 'SELinux status' sestatus-smoke.txt
%files
%license LICENSE
/usr/bin/*
/usr/sbin/*
/usr/libexec/*
/usr/share/*
%config(noreplace) /etc/*
