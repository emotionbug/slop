Name: glib2
Version: 2.90.0
Release: 1.linuxoss%{?dist}
Summary: glib2 upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://gitlab.gnome.org/GNOME/glib
Source0: glib-2.90.0.tar.xz
BuildRequires: gcc, gcc-c++, ninja-build, pcre2-devel >= 10.40, libffi-devel, zlib-devel, libselinux-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n glib-2.90.0
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Dintrospection=disabled -Ddocumentation=false -Dman-pages=disabled -Dsysprof=disabled -Dlibmount=disabled
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
/usr/lib64/lib*.so.*
/usr/lib64/gio/
/usr/libexec/*
/usr/bin/gapplication
/usr/bin/gi-*
/usr/share/bash-completion/completions/*
/usr/bin/gio
/usr/bin/gio-querymodules
/usr/bin/glib-compile-schemas
/usr/bin/gsettings
/usr/bin/gdbus
/usr/bin/gresource
/usr/share/glib-2.0/
%exclude /usr/share/glib-2.0/codegen/
%exclude /usr/share/glib-2.0/gdb/
%exclude /usr/share/glib-2.0/schemas/gschema.dtd
/usr/share/locale/*/LC_MESSAGES/glib20.mo
%files devel
/usr/include/glib-2.0/
/usr/include/gio-unix-2.0/
/usr/lib64/glib-2.0/
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
/usr/bin/glib-gettextize
/usr/share/gettext/its/*
/usr/share/systemtap/tapset/*/*
/usr/bin/glib-genmarshal
/usr/bin/glib-mkenums
/usr/bin/glib-compile-resources
/usr/bin/gdbus-codegen
/usr/bin/gobject-query
/usr/bin/gtester*
/usr/share/glib-2.0/codegen/
/usr/share/glib-2.0/gdb/
/usr/share/glib-2.0/schemas/gschema.dtd
/usr/share/aclocal/*
/usr/share/gdb/*
