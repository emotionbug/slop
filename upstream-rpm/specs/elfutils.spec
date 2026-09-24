Name: elfutils
Version: 0.196
Release: 1.linuxoss%{?dist}
Summary: elfutils upstream EL8 evaluation build
License: GPLv2+ and LGPLv3+
URL: https://sourceware.org/elfutils/
Source0: elfutils-0.196.tar.bz2
BuildRequires: gcc, gcc-c++, make, zlib-devel, bzip2-devel, xz-devel, libzstd-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libelf
Summary: libelf files
%description libelf
libelf files.

%package libs
Summary: libs files
%description libs
libs files.

%package devel
Summary: devel files
%description devel
devel files.

%package libelf-devel
Summary: libelf-devel files
%description libelf-devel
libelf-devel files.

%prep
%setup -q -n elfutils-0.196

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-debuginfod --disable-libdebuginfod --disable-werror
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
rm -f %{buildroot}/usr/lib64/*.a

%check
make %{?_smp_mflags} check

%post libelf -p /sbin/ldconfig
%postun libelf -p /sbin/ldconfig

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license COPYING COPYING-GPLV2 COPYING-LGPLV3
/usr/bin/*
/usr/share/man/man1/*
/usr/share/man/man7/*
/usr/share/man/man8/*
/usr/share/locale/*/LC_MESSAGES/elfutils.mo
%files libelf
/usr/lib64/libelf*.so*
%exclude /usr/lib64/libelf.so
%files libs
/usr/lib64/libdw*.so*
%exclude /usr/lib64/libdw.so
/usr/lib64/libasm*.so*
%exclude /usr/lib64/libasm.so
%files devel
/usr/include/elfutils/
/usr/lib64/libdw.so
/usr/lib64/libasm.so
/usr/include/dwarf.h
/usr/lib64/pkgconfig/libdw.pc
%files libelf-devel
/usr/include/libelf.h
/usr/include/gelf.h
/usr/include/nlist.h
/usr/lib64/libelf.so
/usr/lib64/pkgconfig/libelf.pc
/usr/share/man/man3/*
