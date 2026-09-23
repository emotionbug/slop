Name: libXpm
Version: 3.5.19
Release: 1.linuxoss%{?dist}
Summary: libXpm upstream EL8 candidate
License: MIT
URL: https://www.x.org/
Source0: libXpm-3.5.19.tar.xz
BuildRequires: gcc, make, libX11-devel, libXt-devel, libXext-devel
Vendor: Linux OSS local build

%description
Upstream source build for EL8 compatibility evaluation.

%package devel
Summary: devel files for libXpm
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
%description devel
devel files for libXpm.

%package tools
Summary: tools files for libXpm
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
%description tools
tools files for libXpm.

%prep
%setup -q -n libXpm-3.5.19

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
%doc README.md
%{_libdir}/libXpm.so.*

%files devel
%{_includedir}/X11/xpm.h
%{_libdir}/libXpm.so
%{_libdir}/pkgconfig/xpm.pc
%{_mandir}/man3/*

%files tools
%{_bindir}/cxpm
%{_bindir}/sxpm
%{_mandir}/man1/*
