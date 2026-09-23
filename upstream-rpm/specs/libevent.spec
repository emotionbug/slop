Name: libevent
Version: 2.1.13
Release: 1.linuxoss%{?dist}
Summary: libevent upstream EL8 evaluation
License: BSD
URL: https://libevent.org/
Source0: libevent-2.1.13-stable.tar.gz
BuildRequires: gcc, make, openssl-devel
Vendor: Linux OSS local build

%description
Upstream source build. Target ABI and runtime qualification are separate.

%package devel
Summary: devel files from libevent
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files from libevent.

%prep
%setup -q -n libevent-2.1.13-stable

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static
make %{?_smp_mflags}


%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name "*.la" -delete
rm -f %{buildroot}%{_bindir}/event_rpcgen.py

%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE
%{_libdir}/libevent*.so.*

%files devel
%{_includedir}/event*.h
%{_includedir}/ev*.h
%{_includedir}/event2/
%{_libdir}/libevent*.so
%{_libdir}/pkgconfig/libevent*.pc
