Name: jbig2dec
Version: 0.20
Release: 1.linuxoss%{?dist}
Summary: jbig2dec upstream EL8 evaluation build
License: AGPLv3+
URL: https://jbig2dec.com/
Source0: jbig2dec-0.20.tar.gz
BuildRequires: gcc, make, autoconf, automake, libtool, libpng-devel, python3
Vendor: Linux OSS local build

%description
Upstream build for EL8 evaluation. Target deployment requires separate review.

%package libs
Summary: libs files for %{name}
%description libs
libs files for %{name}.

%package devel
Summary: devel files for %{name}
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files for %{name}.

%prep
%setup -q -n jbig2dec-0.20
ACLOCAL_PATH=/usr/share/aclocal ./autogen.sh
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
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

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license COPYING
%doc README
%{_bindir}/jbig2dec
%{_mandir}/man1/jbig2dec.1*

%files libs
%license COPYING
%{_libdir}/libjbig2dec.so.*

%files devel
%{_includedir}/jbig2.h
%{_libdir}/libjbig2dec.so
%{_libdir}/pkgconfig/jbig2dec.pc
