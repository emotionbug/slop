Name: libbpf
Version: 1.7.0
Release: 1.linuxoss%{?dist}
Summary: libbpf upstream EL8 evaluation build
License: LGPLv2+ or BSD
URL: https://github.com/libbpf/libbpf
Source0: libbpf-1.7.0.tar.gz
BuildRequires: gcc, make, elfutils-libelf-devel, zlib-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n libbpf-1.7.0
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

make -C src %{?_smp_mflags} BUILD_STATIC_ONLY=0
%install
make -C src DESTDIR=%{buildroot} PREFIX=/usr LIBDIR=/usr/lib64 install
rm -f %{buildroot}/usr/lib64/libbpf.a
%check
test -s src/libbpf.so.1.7.0

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE LICENSE.BSD-2-Clause LICENSE.LGPL-2.1
/usr/lib64/libbpf.so.*
%files devel
/usr/include/bpf/
/usr/lib64/libbpf.so
/usr/lib64/pkgconfig/libbpf.pc
