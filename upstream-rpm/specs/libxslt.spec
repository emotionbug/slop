Name: libxslt
Version: 1.1.45
Release: 1.linuxoss%{?dist}
Summary: libxslt upstream EL8 evaluation build
License: MIT
URL: https://gitlab.gnome.org/GNOME/libxslt
Source0: libxslt-1.1.45.tar.xz
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
%setup -q -n libxslt-1.1.45

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-L/opt/linux-oss/build-xml/usr/lib64 -Wl,--build-id -Wl,-z,relro,-z,now'
export PKG_CONFIG_PATH=/opt/linux-oss/build-xml/usr/lib64/pkgconfig
export LD_LIBRARY_PATH=/opt/linux-oss/build-xml/usr/lib64

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --without-python
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
export LD_LIBRARY_PATH=/opt/linux-oss/build-xml/usr/lib64
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license Copyright
/usr/lib64/libxslt.so.*
/usr/lib64/libexslt.so.*
/usr/bin/*
/usr/share/man/man1/*

%files devel
/usr/include/*
/usr/lib64/pkgconfig/*
/usr/lib64/xsltConf.sh
/usr/lib64/libxslt.so
/usr/lib64/libexslt.so
/usr/lib64/cmake/*
/usr/share/doc/*
/usr/share/gtk-doc/html/*
/usr/share/man/man3/*
