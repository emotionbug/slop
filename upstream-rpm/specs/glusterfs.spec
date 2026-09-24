Name: glusterfs
Version: 11.2
Release: 1.linuxoss%{?dist}
Summary: glusterfs upstream EL8 evaluation build
License: GPLv2+ and LGPLv3+
URL: https://www.gluster.org/
Source0: glusterfs-11.2.tar.gz
BuildRequires: gcc, gcc-c++, make, autoconf, automake, libtool, flex, bison, libuuid-devel, openssl-devel, libxml2-devel, libaio-devel, libtirpc-devel, userspace-rcu-devel, python3.11-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package client-xlators
Summary: client-xlators files
%description client-xlators
client-xlators files.

%package fuse
Summary: fuse files
%description fuse
fuse files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n glusterfs-11.2
libtoolize --force
ACLOCAL_PATH=/usr/share/aclocal ./autogen.sh
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --localstatedir=/var --disable-static CC=/usr/bin/gcc PYTHON=python3.11 --disable-linux-io_uring --without-ocf --disable-georeplication --without-tcmalloc
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

mkdir -p %{buildroot}/usr/sbin
mv %{buildroot}/sbin/mount.glusterfs %{buildroot}/usr/sbin/
rmdir %{buildroot}/sbin
%check
make %{?_smp_mflags} check

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license COPYING* INSTALL
/usr/bin/*
/usr/sbin/*
%exclude /usr/sbin/glusterfs
%exclude /usr/sbin/mount.glusterfs
/usr/lib/systemd/*
/usr/libexec/*
/usr/lib/ocf/
/usr/lib/python3.11/site-packages/gluster/
/var/lib/glusterd/
/usr/share/*
%config(noreplace) /etc/*
%files libs
/usr/lib64/lib*.so.*
/usr/lib64/glusterfs/*/rpc-transport/
/usr/lib64/glusterfs/*/auth/
/usr/lib64/glusterfs/*/cloudsync-plugins/
/usr/lib64/glusterfs/*/xlator/system/
%files client-xlators
/usr/lib64/glusterfs/*/xlator/
%exclude /usr/lib64/glusterfs/*/xlator/system/
%files fuse
/usr/sbin/glusterfs
/usr/sbin/mount.glusterfs
%files devel
/usr/include/glusterfs/
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
