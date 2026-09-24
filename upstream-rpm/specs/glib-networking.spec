Name: glib-networking
Version: 2.90.0
Release: 1.linuxoss%{?dist}
Summary: glib-networking upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://gitlab.gnome.org/GNOME/glib-networking
Source0: glib-networking-2.90.0.tar.xz
BuildRequires: gcc, ninja-build, glib2-devel, gnutls-devel, libproxy-devel, gsettings-desktop-schemas-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n glib-networking-2.90.0
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3

%files
/usr/lib/systemd/user/*
%license COPYING
/usr/lib64/gio/modules/*
/usr/libexec/*
/usr/share/dbus-1/services/*
/usr/share/locale/*/LC_MESSAGES/glib-networking.mo
