Name:           binutils
Version:        2.47
Release:        3.linuxoss%{?dist}
Summary:        GNU binary utilities, upstream EL8 evaluation build
License:        GPLv3+
URL:            https://www.gnu.org/software/binutils/
Vendor:         Linux OSS local build
Source0:        binutils-2.47.tar.xz
Patch100: binutils-2.47-gcc8-lto.patch
Source1:        gnu-standards.info.tar.gz
BuildRequires:  gcc, gcc-c++, make, bison, flex, texinfo, zlib-devel
BuildRequires:  dejagnu, expect

%description
GNU assembler, linker and binary utilities built from the upstream release.
This candidate must pass dependency and reverse-dependency validation before
being deployed to an existing RHEL system.

%prep
%setup -q
%patch100 -p1

%build
# EL8's RPM debugedit supports DWARF 4, while GCC 16 defaults to DWARF 5.
# Preserve separate debug information and build IDs instead of disabling it.
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2'
export CXXFLAGS="$CFLAGS"
# Old libiberty preprocessor-only header probes treat fortify's no-optimization
# warning as a missing header. Keep fortify with the optimized compiler flags.
export CPPFLAGS=''
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
mkdir build
cd build
../configure --prefix=/usr --libdir=/usr/lib64 --enable-shared \
  --enable-plugins --enable-ld=default --enable-gold --enable-default-hash-style=gnu \
  --enable-deterministic-archives --disable-werror --disable-gprofng \
  --without-debuginfod --without-zstd --with-system-zlib
make %{?_smp_mflags}

%check
export PATH="$PWD/build/binutils:$PATH"
# GAS invokes objdump/readelf from PATH: using EL8's system objdump 2.30
# produces false test failures for the new instruction set and output format.
make -C build %{?_smp_mflags} check

%install
make -C build DESTDIR=%{buildroot} install
# EL8's outgoing binutils postun unconditionally removes this Info index.
# Keep the real GNU manual present during the upgrade transaction.
tar -xzf %{SOURCE1} -C %{buildroot}%{_infodir} standards.info
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%files
%license COPYING COPYING3 COPYING.LIB COPYING3.LIB
%doc README
%{_bindir}/*
%{_libdir}/*
%{_includedir}/*
%{_datadir}/locale/*/LC_MESSAGES/*.mo
%{_infodir}/*
%{_mandir}/man1/*
%{_prefix}/x86_64-pc-linux-gnu/

%changelog
* Wed Sep 23 2026 Linux OSS local build - 2.47-1.linuxoss
- Build upstream source and run the upstream tests.
