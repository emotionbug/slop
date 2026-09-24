%global __provides_exclude ^(lib(selinux|sepol|semanage)\.so|pkgconfig\(lib(selinux|sepol|semanage)\))
%global __requires_exclude ^lib(selinux|sepol|semanage)\.so
Name: linuxoss-libsemanage311
Version: 3.11
Release: 1.linuxoss%{?dist}
Summary: linuxoss-libsemanage311 upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://github.com/SELinuxProject/selinux
Source0: libsemanage-3.11.tar.gz
BuildRequires: gcc, make, flex, bison, pcre2-devel, CUnit-devel, linuxoss-libsepol311, linuxoss-libselinux311, audit-libs-devel, bzip2-devel, libsepol-devel
Requires: linuxoss-libsepol311 = 3.11-1.linuxoss%{?dist}, linuxoss-libselinux311 = 3.11-1.linuxoss%{?dist}
BuildRequires: linuxoss-secilc311
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%global prefix /opt/linux-oss/selinux-3.11
%prep
%setup -q -n libsemanage-3.11
sed -i 's|../../secilc/secilc|%{prefix}/bin/secilc|' tests/Makefile
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

export PKG_CONFIG_PATH=%{prefix}/lib64/pkgconfig
export CFLAGS="$CFLAGS -I%{prefix}/include"
export LDFLAGS="-L%{prefix}/lib64 $LDFLAGS -Wl,-rpath,%{prefix}/lib64"
make %{?_smp_mflags} PREFIX=%{prefix} SYSCONFDIR=%{prefix}/etc LIBDIR=%{prefix}/lib64 SHLIBDIR=%{prefix}/lib64
%install
make DESTDIR=%{buildroot} PREFIX=%{prefix} SYSCONFDIR=%{prefix}/etc LIBDIR=%{prefix}/lib64 SHLIBDIR=%{prefix}/lib64 install
%check
export CFLAGS="-I%{prefix}/include"
export LDFLAGS="-L%{prefix}/lib64 -Wl,-rpath,%{prefix}/lib64"
export LD_LIBRARY_PATH=%{prefix}/lib64
make %{?_smp_mflags} PREFIX=%{prefix} SYSCONFDIR=%{prefix}/etc LIBDIR=%{prefix}/lib64 SHLIBDIR=%{prefix}/lib64 test
%files
%license LICENSE
%{prefix}/
