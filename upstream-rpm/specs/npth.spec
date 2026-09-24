%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude (^(libnpth[.]so[.]0)[(])
%global __provides_exclude ^(libnpth[.]so|pkgconfig[(].*)
Name: linuxoss-npth18
Version: 1.8
Release: 2.linuxoss%{?dist}
Summary: linuxoss-npth18 upstream EL8 evaluation build
License: LGPLv2.1+
URL: https://gnupg.org/
Source0: npth-1.8.tar.bz2
BuildRequires: gcc, make, libgpg-error-devel
Vendor: Linux OSS local build

%description
Parallel GnuPG build dependency, installed under /opt.
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n npth-1.8

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/opt/linux-oss/gpg-support --libdir=/opt/linux-oss/gpg-support/lib64 --sysconfdir=/etc --disable-static --enable-install-npth-config
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir %{buildroot}/opt/linux-oss/gpg-support/share/info/dir

%check
make %{?_smp_mflags} check

%files
%license COPYING*
/opt/linux-oss/gpg-support/
