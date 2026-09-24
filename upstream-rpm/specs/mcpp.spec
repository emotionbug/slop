%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude (^libmcpp[.]so|^(libmcpp[.]so[.]0)[(])
%global prefix /opt/linux-oss/mcpp-2.7.2
%global __provides_exclude ^(libmcpp[.]so|pkgconfig[(].*)
Name: linuxoss-mcpp-evaluation
Version: 2.7.2
Release: 3.linuxoss%{?dist}
Summary: Private MCPP with Debian maintenance and CVE-2019-14274 patches
License: BSD-2-Clause
URL: https://mcpp.sourceforge.net/
Source0: mcpp-2.7.2.tar.gz
Source1: mcpp_2.7.2-5.3.debian.tar.xz
Source2: mcpp-test-do_msg01
Source3: mcpp-test-do_msg02
Patch0: mcpp-zero-length-line.patch
BuildRequires: gcc, make, patch, valgrind, autoconf, automake, libtool
Vendor: Linux OSS local build
%description
Last upstream release plus pinned Debian patches. Parallel evaluation runtime;
does not replace the distribution mcpp/libmcpp packages.
%prep
%setup -q -n mcpp-2.7.2
tar -xJf %{SOURCE1} debian/patches
while read -r p; do patch -p1 < "debian/patches/$p"; done < debian/patches/series
%patch0 -p1
%build
autoreconf -fiv
CC=/usr/bin/gcc ./configure --prefix=%{prefix} --libdir=%{prefix}/lib64 --enable-mcpplib --disable-static LDFLAGS='-Wl,-rpath,%{prefix}/lib64 -Wl,-z,relro,-z,now'
make -j2
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
%check
printf '#define VALUE 42\nVALUE\n' > example.c
LD_LIBRARY_PATH="$PWD/src/.libs" src/mcpp -P example.c > actual.txt
grep -q 42 actual.txt
for input in %{SOURCE2} %{SOURCE3}; do
  rc=0
  LD_LIBRARY_PATH="$PWD/src/.libs" valgrind --error-exitcode=99 --leak-check=no src/.libs/mcpp "$input" > /dev/null 2> "$(basename "$input").valgrind.log" || rc=$?
  test "$rc" -eq 0 || test "$rc" -eq 22
  grep -q "ERROR SUMMARY: 0 errors" "$(basename "$input").valgrind.log"
done
%files
%license LICENSE
%{prefix}/
