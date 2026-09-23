Name: pkgconf
Version: 3.0.7
Release: 1.linuxoss%{?dist}
Summary: pkgconf upstream EL8 evaluation build
License: ISC
URL: https://github.com/pkgconf/pkgconf
Source0: pkgconf-3.0.7.tar.xz
BuildRequires: gcc, make
Vendor: Linux OSS local build
Requires: libpkgconf%{?_isa} = %{version}-%{release}

%description
Upstream build for EL8 evaluation. Target deployment requires separate review.

%package -n libpkgconf
Summary: pkgconf shared library
%description -n libpkgconf
Shared dependency metadata parser.

%package devel
Summary: devel files for %{name}
%description devel
devel files for %{name}.

%package pkg-config
Summary: pkg-config files for %{name}
Provides: pkg-config = 0.29.2
Provides: pkg-config%{?_isa} = 0.29.2
Provides: pkgconfig = 1:0.29.2
Provides: pkgconfig%{?_isa} = 1:0.29.2
Provides: pkgconfig(pkg-config) = %{version}
Requires: %{name}%{?_isa} = %{version}-%{release}
%description pkg-config
pkg-config files for %{name}.

%package m4
Summary: m4 files for %{name}
Requires: %{name}%{?_isa} = %{version}-%{release}
%description m4
m4 files for %{name}.

%prep
%setup -q -n pkgconf-3.0.7

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-pkg-config-dir=/usr/lib64/pkgconfig:/usr/share/pkgconfig
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
ln -s pkgconf %{buildroot}/usr/bin/pkg-config
ln -s pkgconf %{buildroot}/usr/bin/x86_64-redhat-linux-gnu-pkg-config
ln -s pkgconf.1 %{buildroot}/usr/share/man/man1/pkg-config.1
%check
make %{?_smp_mflags} check

%post -n libpkgconf -p /sbin/ldconfig
%postun -n libpkgconf -p /sbin/ldconfig

%files
%license COPYING
%doc README.md AUTHORS CONTRIBUTING.md COPYING DCO
%{_bindir}/pkgconf
%{_bindir}/bomtool
%{_bindir}/spdxtool
%{_bindir}/pccritic
%{_mandir}/man1/pkgconf.1*
%{_mandir}/man1/bomtool.1*
%{_mandir}/man1/spdxtool.1*
%{_mandir}/man1/pccritic.1*
%{_mandir}/man5/*

%files -n libpkgconf
%license COPYING
%{_libdir}/libpkgconf.so.*

%files devel
%{_includedir}/pkgconf/
%{_libdir}/libpkgconf.so
%{_libdir}/pkgconfig/libpkgconf.pc

%files pkg-config
%{_bindir}/pkg-config
%{_bindir}/x86_64-redhat-linux-gnu-pkg-config
%{_mandir}/man1/pkg-config.1*

%files m4
%{_datadir}/aclocal/pkg.m4
%{_mandir}/man7/pkg.m4.7*
