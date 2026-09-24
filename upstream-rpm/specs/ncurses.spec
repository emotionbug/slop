Name: ncurses
Version: 6.6
Release: 1.linuxoss%{?dist}
Summary: ncurses upstream EL8 evaluation build
License: MIT
URL: https://invisible-island.net/ncurses/
Source0: ncurses-6.6.tar.gz
BuildRequires: gcc, gcc-c++, make
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package base
Summary: base files
%description base
base files.

%package libs
Summary: libs files
Requires: %{name}-base = %{version}-%{release}
%description libs
libs files.

%package devel
Summary: devel files
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n ncurses-6.6
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

for variant in narrow wide; do
  mkdir build-$variant
  cd build-$variant
  wide=--disable-widec; test "$variant" != wide || wide=--enable-widec
  ../configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --with-shared --without-normal     --without-debug --with-termlib=tinfo --with-ticlib --enable-sp-funcs --with-abi-version=6 --with-versioned-syms --enable-pc-files     --with-pkg-config-libdir=/usr/lib64/pkgconfig --enable-overwrite $wide
  make %{?_smp_mflags}
  cd ..
done
%install
make -C build-narrow DESTDIR=%{buildroot} install
# Both variants use libtinfo.so.6. Force installation of the wide build last;
# otherwise make can keep the newer narrow destination from the previous step.
rm -f %{buildroot}/usr/lib64/libtinfo.so*
make -C build-wide DESTDIR=%{buildroot} install
rm -f %{buildroot}/usr/lib64/*.a
mkdir -p %{buildroot}/etc/terminfo
%check
LD_LIBRARY_PATH=build-wide/lib build-wide/progs/tic -V | grep '6.6'
LD_LIBRARY_PATH=build-wide/lib build-wide/progs/infocmp -A misc/terminfo.src xterm ||   LD_LIBRARY_PATH=build-wide/lib build-wide/progs/infocmp xterm

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license COPYING
/usr/bin/*
/usr/share/man/man1/*
%files base
%dir /etc/terminfo
/usr/share/terminfo/
/usr/lib/terminfo
/usr/share/tabset/
/usr/share/man/man5/*
/usr/share/man/man7/*
%files libs
/usr/lib64/*.so.*
%files devel
/usr/include/*
/usr/lib64/*.so
/usr/lib64/pkgconfig/*
/usr/share/man/man3/*
