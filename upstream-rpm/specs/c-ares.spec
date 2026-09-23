Name:           c-ares
Version:        1.34.8
Release:        1.linuxoss%{?dist}
Summary:        Asynchronous DNS library, upstream EL8 candidate
License:        MIT
URL:            https://c-ares.org/
Vendor:         Linux OSS local build
Source0:        c-ares-1.34.8.tar.gz
Source1:        googletest-1.18.0.tar.gz
BuildRequires:  gcc, gcc-c++, make, cmake
%description
Upstream c-ares resolver library with upstream mock DNS and fuzz corpus tests.
%package devel
Summary:        c-ares development files
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description devel
Headers and link metadata for c-ares.
%package tools
Summary:        c-ares resolver utilities
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description tools
Command line resolver utilities from c-ares.
%prep
%setup -q -a 1
%build
# EL8's GoogleTest 1.8 lacks INSTANTIATE_TEST_SUITE_P. Build a pinned private
# test dependency; none of its code is linked into the shipped c-ares library.
cmake -S googletest-1.18.0 -B gtest-build -DCMAKE_INSTALL_PREFIX="$PWD/gtest-install" \
  -DCMAKE_CXX_STANDARD=17 -DBUILD_SHARED_LIBS=OFF -DINSTALL_GTEST=ON
cmake --build gtest-build -- %{?_smp_mflags}
cmake --install gtest-build
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCARES_SHARED=ON -DCARES_STATIC=OFF \
  -DCMAKE_PREFIX_PATH="$PWD/gtest-install" -DCMAKE_CXX_STANDARD=17 \
  -DCARES_BUILD_TESTS=ON -DCARES_BUILD_CONTAINER_TESTS=OFF
cmake --build build -- %{?_smp_mflags}
%check
ctest --test-dir build --output-on-failure
%install
DESTDIR=%{buildroot} cmake --install build
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license LICENSE.md
%doc README.md RELEASE-NOTES.md
%{_libdir}/libcares.so.2*
%files devel
%{_includedir}/ares*.h
%{_libdir}/libcares.so
%{_libdir}/pkgconfig/libcares.pc
%{_libdir}/cmake/c-ares/
%{_mandir}/man3/*
%files tools
%{_bindir}/*
%{_mandir}/man1/*
%changelog
* Thu Sep 24 2026 Linux OSS local build - 1.34.8-1.linuxoss
- Build upstream release with GoogleTest and DNS fuzz corpus checks.
