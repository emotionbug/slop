Name: libtiff
Version: 4.3.0
Release: 2.linuxoss%{?dist}
Summary: libtiff upstream EL8 evaluation
License: libtiff
URL: https://libtiff.gitlab.io/libtiff/
Source0: tiff_4.3.0.orig.tar.gz
Patch100: tiff-4.3.0-ubuntu-fix_TIFFReadRawStrip_man_page_typo.patch
Patch101: tiff-4.3.0-ubuntu-CVE-2022-22844.patch
Patch102: tiff-4.3.0-ubuntu-CVE-2022-0561.patch
Patch103: tiff-4.3.0-ubuntu-CVE-2022-0562.patch
Patch104: tiff-4.3.0-ubuntu-CVE-2022-0865.patch
Patch105: tiff-4.3.0-ubuntu-CVE-2022-0908.patch
Patch106: tiff-4.3.0-ubuntu-CVE-2022-0907.patch
Patch107: tiff-4.3.0-ubuntu-CVE-2022-0909.patch
Patch108: tiff-4.3.0-ubuntu-CVE-2022-0891.patch
Patch109: tiff-4.3.0-ubuntu-CVE-2022-0924.patch
Patch110: tiff-4.3.0-ubuntu-CVE-2022-1354.patch
Patch111: tiff-4.3.0-ubuntu-CVE-2022-1355.patch
Patch112: tiff-4.3.0-ubuntu-CVE-2022-2056_2057_2058.patch
Patch113: tiff-4.3.0-ubuntu-CVE-2022-2867_2868_2869.patch
Patch114: tiff-4.3.0-ubuntu-CVE-2022-3570_3598.patch
Patch115: tiff-4.3.0-ubuntu-CVE-2022-3599.patch
Patch116: tiff-4.3.0-ubuntu-CVE-2022-34526.patch
Patch117: tiff-4.3.0-ubuntu-CVE-2022-3970.patch
Patch118: tiff-4.3.0-ubuntu-CVE-2023-0795.patch
Patch119: tiff-4.3.0-ubuntu-CVE-2023-0800.patch
Patch120: tiff-4.3.0-ubuntu-CVE-2022-48281.patch
Patch121: tiff-4.3.0-ubuntu-0001-countInkNamesString-fix-UndefinedBehaviorSanitizer-a.patch
Patch122: tiff-4.3.0-ubuntu-0002-TIFFClose-avoid-NULL-pointer-dereferencing.-fix-515.patch
Patch123: tiff-4.3.0-ubuntu-0003-Consider-error-return-of-writeSelections.patch
Patch124: tiff-4.3.0-ubuntu-0004-tiffcrop-correctly-update-buffersize-after-rotateIma.patch
Patch125: tiff-4.3.0-ubuntu-0005-tiffcrop-Do-not-reuse-input-buffer-for-subsequent-im.patch
Patch126: tiff-4.3.0-ubuntu-0006-tif_luv-Check-and-correct-for-NaN-data-in-uv_encode.patch
Patch127: tiff-4.3.0-ubuntu-0007-tiffcp-fix-memory-corruption-overflow-on-hostile-ima.patch
Patch128: tiff-4.3.0-ubuntu-0008-raw2tiff-fix-integer-overflow-and-bypass-of-the-chec.patch
Patch129: tiff-4.3.0-ubuntu-CVE-2023-1916.patch
Patch130: tiff-4.3.0-ubuntu-CVE-2022-40090.patch
Patch131: tiff-4.3.0-ubuntu-CVE-2023-3576.patch
Patch132: tiff-4.3.0-ubuntu-CVE-2023-6228.patch
Patch133: tiff-4.3.0-ubuntu-CVE-2023-6277-1.patch
Patch134: tiff-4.3.0-ubuntu-CVE-2023-6277-2.patch
Patch135: tiff-4.3.0-ubuntu-CVE-2023-6277-3.patch
Patch136: tiff-4.3.0-ubuntu-CVE-2023-6277-4.patch
Patch137: tiff-4.3.0-ubuntu-CVE-2023-52356.patch
Patch138: tiff-4.3.0-ubuntu-CVE-2023-3164.patch
Patch139: tiff-4.3.0-ubuntu-CVE-2024-7006.patch
Patch140: tiff-4.3.0-ubuntu-CVE-2025-8176.patch
Patch141: tiff-4.3.0-ubuntu-CVE-2025-8534.patch
Patch142: tiff-4.3.0-ubuntu-CVE-2025-8851.patch
Patch143: tiff-4.3.0-ubuntu-CVE-2025-8961.patch
Patch144: tiff-4.3.0-ubuntu-CVE-2025-9165.patch
Patch145: tiff-4.3.0-ubuntu-CVE-2025-9900.patch
Patch146: tiff-4.3.0-ubuntu-CVE-2025-61143.patch
Patch147: tiff-4.3.0-ubuntu-CVE-2025-61144.patch
Patch148: libtiff-4.3.0-el8-2026-security.patch
BuildRequires: gcc, gcc-c++, cmake, zlib-devel, libjpeg-turbo-devel, xz-devel, libzstd-devel, libwebp-devel, jbigkit-devel
Vendor: Linux OSS local build

%description
Upstream source build. Target ABI and runtime qualification are separate.

%package devel
Summary: devel files from libtiff
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files from libtiff.

%package tools
Summary: tools files from libtiff
Requires: %{name}%{?_isa} = %{version}-%{release}
%description tools
tools files from libtiff.

%prep
%setup -q -n tiff-4.3.0
%patch100 -p1
%patch101 -p1
%patch102 -p1
%patch103 -p1
%patch104 -p1
%patch105 -p1
%patch106 -p1
%patch107 -p1
%patch108 -p1
%patch109 -p1
%patch110 -p1
%patch111 -p1
%patch112 -p1
%patch113 -p1
%patch114 -p1
%patch115 -p1
%patch116 -p1
%patch117 -p1
%patch118 -p1
%patch119 -p1
%patch120 -p1
%patch121 -p1
%patch122 -p1
%patch123 -p1
%patch124 -p1
%patch125 -p1
%patch126 -p1
%patch127 -p1
%patch128 -p1
%patch129 -p1
%patch130 -p1
%patch131 -p1
%patch132 -p1
%patch133 -p1
%patch134 -p1
%patch135 -p1
%patch136 -p1
%patch137 -p1
%patch138 -p1
%patch139 -p1
%patch140 -p1
%patch141 -p1
%patch142 -p1
%patch143 -p1
%patch144 -p1
%patch145 -p1
%patch146 -p1
%patch147 -p1
%patch148 -p1

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
export CXX=/usr/bin/g++
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_SHARED_LIBS=ON -Dtiff-tests=ON -Dtiff-docs=OFF -Dtiff-tools=ON
cmake --build build --parallel %{?_smp_build_ncpus}


%install
DESTDIR=%{buildroot} cmake --install build
find %{buildroot} -name "*.la" -delete


%check
ctest --test-dir build --output-on-failure --parallel 2

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYRIGHT
%{_libdir}/libtiff*.so.*

%files devel
%{_includedir}/tiff*.h
%{_includedir}/tiffio.hxx
%{_libdir}/libtiff*.so
%{_libdir}/pkgconfig/libtiff-4.pc
%{_mandir}/man3/*
%doc /usr/share/doc/tiff/

%files tools
%{_bindir}/*
%{_mandir}/man1/*
