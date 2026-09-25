Name: brotli
Version: 1.2.0
Release: 1.linuxoss%{?dist}
Summary: Brotli compression library and command line tool
License: MIT
URL: https://github.com/google/brotli
Source0: brotli-1.2.0.tar.gz
Source1: brotli-1.2.0-testdata.txz
BuildRequires: gcc, gcc-c++, cmake, make
Vendor: Linux OSS local build
%description
Brotli compression libraries retaining the libbrotli*.so.1 ABI.
%package devel
Summary: Brotli headers and pkg-config files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
Headers and link files for applications using Brotli.
%prep
%setup -q
tar -xf %{SOURCE1}
%build
export CC=/usr/bin/gcc CXX=/usr/bin/g++ PKG_CONFIG_PATH= LD_LIBRARY_PATH=
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2'
export CXXFLAGS="$CFLAGS"
export LDFLAGS='-Wl,--build-id,-z,relro,-z,now'
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_SHARED_LIBS=ON -DBROTLI_DISABLE_TESTS=OFF
cmake --build build -j2
%check
ctest --test-dir build --output-on-failure -j2
%install
DESTDIR=%{buildroot} cmake --install build
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license LICENSE
/usr/bin/*
/usr/lib64/libbrotli*.so.*
/usr/share/man/man1/*
%files devel
/usr/include/brotli/
/usr/lib64/libbrotli*.so
/usr/lib64/pkgconfig/*
/usr/share/man/man3/*
