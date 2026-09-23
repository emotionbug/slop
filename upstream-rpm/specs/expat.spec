Name:           expat
Version:        2.8.5
Release:        1.linuxoss%{?dist}
Summary:        Streaming XML parser, upstream EL8 candidate
License:        MIT
URL:            https://libexpat.github.io/
Vendor:         Linux OSS local build
Source0:        expat-2.8.5.tar.xz
BuildRequires:  gcc, gcc-c++, make, cmake

%description
Upstream Expat built with its XML parser tests enabled.

%package devel
Summary:        Expat development files
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description devel
Headers and linking metadata for Expat.

%prep
%setup -q
%build
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_SHARED_LIBS=ON \
  -DEXPAT_BUILD_TESTS=ON -DEXPAT_BUILD_DOCS=OFF -DEXPAT_BUILD_PKGCONFIG=ON
cmake --build build -- %{?_smp_mflags}
%check
ctest --test-dir build --output-on-failure
%install
DESTDIR=%{buildroot} cmake --install build

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license COPYING
%doc README.md Changes
%doc %{_docdir}/expat/AUTHORS
%doc %{_docdir}/expat/changelog
%{_bindir}/xmlwf
%{_mandir}/man1/xmlwf.1*
%{_libdir}/libexpat.so.1*
%files devel
%{_includedir}/expat*.h
%{_libdir}/libexpat.so
%{_libdir}/pkgconfig/expat.pc
%{_libdir}/cmake/expat-*/

%changelog
* Thu Sep 24 2026 Linux OSS local build - 2.8.5-1.linuxoss
- Build pinned upstream release and run parser tests.
