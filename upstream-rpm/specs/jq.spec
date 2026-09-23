Name: jq
Version: 1.8.2
Release: 1.linuxoss%{?dist}
Summary: jq upstream EL8 candidate
License: MIT
URL: https://jqlang.org/
Source0: jq-1.8.2.tar.gz
BuildRequires: gcc, make, oniguruma-devel
Vendor: Linux OSS local build

%description
Upstream source build for EL8 compatibility evaluation.

%package devel
Summary: devel files for jq
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
%description devel
devel files for jq.

%prep
%setup -q -n jq-1.8.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-maintainer-mode --with-oniguruma=/usr
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
%{_docdir}/jq/AUTHORS
%{_docdir}/jq/COPYING
%{_docdir}/jq/NEWS.md
%{_bindir}/jq
%{_libdir}/libjq.so.*
%{_mandir}/man1/jq.1*

%files devel
%{_includedir}/jq.h
%{_includedir}/jv.h
%{_libdir}/libjq.so
%{_libdir}/pkgconfig/libjq.pc
