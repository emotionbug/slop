Name: wget
Version: 1.25.0
Release: 2.linuxoss%{?dist}
Summary: wget upstream EL8 evaluation build
License: GPLv3+
URL: https://www.gnu.org/software/wget/
Source0: wget-1.25.0.tar.gz
Patch0: wget-CVE-2026-58469.patch
Patch1: wget-CVE-2026-58470.patch
Patch2: wget-CVE-2026-58471.patch
Patch3: wget-CVE-2026-58472.patch
Patch4: wget-metalink-trim-followup.patch
Patch5: wget-metalink-ctype-followup.patch
Patch6: wget-html-size-followup.patch
BuildRequires: gcc, make, gnutls-devel, libidn2-devel, libpsl-devel, pcre2-devel, zlib-devel
BuildRequires: perl-HTTP-Daemon, perl-IO-Socket-SSL
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n wget-1.25.0
%patch0 -p1
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1
%patch5 -p1
%patch6 -p1

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-ssl=gnutls
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%files
%license COPYING
%config(noreplace) /etc/wgetrc
/usr/bin/wget
/usr/share/info/wget.info*
/usr/share/man/man1/wget.1*
/usr/share/locale/*/LC_MESSAGES/wget*.mo
