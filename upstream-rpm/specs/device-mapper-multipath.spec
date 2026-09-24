Name: device-mapper-multipath
Version: 0.15.1
Release: 1.linuxoss%{?dist}
Summary: device-mapper-multipath upstream EL8 evaluation build
License: GPLv2
URL: https://github.com/opensvc/multipath-tools
Source0: multipath-tools-0.15.1.tar.gz
BuildRequires: gcc, make, device-mapper-devel, libaio-devel, systemd-devel, json-c-devel, userspace-rcu-devel, libmount-devel, libcmocka-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package -n kpartx
Summary: Partition mapping tool
%description -n kpartx
Partition mapping tool.

%prep
%setup -q -n multipath-tools-0.15.1
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
# Upstream selects its own _FORTIFY_SOURCE level; avoid a conflicting redefinition.
export CPPFLAGS=''
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

make %{?_smp_mflags} CC=/usr/bin/gcc LIB=lib64
%install
make CC=/usr/bin/gcc DESTDIR=%{buildroot} LIB=lib64 install
mkdir -p %{buildroot}/usr/sbin
if test -d %{buildroot}/sbin; then mv %{buildroot}/sbin/* %{buildroot}/usr/sbin/; rmdir %{buildroot}/sbin; fi
mkdir -p %{buildroot}/usr/lib64
if test -d %{buildroot}/lib64; then cp -a %{buildroot}/lib64/. %{buildroot}/usr/lib64/; rm -rf %{buildroot}/lib64; fi
%check
make %{?_smp_mflags} CC=/usr/bin/gcc LIB=lib64 test

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license LICENSES/*
/usr/sbin/*
%exclude /usr/sbin/kpartx
/usr/lib/systemd/*
/usr/lib/tmpfiles.d/*
/usr/lib/modules-load.d/*
/usr/lib/udev/*
/usr/share/man/*/*
%files libs
/usr/lib64/*
/usr/include/*
%files -n kpartx
/usr/sbin/kpartx
