Name: gdb
Version: 17.2
Release: 1.linuxoss%{?dist}
Summary: gdb upstream EL8 evaluation build
License: GPLv3+
URL: https://www.gnu.org/software/gdb/
Source0: gdb-17.2.tar.xz
BuildRequires: gcc, gcc-c++, make, gmp-devel, mpfr-devel, ncurses-devel, readline-devel, expat-devel, python3-devel, texinfo, source-highlight-devel
Vendor: Linux OSS local build
Requires: gdb-headless%{?_isa} = %{version}-%{release}

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package headless
Summary: headless files
%description headless
headless files.

%prep
%setup -q -n gdb-17.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
# Old libiberty preprocessor probes treat fortify's no-optimization warning as a missing header.
export CPPFLAGS=''
export CFLAGS="$CFLAGS -D_FORTIFY_SOURCE=2"
export CXXFLAGS="$CXXFLAGS -D_FORTIFY_SOURCE=2"
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --with-python=/usr/bin/python3 --with-system-readline --with-expat --without-guile --disable-werror
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install-gdb install-gdbserver
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
rm -f %{buildroot}/usr/lib64/*.a
%check
./gdb/gdb --batch -nx -ex 'python print(6 * 7)' | grep -qx 42
./gdb/gdb --batch -nx -ex 'show version' | grep '17.2'

%files
%license COPYING3
/usr/bin/gdb-add-index
/usr/bin/gcore
/usr/bin/gdbserver
/usr/bin/gstack
/usr/share/man/man1/*
%files headless
/usr/bin/gdb
/usr/include/gdb/
/usr/share/gdb/
/usr/share/info/*
/usr/lib64/libinproctrace.so
/usr/share/man/man5/*
