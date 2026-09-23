Name:           zlib
Version:        1.3.2
Release:        1.linuxoss%{?dist}
Summary:        Compression library, upstream EL8 evaluation build
License:        Zlib
URL:            https://zlib.net/
Vendor:         Linux OSS local build
Source0:        zlib-1.3.2.tar.xz
BuildRequires:  gcc, make

%description
Upstream zlib with shared-library ABI compatibility checks required before use.

%package devel
Summary:        Headers and linking files for zlib
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description devel
Headers and link metadata for building applications with zlib.

%prep
%setup -q

%build
export CFLAGS="%{optflags}"
export LDFLAGS="%{?build_ldflags}"
./configure --prefix=/usr --libdir=/usr/lib64
make %{?_smp_mflags}

%check
make test

%install
make DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_libdir}/libz.a

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE
%doc README ChangeLog
%{_libdir}/libz.so.1*

%files devel
%{_includedir}/zlib.h
%{_includedir}/zconf.h
%{_libdir}/libz.so
%{_libdir}/pkgconfig/zlib.pc
%{_mandir}/man3/zlib.3*

%changelog
* Wed Sep 23 2026 Linux OSS local build - 1.3.2-1.linuxoss
- Build upstream release with static and shared upstream tests.
