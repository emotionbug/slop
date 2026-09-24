Name: nmap
%global debug_package %{nil}
Version: 7.991
Release: 1.linuxoss%{?dist}
Summary: nmap upstream EL8 evaluation build
License: NPSL
URL: https://nmap.org/
Source0: nmap-7.991.tar.bz2
BuildRequires: gcc, gcc-c++, make, openssl-devel, libpcap-devel, pcre2-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package ncat
Summary: ncat files
%description ncat
ncat files.

%prep
%setup -q -n nmap-7.991

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --without-zenmap --without-ndiff --with-libpcap=/usr --with-libpcre=included
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make check

%files
%license LICENSE
/usr/bin/nmap
/usr/bin/nping
/usr/share/nmap/
/usr/share/man/man1/nmap.1*
/usr/share/man/*/man1/nmap.1*
/usr/share/man/man1/nping.1*
%files ncat
/usr/bin/ncat
/usr/share/ncat/
/usr/share/man/man1/ncat.1*
