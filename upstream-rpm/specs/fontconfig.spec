Name: fontconfig
Version: 2.18.3
Release: 1.linuxoss%{?dist}
Summary: fontconfig upstream EL8 evaluation build
License: MIT
URL: https://gitlab.freedesktop.org/fontconfig/fontconfig
Source0: fontconfig-2.18.3.tar.gz
BuildRequires: gcc, ninja-build, freetype-devel, expat-devel, libuuid-devel, gperf
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n fontconfig-2.18.3
%build
meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Ddoc=disabled
meson compile -C build -j2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3
%files
%license COPYING
/usr/bin/*
/usr/lib64/libfontconfig.so.*
/usr/share/*
%exclude /usr/share/licenses/fontconfig/*
%config(noreplace) /etc/fonts/*
%files devel
/usr/include/fontconfig/
/usr/lib64/libfontconfig.so
/usr/lib64/pkgconfig/*
