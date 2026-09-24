Name: sqlite
Version: 3.53.4
Release: 1.linuxoss%{?dist}
Summary: sqlite upstream EL8 evaluation build
License: Public Domain
URL: https://sqlite.org/
Source0: sqlite-autoconf-3530400.tar.gz
BuildRequires: gcc, make, readline-devel, zlib-devel, tcl-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package libs
Summary: libs files
%description libs
libs files.

%package devel
Summary: devel files
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n sqlite-autoconf-3530400

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2 -DSQLITE_ENABLE_COLUMN_METADATA -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_UNLOCK_NOTIFY'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --enable-threadsafe --enable-readline --enable-fts5 --soname=legacy
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
chmod 0755 %{buildroot}/usr/lib64/libsqlite3.so.*
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
./sqlite3 :memory: "CREATE VIRTUAL TABLE t USING fts5(x); INSERT INTO t VALUES ('hello'); SELECT * FROM t WHERE t MATCH 'hello';" | grep -qx hello
./sqlite3 :memory: 'PRAGMA integrity_check;' | grep -qx ok

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
/usr/bin/sqlite3
/usr/share/man/man1/sqlite3.1*
%files libs
/usr/lib64/libsqlite3.so.*
%files devel
/usr/include/sqlite3*.h
/usr/lib64/libsqlite3.so
/usr/lib64/pkgconfig/sqlite3.pc
