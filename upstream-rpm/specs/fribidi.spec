Name: fribidi
Version: 1.0.17
Release: 1.linuxoss%{?dist}
Summary: fribidi upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://github.com/fribidi/fribidi
Source0: fribidi-1.0.17.tar.xz
BuildRequires: gcc, ninja-build
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n fribidi-1.0.17
%build
meson setup build --prefix=/usr --libdir=lib64 --buildtype=debugoptimized --wrap-mode=nodownload -Ddocs=false
meson compile -C build -j2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2
%files
%license COPYING
/usr/bin/*
/usr/share/man/man1/*
/usr/lib64/libfribidi.so.*
%files devel
/usr/include/fribidi/
/usr/lib64/libfribidi.so
/usr/lib64/pkgconfig/*
