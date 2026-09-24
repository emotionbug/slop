Name: pango
Version: 1.58.2
Release: 1.linuxoss%{?dist}
Summary: pango upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://pango.gnome.org/
Source0: pango-1.58.2.tar.xz
BuildRequires: gcc, ninja-build, glib2-devel, cairo-devel, fontconfig-devel, freetype-devel, harfbuzz-devel, fribidi-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n pango-1.58.2
%build
meson setup build --prefix=/usr --libdir=lib64 --buildtype=debugoptimized --wrap-mode=nodownload -Dintrospection=disabled -Ddocumentation=false -Dbuild-testsuite=true
meson compile -C build -j2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3
%files
%license COPYING
/usr/bin/*
/usr/lib64/libpango*.so.*
%files devel
/usr/include/pango-1.0/
/usr/lib64/libpango*.so
/usr/lib64/pkgconfig/*
