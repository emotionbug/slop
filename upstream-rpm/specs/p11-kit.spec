Name: p11-kit
Version: 0.26.5
Release: 1.linuxoss%{?dist}
Summary: p11-kit upstream EL8 evaluation build
License: BSD
URL: https://p11-glue.github.io/p11-glue/p11-kit.html
Source0: p11-kit-0.26.5.tar.xz
BuildRequires: gcc, make, ninja-build, libffi-devel, libtasn1-devel, systemd-devel, gettext
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package trust
Summary: trust files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description trust
trust files.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n p11-kit-0.26.5
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

meson setup build --prefix=/usr --libdir=lib64 --sysconfdir=/etc --buildtype=debugoptimized --wrap-mode=nodownload -Dtrust_module=enabled -Dtrust_paths=/etc/pki/ca-trust/source:/usr/share/pki/ca-trust-source -Dgtk_doc=false -Dman=false -Dsystemd=enabled
meson compile -C build -j 2
%install
DESTDIR=%{buildroot} meson install -C build
mkdir -p %{buildroot}/etc/pkcs11/modules
%check
meson test -C build --print-errorlogs --num-processes 2

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%dir /etc/pkcs11/modules
%license COPYING
/usr/bin/p11-kit
/usr/lib64/libp11-kit.so.*
/usr/lib64/p11-kit-proxy.so
/usr/lib64/pkcs11/p11-kit-client.so
%config(noreplace) /etc/pkcs11/pkcs11.conf.example
/usr/libexec/p11-kit/
/usr/share/locale/*/LC_MESSAGES/p11-kit.mo
/usr/share/zsh/site-functions/_p11-kit
/usr/lib/systemd/user/p11-kit*
%files trust
/usr/bin/trust
/usr/lib64/pkcs11/p11-kit-trust.so
/usr/share/p11-kit/modules/p11-kit-trust.module
/usr/share/zsh/site-functions/_trust
%files devel
/usr/include/p11-kit-1/
/usr/lib64/libp11-kit.so
/usr/lib64/pkgconfig/p11-kit-1.pc
