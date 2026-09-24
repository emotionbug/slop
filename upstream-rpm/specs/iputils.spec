Name: iputils
Version: 20250605
Release: 1.linuxoss%{?dist}
Summary: iputils upstream EL8 evaluation build
License: BSD and GPLv2+
URL: https://github.com/iputils/iputils
Source0: iputils-20250605.tar.xz
BuildRequires: gcc, ninja-build, libcap-devel, libidn2-devel, gettext
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n iputils-20250605
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --localstatedir=/var --buildtype=debugoptimized --wrap-mode=nodownload -DBUILD_MANS=false -DNO_SETCAP_OR_SUID=true
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
%check
meson test -C build --print-errorlogs --num-processes 2

%files
%license LICENSE Documentation/LICENSE.BSD3 Documentation/LICENSE.GPL2
%caps(cap_net_raw=ep) /usr/bin/ping
/usr/bin/arping
/usr/bin/clockdiff
/usr/bin/tracepath
/usr/share/locale/*/LC_MESSAGES/iputils.mo
