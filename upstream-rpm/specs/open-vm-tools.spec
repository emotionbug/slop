Name: open-vm-tools
Version: 13.1.0
Release: 1.linuxoss%{?dist}
Summary: open-vm-tools upstream EL8 evaluation build
License: GPLv2 and LGPLv2 and BSD
URL: https://github.com/vmware/open-vm-tools
Source0: open-vm-tools-13.1.0-25218885.tar.gz
BuildRequires: gcc, gcc-c++, make, glib2-devel, pam-devel, libtirpc-devel, libmspack-devel, libxml2-devel, libtool-ltdl-devel, systemd-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: Guest API headers and linker files
%description devel
Guest API development files.

%prep
%setup -q -n open-vm-tools-13.1.0-25218885

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --without-x --without-gtk3 --without-gtkmm3 --without-xerces --disable-docs --with-pam --with-linuxio
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%files
%license COPYING
/usr/bin/*
/usr/lib64/open-vm-tools/
/usr/lib64/lib*.so.*
/usr/lib/udev/rules.d/*
/usr/share/*
%config(noreplace) /etc/*

%files devel
/usr/include/*
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
