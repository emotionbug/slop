Name: libogg
Version: 1.3.6
Release: 1.linuxoss%{?dist}
Epoch: 2
Summary: Ogg framing library
License: BSD
URL: https://xiph.org/ogg/
Source0: libogg-1.3.6.tar.xz
BuildRequires: gcc, make
Vendor: Linux OSS local build

%description
Upstream Ogg framing library, also required to build current libtheora.

%package devel
Summary: Ogg development files
Requires: %{name}%{?_isa} = %{epoch}:%{version}-%{release}
%description devel
Ogg headers and development files.

%prep
%setup -q

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --disable-static
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete

%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
%{_libdir}/libogg.so.*

%files devel
%{_includedir}/ogg/
%{_libdir}/libogg.so
%{_libdir}/pkgconfig/ogg.pc
%{_datadir}/aclocal/ogg.m4
%{_datadir}/doc/libogg/
