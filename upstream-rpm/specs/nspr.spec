Name: nspr
Version: 4.40
Release: 1.linuxoss%{?dist}
Summary: nspr upstream EL8 evaluation build
License: MPL-2.0
URL: https://firefox-source-docs.mozilla.org/nspr/
Source0: nspr-4.40.tar.gz
BuildRequires: gcc, gcc-c++, make
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n nspr-4.40
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

mkdir build
cd build
../nspr/configure --prefix=/usr --libdir=/usr/lib64 --includedir=/usr/include/nspr --enable-64bit --enable-optimize --disable-debug
make %{?_smp_mflags}
%install
make -C build DESTDIR=%{buildroot} install
find %{buildroot} -name '*.a' -delete
%check
make -C build/pr/tests %{?_smp_mflags}
cd build/pr/tests
for t in version vercheck zerolen testfile; do ./"$t"; done

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license nspr/LICENSE
/usr/lib64/lib*.so
%files devel
/usr/bin/*
/usr/include/nspr/
/usr/lib64/pkgconfig/*
/usr/share/aclocal/*
