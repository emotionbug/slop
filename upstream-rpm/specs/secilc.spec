%global prefix /opt/linux-oss/selinux-3.11
%global __requires_exclude ^libsepol\.so
Name: linuxoss-secilc311
Version: 3.11
Release: 1.linuxoss%{?dist}
Summary: Private SELinux CIL compiler for isolated policy library evaluation
License: BSD-2-Clause
URL: https://github.com/SELinuxProject/selinux
Source0: secilc-3.11.tar.gz
BuildRequires: gcc, make, xmlto, checkpolicy, linuxoss-libsepol311
Requires: linuxoss-libsepol311 = 3.11-1.linuxoss%{?dist}
Vendor: Linux OSS local build
%description
Private compiler. Does not load or change the active host SELinux policy.
%prep
%setup -q -n secilc-3.11
%build
make -j2 PREFIX=%{prefix} CFLAGS='-O2 -g -I%{prefix}/include' LDFLAGS='-L%{prefix}/lib64 -Wl,-rpath,%{prefix}/lib64 -Wl,-z,relro,-z,now'
%install
make PREFIX=%{prefix} DESTDIR=%{buildroot} install
%check
make test
%files
%license LICENSE
%{prefix}/bin/*
%{prefix}/share/man/man8/*
