%global debug_package %{nil}
Name: librsvg2
Version: 2.62.4
Release: 1.linuxoss%{?dist}
Summary: Current upstream SVG renderer built offline for EL8 evaluation
License: LGPLv2+
URL: https://gitlab.gnome.org/GNOME/librsvg
Source0: librsvg-2.62.4.tar.xz
Source1: librsvg-2.62.4-vendor.tar.xz
BuildRequires: rust, cargo, gcc, ninja-build, pango-devel, cairo-devel, gdk-pixbuf2-devel, libxml2-devel, glib2-devel
Vendor: Linux OSS local build
%description
Offline build with pinned Rust dependencies. Local checks do not establish
compatibility with all server font and image consumers.
%package devel
Summary: SVG renderer development files
Requires: librsvg2%{?_isa} = %{version}-%{release}
%description devel
Development files for the corresponding renderer.
%prep
%setup -q -n librsvg-2.62.4
tar -xJf %{SOURCE1}
# EL8 /usr/bin/python3 is 3.6; upstream build helpers require newer Python.
sed -i '1s|.*|#!/usr/bin/python3.11|' meson/*.py
%build
export CARGO_HOME="$PWD/.cargo-home" CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=2
meson setup build --prefix=/usr --libdir=lib64 --buildtype=release --wrap-mode=nodownload -Dintrospection=disabled -Dpixbuf=enabled -Dpixbuf-loader=enabled -Ddocs=disabled -Dvala=disabled -Davif=disabled -Dtests=true
meson compile -C build -j2
%install
export CARGO_HOME="$PWD/.cargo-home" CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=2
DESTDIR=%{buildroot} meson install -C build
%check
export CARGO_HOME="$PWD/.cargo-home" CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=2
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license COPYING.LIB
/usr/bin/rsvg-convert
/usr/share/thumbnailers/librsvg.thumbnailer
/usr/lib64/librsvg-2.so.*
/usr/lib64/gdk-pixbuf-2.0/
%files devel
/usr/include/librsvg-2.0/
/usr/lib64/librsvg-2.so
/usr/lib64/pkgconfig/librsvg-2.0.pc
