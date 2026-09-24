Name: mdadm
Version: 4.4
Release: 1.linuxoss%{?dist}
Summary: mdadm upstream EL8 evaluation build
License: GPLv2+
URL: https://git.kernel.org/pub/scm/utils/mdadm/mdadm.git/
Source0: mdadm-4.4.tar.xz
BuildRequires: gcc, make, systemd-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n mdadm-4.4
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

make %{?_smp_mflags} CXFLAGS="$CFLAGS" EXTRALDFLAGS="$LDFLAGS"
%install
make DESTDIR=%{buildroot} BINDIR=/usr/sbin MANDIR=/usr/share/man install
%check
./mdadm --version
./mdadm --examine --scan
%files
%license COPYING
/usr/sbin/*
/usr/share/man/*/*
/usr/lib/udev/rules.d/*
