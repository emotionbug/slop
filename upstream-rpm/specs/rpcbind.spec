Name: rpcbind
Version: 1.3.1
Release: 1.linuxoss%{?dist}
Summary: rpcbind upstream EL8 evaluation build
License: BSD
URL: https://sourceforge.net/projects/rpcbind/
Source0: rpcbind-1.3.1.tar.bz2
BuildRequires: gcc, make, libtirpc-devel, systemd-devel
Vendor: Linux OSS local build

Requires(pre): shadow-utils
Requires(pre): /usr/bin/getent

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n rpcbind-1.3.1

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-rpcuser=rpc --with-systemdsystemunitdir=/usr/lib/systemd/system --enable-warmstarts
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
ln -s ../sbin/rpcbind %{buildroot}/usr/bin/rpcbind
ln -s ../bin/rpcinfo %{buildroot}/usr/sbin/rpcinfo
mkdir -p %{buildroot}/etc/sysconfig
printf 'RPCBIND_ARGS=""\n' > %{buildroot}/etc/sysconfig/rpcbind
sed -i '/^ExecStart=/s| -w -f| $RPCBIND_ARGS -w -f|' %{buildroot}/usr/lib/systemd/system/rpcbind.service
sed -i '/^\[Service\]/a EnvironmentFile=-/etc/sysconfig/rpcbind' %{buildroot}/usr/lib/systemd/system/rpcbind.service
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%pre
getent group rpc >/dev/null || groupadd -r rpc
getent passwd rpc >/dev/null || useradd -r -g rpc -d /var/lib/rpcbind -s /sbin/nologin -c 'RPC Bind' rpc
%files
%config(noreplace) /etc/sysconfig/rpcbind
/usr/bin/rpcbind
%license COPYING
/usr/sbin/*
/usr/bin/rpcinfo
/usr/share/man/man8/*
/usr/lib/systemd/system/rpcbind.*
