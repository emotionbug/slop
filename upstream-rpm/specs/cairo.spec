Name: cairo
Version: 1.18.6
Release: 1.linuxoss%{?dist}
Summary: cairo upstream EL8 evaluation build
License: LGPLv2 or MPLv1.1
URL: https://cairographics.org/
Source0: cairo-1.18.6.tar.xz
BuildRequires: gcc, gcc-c++, ninja-build, pixman-devel, freetype-devel, fontconfig-devel, glib2-devel, libpng-devel, libXrender-devel, libxcb-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package gobject
Summary: gobject files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description gobject
gobject files.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n cairo-1.18.6
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --buildtype=debugoptimized --wrap-mode=nodownload -Dtests=disabled -Dxlib=enabled -Dxcb=enabled -Dglib=enabled -Dfreetype=enabled -Dfontconfig=enabled
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
# Bounded image/PDF/font rendering smoke; upstream visual comparison suite is not run.
cat > cairo-smoke.c <<'EOF'
#include <cairo.h>
#include <cairo-pdf.h>
#include <stdio.h>
int main(void) {
  cairo_surface_t *s=cairo_image_surface_create(CAIRO_FORMAT_ARGB32,64,64);
  cairo_t *c=cairo_create(s);
  cairo_set_source_rgb(c,1,0,0); cairo_paint(c);
  cairo_set_source_rgb(c,0,0,0); cairo_select_font_face(c,"sans",CAIRO_FONT_SLANT_NORMAL,CAIRO_FONT_WEIGHT_NORMAL);
  cairo_move_to(c,4,32); cairo_show_text(c,"EL8");
  if(cairo_status(c)!=CAIRO_STATUS_SUCCESS || cairo_surface_write_to_png(s,"smoke.png")) return 1;
  cairo_destroy(c); cairo_surface_destroy(s);
  s=cairo_image_surface_create_from_png("smoke.png");
  if(cairo_surface_status(s) || cairo_image_surface_get_width(s)!=64) return 2;
  cairo_surface_destroy(s);
  s=cairo_pdf_surface_create("smoke.pdf",64,64); c=cairo_create(s); cairo_paint(c); cairo_show_page(c);
  cairo_destroy(c); cairo_surface_finish(s);
  int rc=cairo_surface_status(s); cairo_surface_destroy(s); return rc;
}
EOF
gcc -I. -Isrc -Ibuild/src cairo-smoke.c -Lbuild/src -lcairo -o cairo-smoke
LD_LIBRARY_PATH=build/src ./cairo-smoke
test -s smoke.png && test -s smoke.pdf

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%post gobject -p /sbin/ldconfig
%postun gobject -p /sbin/ldconfig

%files
%license COPYING COPYING-LGPL-2.1 COPYING-MPL-1.1
/usr/lib64/libcairo.so.*
/usr/lib64/libcairo-script-interpreter.so.*
/usr/bin/cairo-trace
/usr/lib64/cairo/
%files gobject
/usr/lib64/libcairo-gobject.so.*
%files devel
/usr/include/cairo/
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
