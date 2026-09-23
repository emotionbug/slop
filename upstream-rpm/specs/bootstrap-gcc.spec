%global debug_package %{nil}
%global __brp_strip_lto %{nil}
%global prefix /opt/linux-oss/bootstrap/gcc-16.2.0
Name:           linuxoss-bootstrap-gcc
Version:        16.2.0
Release:        1.linuxoss%{?dist}
Summary:        Private C/C++ compiler for building the replacement RPM set
License:        GPLv3+ with exceptions and LGPLv3+
URL:            https://gcc.gnu.org/
Vendor:         Linux OSS local build
Source0:        gcc-16.2.0.tar.xz
BuildRequires:  gcc, gcc-c++, make, gmp-devel, mpfr-devel, libmpc-devel
BuildRequires:  zlib-devel, dejagnu, expect, texinfo

%description
Three-stage bootstrapped C/C++ compiler for the isolated build environment.
This private toolchain does not replace or remediate the server's GCC RPMs.
It supplies the compiler required to build newer glibc and other components.

%prep
%setup -q -n gcc-%{version}

%build
mkdir build
cd build
../configure --prefix=%{prefix} --enable-languages=c,c++ --disable-multilib \
  --enable-bootstrap --enable-checking=release --with-system-zlib \
  --enable-default-pie --enable-default-ssp --disable-libsanitizer \
  --disable-libvtv --disable-libquadmath --disable-libgomp
make %{?_smp_mflags} bootstrap

%check
# Full DejaGNU suites are run separately with explicit result review; these
# checks ensure the bootstrap compiler itself compiles and runs C and C++.
printf '#include <stdio.h>\nint main(void){puts("gcc-bootstrap-c-ok");return 0;}\n' > build/check.c
build/gcc/xgcc -Bbuild/gcc build/check.c -o build/check-c
build/check-c
printf '#include <vector>\nint main(){std::vector<int> x{1,2,3};return x.at(2)!=3;}\n' > build/check.cc
build/gcc/xg++ -Bbuild/gcc \
  -Ibuild/x86_64-pc-linux-gnu/libstdc++-v3/include \
  -Ibuild/x86_64-pc-linux-gnu/libstdc++-v3/include/x86_64-pc-linux-gnu \
  -Ilibstdc++-v3/libsupc++ \
  build/check.cc -Lbuild/x86_64-pc-linux-gnu/libstdc++-v3/src/.libs \
  -Wl,-rpath,$PWD/build/x86_64-pc-linux-gnu/libstdc++-v3/src/.libs -o build/check-cxx
build/check-cxx

%install
# GCC's top-level install target exports the original host compiler. Some
# generated checksum files are rebuilt during installation; stage-3 objects
# then require the bootstrap libstdc++, not EL8's GCC 8 runtime. Use the same
# stage-2 compiler/header/library combination used to build stage 3.
stage_root="$PWD/build"
stage_cc="$stage_root/prev-gcc/xgcc -B$stage_root/prev-gcc/"
stage_cxx="$stage_root/prev-gcc/xg++ -B$stage_root/prev-gcc/ -nostdinc++"
stage_cxx="$stage_cxx -B$stage_root/prev-x86_64-pc-linux-gnu/libstdc++-v3/src/.libs"
stage_cxx="$stage_cxx -B$stage_root/prev-x86_64-pc-linux-gnu/libstdc++-v3/libsupc++/.libs"
stage_cxx="$stage_cxx -I$stage_root/prev-x86_64-pc-linux-gnu/libstdc++-v3/include/x86_64-pc-linux-gnu"
stage_cxx="$stage_cxx -I$stage_root/prev-x86_64-pc-linux-gnu/libstdc++-v3/include -I$PWD/libstdc++-v3/libsupc++"
stage_cxx="$stage_cxx -L$stage_root/prev-x86_64-pc-linux-gnu/libstdc++-v3/src/.libs"
stage_cxx="$stage_cxx -L$stage_root/prev-x86_64-pc-linux-gnu/libstdc++-v3/libsupc++/.libs"
make -C build DESTDIR=%{buildroot} install \
  CC="$stage_cc" CXX="$stage_cxx" CC_FOR_BUILD="$stage_cc" CXX_FOR_BUILD="$stage_cxx" \
  LDFLAGS='-static-libstdc++ -static-libgcc'
find %{buildroot} -name '*.la' -delete

%files
%license COPYING COPYING3 COPYING.RUNTIME COPYING.LIB COPYING3.LIB
%{prefix}/

%changelog
* Wed Sep 23 2026 Linux OSS local build - 16.2.0-1.linuxoss
- Bootstrap private compiler for the replacement package build graph.
