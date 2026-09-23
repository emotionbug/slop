Name: libsolv
Version: 0.7.40
Release: 1.linuxoss%{?dist}
Summary: libsolv upstream EL8 evaluation build
License: BSD
URL: https://github.com/openSUSE/libsolv
Source0: libsolv-0.7.40.tar.gz
BuildRequires: gcc, make, cmake, rpm-devel, expat-devel, zlib-devel, xz-devel, bzip2-devel, libzstd-devel
Vendor: Linux OSS local build

%description
Upstream build for EL8 evaluation. Target deployment requires separate review.

%package devel
Summary: devel files for %{name}
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files for %{name}.

%package tools
Summary: tools files for %{name}
Requires: %{name}%{?_isa} = %{version}-%{release}
%description tools
tools files for %{name}.

%prep
%setup -q

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_INSTALL_PREFIX=/usr \
  -DCMAKE_INSTALL_LIBDIR=lib64 -DLIB=lib64 \
  -DENABLE_RPMDB=ON -DENABLE_RPMDB_LIBRPM=ON -DENABLE_RPMPKG=ON -DENABLE_RPMPKG_LIBRPM=ON \
  -DENABLE_RPMMD=ON -DENABLE_COMPS=ON -DENABLE_COMPLEX_DEPS=ON -DMULTI_SEMANTICS=ON \
  -DENABLE_CONDA=ON -DENABLE_APPDATA=ON \
  -DENABLE_LZMA_COMPRESSION=ON -DENABLE_BZIP2_COMPRESSION=ON -DENABLE_ZSTD_COMPRESSION=ON
cmake --build build -- %{?_smp_mflags}

%install
DESTDIR=%{buildroot} cmake --install build

%check
cd build
ctest --output-on-failure -j2

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE.BSD
%doc README
%{_libdir}/libsolv.so.1*
%{_libdir}/libsolvext.so.1*

%files devel
%{_includedir}/solv/
%{_libdir}/libsolv.so
%{_libdir}/libsolvext.so
%{_libdir}/pkgconfig/*.pc
%{_datadir}/cmake/Modules/FindLibSolv.cmake
%{_mandir}/man3/*

%files tools
%{_bindir}/*
%{_mandir}/man1/*
