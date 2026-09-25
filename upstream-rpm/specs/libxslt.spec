Name: libxslt
Version: 1.1.32
Release: 7.linuxoss%{?dist}
Summary: libxslt upstream EL8 evaluation build
License: MIT
URL: https://gitlab.gnome.org/GNOME/libxslt
Source0: libxslt-1.1.32.tar.gz
Patch100: multilib.patch
Patch101: libxslt-1.1.26-utf8-docs.patch
Patch102: multilib2.patch
Patch103: libxslt-1.1.32-CVE-2019-18197.patch
Patch104: libxslt-1.1.32-CVE-2019-11068.patch
Patch105: libxslt-1.1.32-unexpected-rvt-flag.patch
Patch106: libxslt-1.1.32-CVE-2024-55549.patch
Patch107: libxslt-1.1.32-CVE-2025-24855.patch
Patch108: libxslt-1.1.32-CVE-2023-40403.patch
Patch109: libxslt-1.1.32-CVE-2025-10911.patch
Patch110: libxslt-CVE-2019-13117.patch
Patch111: libxslt-CVE-2019-13118.patch
Patch112: libxslt-CVE-2025-11731.patch
BuildRequires: gcc, make, libxml2-devel, libgcrypt-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files.

%prep
%setup -q -n libxslt-1.1.32
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
%patch110 -p1
%patch111 -p1
%patch112 -p1
autoreconf -vfi

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
export PKG_CONFIG_PATH=
export LD_LIBRARY_PATH=

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --without-python
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
export LD_LIBRARY_PATH=
make %{?_smp_mflags} tests

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license Copyright
/usr/lib64/libxslt.so.*
/usr/lib64/libexslt.so.*
/usr/lib64/libxslt-plugins/
/usr/bin/*
/usr/share/man/man1/*

%files devel
/usr/include/*
/usr/lib64/pkgconfig/*
/usr/lib64/xsltConf.sh
/usr/lib64/libxslt.so
/usr/lib64/libexslt.so
/usr/share/doc/*
/usr/share/man/man3/*
/usr/share/aclocal/libxslt.m4
