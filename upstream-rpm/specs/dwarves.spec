Name:           dwarves
Version:        1.32
Release:        1.linuxoss%{?dist}
Summary:        DWARF and BTF tools required for latest kernel builds
License:        GPLv2 and LGPLv2.1 and BSD
URL:            https://git.kernel.org/pub/scm/devel/pahole/pahole.git
Vendor:         Linux OSS local build
Source0:        dwarves-1.32.tar.xz
BuildRequires:  gcc, gcc-c++, make, cmake, elfutils-devel, zlib-devel, python3.11
Provides:       bundled(libbpf) = 1.8

%description
Upstream pahole and related DWARF/BTF tools for the isolated kernel builder.
The upstream release bundles libbpf; its source is included in the SRPM.

%prep
%setup -q

%build
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 \
  -DPython3_EXECUTABLE=/usr/bin/python3.11 -DLIBBPF_EMBEDDED=ON
cmake --build build -- %{?_smp_mflags}

%check
export PATH="$PWD/build:$PATH"
tests/tests --jobs 4

%install
DESTDIR=%{buildroot} cmake --install build

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
%{_bindir}/*
%{_libdir}/*
%{_includedir}/*
%{_mandir}/man1/*
%{_datadir}/dwarves/

%changelog
* Wed Sep 23 2026 Linux OSS local build - 1.32-1.linuxoss
- Prepare the BTF generator for the kernel build and run upstream checks.
