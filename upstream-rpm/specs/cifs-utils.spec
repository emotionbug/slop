Name: cifs-utils
Version: 7.7
Release: 1.linuxoss%{?dist}
Summary: cifs-utils upstream EL8 evaluation build
License: GPLv3+
URL: https://wiki.samba.org/index.php/LinuxCIFS_utils
Source0: cifs-utils-7.7.tar.bz2
BuildRequires: gcc, make, libtalloc-devel, keyutils-libs-devel, libcap-ng-devel, krb5-devel, pam-devel, libwbclient-devel
Vendor: Linux OSS local build

Requires(post): /usr/sbin/alternatives
Requires(postun): /usr/sbin/alternatives

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n cifs-utils-7.7

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-man --with-pamdir=/usr/lib64/security --enable-cifsupcall --enable-cifscreds --enable-cifsacl --enable-cifsidmap
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
mkdir -p %{buildroot}/etc/request-key.d %{buildroot}/etc/cifs-utils
printf '%s\n' 'create cifs.idmap * * /usr/sbin/cifs.idmap %%k' > %{buildroot}/etc/request-key.d/cifs.idmap.conf
printf '%s\n' 'create cifs.spnego * * /usr/sbin/cifs.upcall %%k' > %{buildroot}/etc/request-key.d/cifs.spnego.conf
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%post
/usr/sbin/alternatives --install /etc/cifs-utils/idmap-plugin cifs-idmap-plugin /usr/lib64/cifs-utils/idmapwb.so 20
%postun
if [ "$1" -eq 0 ]; then /usr/sbin/alternatives --remove cifs-idmap-plugin /usr/lib64/cifs-utils/idmapwb.so; fi
%files
%dir /etc/cifs-utils
%ghost /etc/cifs-utils/idmap-plugin
%config(noreplace) /etc/request-key.d/cifs.*.conf
%license COPYING
/usr/bin/*
/usr/sbin/*
/sbin/*
/usr/lib64/cifs-utils/
/usr/lib64/security/pam_cifscreds.so
/usr/include/cifsidmap.h
