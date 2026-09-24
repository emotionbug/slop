Name: util-linux
Version: 2.42.2
Release: 1.linuxoss%{?dist}
Summary: util-linux upstream EL8 evaluation build
License: GPLv2+ and LGPLv2+ and BSD
URL: https://www.kernel.org/pub/linux/utils/util-linux/
Source0: util-linux-2.42.2.tar.gz
BuildRequires: gcc, make, ncurses-devel, readline-devel, libselinux-devel, libcap-ng-devel, systemd-devel, pam-devel, sqlite-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package -n libblkid
Summary: libblkid runtime
%description -n libblkid
libblkid runtime.

%package -n libfdisk
Summary: libfdisk runtime
%description -n libfdisk
libfdisk runtime.

%package -n libmount
Summary: libmount runtime
%description -n libmount
libmount runtime.

%package -n libsmartcols
Summary: libsmartcols runtime
%description -n libsmartcols
libsmartcols runtime.

%package -n libuuid
Summary: libuuid runtime
%description -n libuuid
libuuid runtime.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%setup -q -n util-linux-2.42.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-makeinstall-chown --disable-makeinstall-setuid --disable-kill --disable-su --disable-runuser --disable-chfn-chsh --disable-login --disable-nologin --disable-lastb --disable-last --disable-pylibmount --without-python --without-systemd --disable-liblastlog2 --disable-lastlog2 --disable-pam-lastlog2
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
for dir in bin sbin; do
  if test -d %{buildroot}/$dir; then
    mkdir -p %{buildroot}/usr/$dir
    mv %{buildroot}/$dir/* %{buildroot}/usr/$dir/
    rmdir %{buildroot}/$dir
  fi
done
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%files
%license COPYING*
/usr/bin/*
/usr/share/doc/util-linux/
/usr/sbin/*
/usr/share/man/*/*
/usr/share/locale/*/LC_MESSAGES/util-linux.mo
/usr/share/bash-completion/completions/*

%files -n libblkid
/usr/lib64/libblkid.so.*

%files -n libfdisk
/usr/lib64/libfdisk.so.*

%files -n libmount
/usr/lib64/libmount.so.*

%files -n libsmartcols
/usr/lib64/libsmartcols.so.*

%files -n libuuid
/usr/lib64/libuuid.so.*

%files devel
/usr/include/*
/usr/lib64/*.so
/usr/lib64/pkgconfig/*

%post -n libblkid -p /sbin/ldconfig
%postun -n libblkid -p /sbin/ldconfig

%post -n libfdisk -p /sbin/ldconfig
%postun -n libfdisk -p /sbin/ldconfig

%post -n libmount -p /sbin/ldconfig
%postun -n libmount -p /sbin/ldconfig

%post -n libsmartcols -p /sbin/ldconfig
%postun -n libsmartcols -p /sbin/ldconfig

%post -n libuuid -p /sbin/ldconfig
%postun -n libuuid -p /sbin/ldconfig
