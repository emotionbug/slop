%global __requires_exclude ^lib(assuan|ksba|npth)\.so
Name: gnupg2
Version: 2.5.24
Release: 1.linuxoss%{?dist}
Summary: gnupg2 upstream EL8 evaluation build
License: GPLv3+
URL: https://gnupg.org/
Source0: gnupg-2.5.24.tar.bz2
BuildRequires: gcc, make, libgpg-error-devel, libgcrypt-devel, linuxoss-libassuan3, linuxoss-libksba18, linuxoss-npth18, gnutls-devel, sqlite-devel, readline-devel, bzip2-devel, zlib-devel
Requires: linuxoss-libassuan3 >= 3.0.2, linuxoss-libksba18 >= 1.8.1, linuxoss-npth18 >= 1.8
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package smime
Summary: smime files
Requires: linuxoss-libassuan3 >= 3.0.2, linuxoss-libksba18 >= 1.8.1, linuxoss-npth18 >= 1.8
%description smime
smime files.

%prep
%setup -q -n gnupg-2.5.24

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,-rpath,/opt/linux-oss/gpg-support/lib64 -Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-libassuan-prefix=/opt/linux-oss/gpg-support --with-ksba-prefix=/opt/linux-oss/gpg-support --with-npth-prefix=/opt/linux-oss/gpg-support
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
ln -s gpg %{buildroot}/usr/bin/gpg2
ln -s gpgv %{buildroot}/usr/bin/gpgv2
%check
make %{?_smp_mflags} check

%files
%license COPYING
/usr/bin/*
%exclude /usr/bin/gpgsm
/usr/libexec/*
/usr/sbin/*
/usr/share/doc/gnupg/
/usr/share/gnupg/
/usr/share/info/*
/usr/share/man/*/*
/usr/share/locale/*/LC_MESSAGES/gnupg2.mo
%files smime
/usr/bin/gpgsm
