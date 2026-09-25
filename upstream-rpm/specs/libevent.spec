Name: libevent
Version: 2.1.8
Release: 12.linuxoss%{?dist}
Summary: libevent upstream EL8 evaluation
License: BSD
URL: https://libevent.org/
Source0: libevent-2.1.8-stable.tar.gz
Patch100: port-scripts-to-python3.patch
Patch101: libevent-2.1.8-CVE-2026-63382.patch
Patch102: libevent-2.1.8-CVE-2026-63383.patch
Patch103: libevent-2.1.8-CVE-2026-63384.patch
Patch104: libevent-2.1.8-CVE-2026-63385.patch
Patch105: libevent-2.1.8-CVE-2026-63387.patch
Patch106: libevent-2.1.8-CVE-2026-63388.patch
Patch107: libevent-CVE-2026-63379.patch
Patch108: libevent-CVE-2026-63381.patch
Patch109: libevent-el8-timing-retry.patch
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
%setup -q -n libevent-2.1.8-stable
%patch100 -p1
%patch101 -p1
%patch102 -p1
%patch103 -p1
%patch104 -p1
%patch105 -p1
%patch106 -p1
%patch107 -p1
%patch108 -p1
%patch109 -p1

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
# Backend suites contain 50 ms wall-clock assertions. Serialize them so the
# suites do not contend with one another in the isolated build container.
make -j1 check

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
