%global debug_package %{nil}
%global prefix /opt/linux-oss/fwupd-2.1.8
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude ^libfwupd[.]so
Name: linuxoss-fwupd-library-evaluation
Version: 2.1.8
Release: 1.linuxoss%{?dist}
Summary: Private upstream fwupd client library for EL8 evaluation
License: LGPL-2.1-or-later
URL: https://github.com/fwupd/fwupd
Source0: fwupd-2.1.8.tar.xz
BuildRequires: gcc, glib2-devel >= 2.68, libcurl-devel >= 7.62, gnutls-devel, xz-devel, zlib-devel, python3.11-jinja2
Requires: glib2 >= 2.68, libcurl >= 7.62
Vendor: Linux OSS local build
%description
Parallel client library build. Does not install or replace the system firmware
update daemon, flash firmware, or establish compatibility with hardware.
%prep
%setup -q -n fwupd-2.1.8
%build
meson setup build --prefix=%{prefix} --libdir=lib64 --buildtype=release --wrap-mode=nodownload --auto-features=disabled -Dbuild=library -Dgnutls=enabled -Dpython=/usr/bin/python3.11 -Dtests=true -Dman=false -Dfirmware-packager=false -Dmetainfo=false -Dbash_completion=false -Dfish_completion=false
meson compile -C build -j2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2 --timeout-multiplier 3
%files
%license COPYING
%{prefix}/
