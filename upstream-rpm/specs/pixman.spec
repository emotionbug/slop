Name: pixman
Version: 0.46.4
Release: 1.linuxoss%{?dist}
Summary: Pixel manipulation library for EL8
License: MIT
URL: https://cairographics.org/
Source0: pixman-0.46.4.tar.gz
Vendor: Linux OSS local build
BuildRequires: gcc, make, ninja-build, libpng-devel
%description
Upstream dependency required by newer Cairo. Local compatibility evaluation.
%package devel
Summary: Pixman headers
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
Development files.
%prep
%setup -q -n pixman-0.46.4
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
meson setup build --prefix=/usr --libdir=lib64 --buildtype=debugoptimized --wrap-mode=nodownload
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license COPYING
/usr/lib64/libpixman-1.so.*
%files devel
/usr/include/pixman-1/
/usr/lib64/libpixman-1.so
/usr/lib64/pkgconfig/pixman-1.pc
