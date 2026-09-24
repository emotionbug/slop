%global __requires_exclude ^lib(bsd|md)\.so
Name: kbd
Version: 2.10.0
Release: 1.linuxoss%{?dist}
Summary: kbd upstream EL8 evaluation build
License: GPLv2+
URL: https://kbd-project.org/
Source0: kbd-2.10.0.tar.xz
Patch0: kbd-2.10.0-el8-test-headers.patch
BuildRequires: gcc, make, gettext-devel, check-devel, pam-devel
BuildRequires: linuxoss-bsd-compat
Requires: linuxoss-bsd-compat
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package misc
Summary: misc files
%description misc
misc files.

%prep
%setup -q -n kbd-2.10.0
%patch0 -p1
# EL8 does not declare strlcpy/strlcat in libc; these translation units use libbsd.
sed -i '1i#include <bsd/string.h>' src/libkeymap/analyze.c src/libkeymap/func.c src/libkeymap/dump.c src/libkeymap/loadkeys.c src/libkeymap/parser.c
sed -i '1i#include <bsd/string.h>' tests/libkeymap/libkeymap-test29.c

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
# Linux UAPI operation numbers verified in the pinned Linux 7.2.7 source.
# Upstream kdfontop.c handles unsupported operations on older kernels.
export CPPFLAGS='-D_FORTIFY_SOURCE=2 -I/opt/linux-oss/bsd-compat/include -DKD_FONT_OP_GET_TALL=5 -DKD_FONT_OP_SET_TALL=4'
export LDFLAGS='-L/opt/linux-oss/bsd-compat/lib64 -Wl,-rpath,/opt/linux-oss/bsd-compat/lib64 -Wl,--build-id -Wl,-z,relro,-z,now'
export LIBS='-lbsd -lmd -ldl'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --datadir=/usr/share/kbd
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%files
%license COPYING
%config(noreplace) /etc/pam.d/vlock
/usr/bin/*
/usr/share/man/*/*
/usr/share/locale/*/LC_MESSAGES/kbd.mo
%files misc
/usr/share/kbd/
