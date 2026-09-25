Name: gtk2
Version: 2.24.33
Release: 5.linuxoss%{?dist}
Summary: gtk2 upstream EL8 evaluation build
License: LGPLv2+
URL: https://www.gtk.org/
Source0: gtk+-2.24.33.tar.xz
Patch100: gtk-CVE-2024-6655.patch
BuildRequires: gcc, make, glib2-devel, atk-devel, pango-devel, gdk-pixbuf2-devel, libX11-devel, libXext-devel, libXrender-devel, libXi-devel, libXrandr-devel, libXcursor-devel, libXcomposite-devel, libXdamage-devel, cairo-devel, cups-devel, xorg-x11-server-Xvfb, xorg-x11-xauth, openbox
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n gtk+-2.24.33
%patch100 -p1

sed -i 's/__GTK_MARSHAL_MARSHAL_C__/__gtk_marshal_MARSHAL_C__/g' gtk/gtk.symbols
%build
export PKG_CONFIG_PATH= LD_LIBRARY_PATH=
export CC=/usr/bin/gcc
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-introspection --disable-gtk-doc --enable-cups
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
# EL8 GTK3 owns the unqualified helper; keep the GTK2 helper separately named.
mv %{buildroot}/usr/bin/gtk-update-icon-cache %{buildroot}/usr/bin/gtk2-update-icon-cache
sed -i '1s|python$|python3|' %{buildroot}/usr/bin/gtk-builder-convert
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
mkdir -p "$HOME/.local/share"
# RPM scriptlet cache generation is not guaranteed in the build image.
/usr/bin/gdk-pixbuf-query-loaders-64 > "$PWD/pixbuf-loaders.cache"
export GDK_PIXBUF_MODULE_FILE="$PWD/pixbuf-loaders.cache"
xvfb-run -a sh -c 'openbox >/tmp/gtk-openbox.log 2>&1 & wm=$!; trap "kill $wm" EXIT; sleep 1; make -j2 check'

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%config(noreplace) /etc/gtk-2.0/im-multipress.conf
%license COPYING
/usr/bin/*
/usr/lib64/lib*.so.*
/usr/lib64/gtk-2.0/
/usr/share/gtk-2.0/
/usr/share/gtk-doc/
/usr/share/themes/*
/usr/share/locale/*/LC_MESSAGES/gtk20*.mo
%files devel
/usr/include/gail-1.0/
/usr/include/gtk-2.0/
/usr/include/gtk-unix-print-2.0/
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
/usr/share/aclocal/*
