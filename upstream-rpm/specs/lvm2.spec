Name: lvm2
Epoch: 8
Version: 2.03.42
Release: 1.linuxoss%{?dist}
Summary: lvm2 upstream EL8 evaluation build
License: GPLv2 and LGPLv2
URL: https://sourceware.org/lvm2/
Source0: LVM2.2.03.42.tgz
BuildRequires: gcc, gcc-c++, make, libaio-devel, libblkid-devel, libudev-devel, readline-devel, systemd-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.


%package -n lvm2-libs
Summary: lvm2-libs files
%description -n lvm2-libs
Upstream LVM2/device-mapper evaluation files.

%package -n lvm2-devel
Summary: lvm2-devel files
%description -n lvm2-devel
Upstream LVM2/device-mapper evaluation files.

%package -n device-mapper
Summary: device-mapper files
%description -n device-mapper
Upstream LVM2/device-mapper evaluation files.

%package -n device-mapper-libs
Summary: device-mapper-libs files
%description -n device-mapper-libs
Upstream LVM2/device-mapper evaluation files.

%package -n device-mapper-event
Summary: device-mapper-event files
%description -n device-mapper-event
Upstream LVM2/device-mapper evaluation files.

%package -n device-mapper-event-libs
Summary: device-mapper-event-libs files
%description -n device-mapper-event-libs
Upstream LVM2/device-mapper evaluation files.
%prep
%setup -q -n LVM2.2.03.42

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --enable-cmdlib --enable-dmeventd --enable-udev_sync --enable-udev_rules --enable-lvmpolld --with-thin=internal --with-cache=internal
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
make DESTDIR=%{buildroot} install_systemd_units
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make -C test unit-test
make -C test run-unit-test


%files
%license COPYING COPYING.LIB
/usr/sbin/*
%exclude /usr/sbin/dmsetup
%exclude /usr/sbin/dmstats
%exclude /usr/sbin/dmeventd
/usr/lib/systemd/*
%exclude /usr/lib/systemd/system/dm-event.*
/usr/lib/udev/*
/usr/libexec/*
/usr/share/man/*/*
%config(noreplace) /etc/lvm/*
%files -n lvm2-libs
/usr/lib64/liblvm2cmd.so.*
/usr/lib64/device-mapper/
/usr/lib64/libdevmapper-event-lvm2.so.*
%files -n lvm2-devel
/usr/include/*
/usr/lib/*.so
/usr/lib64/*.so
%files -n device-mapper
/usr/sbin/dmsetup
/usr/sbin/dmstats
%files -n device-mapper-libs
/usr/lib64/libdevmapper.so.*
%files -n device-mapper-event
/usr/sbin/dmeventd
/usr/lib/systemd/system/dm-event.*
%files -n device-mapper-event-libs
/usr/lib64/libdevmapper-event.so.*

%post -n lvm2-libs -p /sbin/ldconfig
%postun -n lvm2-libs -p /sbin/ldconfig

%post -n device-mapper-libs -p /sbin/ldconfig
%postun -n device-mapper-libs -p /sbin/ldconfig

%post -n device-mapper-event-libs -p /sbin/ldconfig
%postun -n device-mapper-event-libs -p /sbin/ldconfig
