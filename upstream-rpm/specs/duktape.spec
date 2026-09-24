Name: duktape
Version: 2.7.0
Release: 1.linuxoss%{?dist}
Summary: duktape upstream EL8 evaluation build
License: MIT
URL: https://duktape.org/
Source0: duktape-2.7.0.tar.xz
BuildRequires: gcc, make
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n duktape-2.7.0
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

make -f Makefile.sharedlibrary %{?_smp_mflags} INSTALL_PREFIX=/usr LIBDIR=/lib64
gcc $CFLAGS -Isrc examples/cmdline/duk_cmdline.c src/duktape.c -lm -o duk
%install
make -f Makefile.sharedlibrary INSTALL_PREFIX=/usr LIBDIR=/lib64 DESTDIR=%{buildroot} install
%check
./duk -e 'if (JSON.stringify([1,2,3]) !== "[1,2,3]") { throw new Error("JSON regression"); } if (6 * 7 !== 42) { throw new Error("arithmetic regression"); }'

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE.txt
/usr/lib64/libduktape*.so.*
%files devel
/usr/lib64/libduktape*.so
/usr/include/*
/usr/lib64/pkgconfig/*
