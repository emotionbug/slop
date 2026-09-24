Name: icu
Version: 78.3
Release: 1.linuxoss%{?dist}
Summary: icu upstream EL8 evaluation build
License: Unicode-3.0
URL: https://icu.unicode.org/
Source0: icu4c-78.3-sources.tgz
BuildRequires: gcc, gcc-c++, make, python3
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package -n libicu
Summary: ICU Unicode runtime libraries
%description -n libicu
Unicode character, locale and collation runtime libraries.
%package devel
Summary: ICU development files
Requires: libicu%{?_isa} = %{version}-%{release}
%description devel
ICU development files.

%prep
%setup -q -n icu
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

cd source
./configure --prefix=/usr --libdir=/usr/lib64 --disable-static --enable-shared
make %{?_smp_mflags}
%install
make -C source DESTDIR=%{buildroot} install
%check
make -C source %{?_smp_mflags} check

%post -n libicu -p /sbin/ldconfig
%postun -n libicu -p /sbin/ldconfig

%files
%license LICENSE
/usr/bin/*
/usr/sbin/*
/usr/share/man/*/*
%files -n libicu
%license LICENSE
/usr/lib64/libicu*.so.*
%files devel
/usr/include/unicode/
/usr/lib64/libicu*.so
/usr/lib64/icu/
/usr/lib64/pkgconfig/*
/usr/share/icu/
