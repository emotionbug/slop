Name: polkit
Version: 127
Release: 1.linuxoss%{?dist}
Summary: polkit upstream EL8 evaluation build
License: LGPLv2+
URL: https://gitlab.freedesktop.org/polkit/polkit
Source0: polkit-127.tar.gz
BuildRequires: gcc, ninja-build, glib2-devel, expat-devel, duktape-devel, pam-devel, systemd-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n polkit-127
sed -i "s/pkgconfig : 'sysusers_dir')/pkgconfig : 'sysusers_dir', default_value : '\/usr\/lib\/sysusers.d')/;s/pkgconfig : 'tmpfiles_dir')/pkgconfig : 'tmpfiles_dir', default_value : '\/usr\/lib\/tmpfiles.d')/" meson.build
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -Dintrospection=false -Dtests=true -Dos_type=redhat -Dpam_include=system-auth -Dpam_prefix=/etc/pam.d -Dsession_tracking=logind
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
# Full upstream suite needs Python >=3.12, dbusmock, PyGObject >=GI 1.64
# and a mount/user namespace. The EL8 harness failure is retained in build evidence.
# This evaluation RPM has CLI/library smoke coverage only; authorization needs a VM.
build/src/programs/pkexec --version
LD_LIBRARY_PATH="$PWD/build/src/polkit:$PWD/build/src/polkitagent" %{buildroot}/usr/bin/pkaction --version

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/*
%attr(4755,root,root) /usr/bin/pkexec
/usr/lib/polkit-1/
%attr(4755,root,root) /usr/lib/polkit-1/polkit-agent-helper-1
/usr/lib/systemd/*
/usr/lib/sysusers.d/*
/usr/share/polkit-1/
/usr/share/gettext/its/polkit.*
/usr/share/locale/*/LC_MESSAGES/polkit-1.mo
/usr/lib/tmpfiles.d/*
/usr/share/dbus-1/*
%config(noreplace) /etc/*
%files libs
/usr/lib64/libpolkit*.so.*
%files devel
/usr/include/polkit-1/
/usr/lib64/libpolkit*.so
/usr/lib64/pkgconfig/*
