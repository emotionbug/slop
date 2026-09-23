Name: oniguruma
Version: 6.9.10
Release: 2.linuxoss%{?dist}
Summary: oniguruma upstream EL8 candidate
License: BSD
URL: https://github.com/kkos/oniguruma
Source0: onig-6.9.10.tar.gz
Patch0: oniguruma-el8-posix-symbols.patch
BuildRequires: gcc, make
Vendor: Linux OSS local build

%description
Upstream source build for EL8 compatibility evaluation.

%package devel
Summary: devel files for oniguruma
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
%description devel
devel files for oniguruma.

%prep
%setup -q -n onig-6.9.10
%patch0 -p1

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --enable-posix-api
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
%{_libdir}/libonig.so.*

%files devel
%{_includedir}/onig*.h
%{_libdir}/libonig.so
%{_libdir}/pkgconfig/oniguruma.pc
%{_bindir}/onig-config
