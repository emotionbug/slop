Name:           zstd
Version:        1.5.7
Release:        1.linuxoss%{?dist}
Summary:        Zstandard compression utilities, upstream EL8 candidate
License:        BSD-3-Clause OR GPL-2.0-only
URL:            https://github.com/facebook/zstd
Vendor:         Linux OSS local build
Source0:        zstd-1.5.7.tar.gz
BuildRequires:  gcc, gcc-c++, make, python3.11, zlib-devel, xz-devel, lz4-devel
Requires:       libzstd%{?_isa} = %{version}-%{release}
%description
Upstream Zstandard compression utility.
%package -n libzstd
Summary:        Zstandard shared library
%description -n libzstd
Shared Zstandard compression library.
%package -n libzstd-devel
Summary:        Zstandard development files
Requires:       libzstd%{?_isa} = %{version}-%{release}
%description -n libzstd-devel
Headers and link metadata for Zstandard.
%prep
%setup -q
%build
export CFLAGS="%{optflags}"
export ZSTD_LIB_DEPRECATED=1
make %{?_smp_mflags} PREFIX=/usr LIBDIR=/usr/lib64
%check
export CFLAGS="%{optflags}"
export ZSTD_LIB_DEPRECATED=1
# The standard native test suite includes randomized stream/corpus tests.
mkdir -p test-python
ln -s /usr/bin/python3.11 test-python/python3
export PATH="$PWD/test-python:$PATH"
make -C tests %{?_smp_mflags} test
%install
export CFLAGS="%{optflags}"
export ZSTD_LIB_DEPRECATED=1
make DESTDIR=%{buildroot} PREFIX=/usr LIBDIR=/usr/lib64 install
rm -f %{buildroot}%{_libdir}/libzstd.a
%post -n libzstd -p /sbin/ldconfig
%postun -n libzstd -p /sbin/ldconfig
%files
%license LICENSE COPYING
%doc README.md CHANGELOG
%{_bindir}/*
%{_mandir}/man1/*
%files -n libzstd
%license LICENSE COPYING
%{_libdir}/libzstd.so.1*
%files -n libzstd-devel
%{_includedir}/zstd*.h
%{_includedir}/zdict.h
%{_libdir}/libzstd.so
%{_libdir}/pkgconfig/libzstd.pc
%changelog
* Thu Sep 24 2026 Linux OSS local build - 1.5.7-1.linuxoss
- Build upstream release and run native upstream tests.
