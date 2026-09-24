Name: gdk-pixbuf2
Version: 2.44.8
Release: 1.linuxoss%{?dist}
Summary: gdk-pixbuf2 upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://gitlab.gnome.org/GNOME/gdk-pixbuf
Source0: gdk-pixbuf-2.44.8.tar.xz
BuildRequires: gcc, ninja-build, glib2-devel, libpng-devel, libjpeg-turbo-devel, libtiff-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package modules
Summary: modules files
%description modules
modules files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n gdk-pixbuf-2.44.8
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Dintrospection=disabled -Dman=false -Dinstalled_tests=false -Dglycin=disabled -Dothers=enabled -Dlegacy_xpm=enabled
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/*
/usr/share/thumbnailers/*
/usr/lib64/libgdk_pixbuf-2.0.so.*
/usr/share/locale/*/LC_MESSAGES/gdk-pixbuf.mo
%files modules
/usr/lib64/gdk-pixbuf-2.0/
%files devel
/usr/include/gdk-pixbuf-2.0/
/usr/lib64/libgdk_pixbuf-2.0.so
/usr/lib64/pkgconfig/*
