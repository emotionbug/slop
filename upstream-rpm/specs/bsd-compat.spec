%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude (^lib(bsd|md)[.]so|^(libbsd[.]so[.]0|libmd[.]so[.]0)[(])
%global __provides_exclude ^(lib(bsd|md)[.]so|pkgconfig[(].*)
%global prefix /opt/linux-oss/bsd-compat
Name: linuxoss-bsd-compat
Version: 0.12.2
Release: 2.linuxoss%{?dist}
Summary: BSD compatibility functions for EL8 upstream builds
License: BSD and MIT
URL: https://libbsd.freedesktop.org/
Source0: libbsd-0.12.2.tar.xz
Source1: libmd-1.2.0.tar.xz
Vendor: Linux OSS local build
BuildRequires: gcc, make

%description
Private libbsd 0.12.2 and libmd 1.2.0 for newer programs needing strlcpy/strlcat
on EL8. Bundled components must be assessed separately from the package version.

%prep
%setup -q -c -T
tar -xf %{SOURCE0}
tar -xf %{SOURCE1}
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now -Wl,-rpath,%{prefix}/lib64'
cd libmd-1.2.0
./configure --prefix=%{prefix} --libdir=%{prefix}/lib64 --disable-static
make %{?_smp_mflags}
make DESTDIR="$PWD/../stage" install
cd ../libbsd-0.12.2
export MD5_CFLAGS="-I$PWD/../libmd-1.2.0/include"
export MD5_LIBS="-L$PWD/../libmd-1.2.0/src/.libs -lmd"
export LDFLAGS="-L$PWD/../libmd-1.2.0/src/.libs $LDFLAGS"
export CPPFLAGS="-I$PWD/../libmd-1.2.0/include $CPPFLAGS"
./configure --prefix=%{prefix} --libdir=%{prefix}/lib64 --disable-static
make %{?_smp_mflags}
%install
make -C libmd-1.2.0 DESTDIR=%{buildroot} install
make -C libbsd-0.12.2 DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
# Upstream's linker script embeds MD5_LIBS. Use the installed libmd location.
printf 'GROUP ( %{prefix}/lib64/libbsd.so.0 AS_NEEDED ( %{prefix}/lib64/libmd.so.0 ) )\n' > %{buildroot}%{prefix}/lib64/libbsd.so
sed -i "s|$PWD/libbsd-0.12.2/../libmd-1.2.0/src/.libs|%{prefix}/lib64|g" %{buildroot}%{prefix}/lib64/pkgconfig/*.pc
%check
export C_INCLUDE_PATH="$PWD/libmd-1.2.0/include"
make -C libmd-1.2.0 %{?_smp_mflags} check
LD_LIBRARY_PATH="$PWD/libmd-1.2.0/src/.libs" make -C libbsd-0.12.2 %{?_smp_mflags} check
%files
%license libmd-1.2.0/COPYING libbsd-0.12.2/COPYING
%{prefix}/
