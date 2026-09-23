Name: libidn
Version: 1.44
Release: 1.linuxoss%{?dist}
Summary: libidn upstream EL8 candidate
License: LGPLv2+ and GPLv3+
URL: https://www.gnu.org/software/libidn/
Source0: libidn-1.44.tar.gz
BuildRequires: gcc, make, texinfo
Vendor: Linux OSS local build

%description
Upstream source build for EL8 compatibility evaluation.

%package devel
Summary: devel files for libidn
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
%description devel
devel files for libidn.

%prep
%setup -q -n libidn-1.44

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-java --disable-csharp
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
%license COPYING COPYING.LESSERv2 COPYING.LESSERv3 COPYINGv2
%doc README
%{_libdir}/libidn.so.*
%{_bindir}/idn
%{_mandir}/man1/idn.1*
%{_datadir}/locale/*/LC_MESSAGES/libidn.mo
%{_datadir}/emacs/site-lisp/*.el

%files devel
%{_includedir}/*.h
%{_libdir}/libidn.so
%{_libdir}/pkgconfig/libidn.pc
%{_mandir}/man3/*
%{_infodir}/libidn.info*
%{_infodir}/libidn-components.png*
