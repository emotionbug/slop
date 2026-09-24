Name: avahi
Version: 0.8
Release: 1.linuxoss%{?dist}
Summary: avahi upstream EL8 evaluation build
License: LGPLv2+
URL: https://avahi.org/
Source0: avahi-0.8.tar.gz
BuildRequires: gcc, make, dbus-devel, libdaemon-devel, glib2-devel, expat-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package devel
Summary: devel files
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n avahi-0.8

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-qt3 --disable-qt4 --disable-qt5 --disable-gtk --disable-gtk3 --disable-python --disable-mono --disable-doxygen-doc --disable-manpages --disable-autoipd --disable-core-docs --disable-gobject --disable-libevent
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
# Only client/common libraries are evaluated here; no daemon replacement.
rm -rf %{buildroot}/etc %{buildroot}/var %{buildroot}/run %{buildroot}/usr/bin %{buildroot}/usr/sbin %{buildroot}/usr/lib %{buildroot}/usr/share
rm -f %{buildroot}/usr/lib64/libavahi-glib* %{buildroot}/usr/lib64/libavahi-core*
rm -f %{buildroot}/usr/lib64/pkgconfig/avahi-glib.pc %{buildroot}/usr/lib64/pkgconfig/avahi-core.pc
rm -rf %{buildroot}/usr/include/avahi-glib %{buildroot}/usr/include/avahi-core
%check
make %{?_smp_mflags} check

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license LICENSE
%files libs
%license LICENSE
/usr/lib64/libavahi-common.so.*
/usr/lib64/libavahi-client.so.*
%files devel
/usr/include/avahi-common/
/usr/include/avahi-client/
/usr/lib64/libavahi-common.so
/usr/lib64/libavahi-client.so
/usr/lib64/pkgconfig/*
