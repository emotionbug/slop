Name: ghostscript
Version: 10.08.0
Release: 1.linuxoss%{?dist}
Summary: ghostscript upstream EL8 evaluation build
License: AGPLv3+
URL: https://ghostscript.com/
Source0: ghostscript-10.08.0.tar.gz
BuildRequires: gcc, gcc-c++, make, fontconfig-devel, freetype-devel, libpng-devel, libjpeg-turbo-devel, zlib-devel, libtiff-devel, lcms2-devel, cups-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package -n libgs
Summary: Ghostscript shared API library
%description -n libgs
Upstream Ghostscript shared library; major SONAME migration requires consumer rebuilding.
%package devel
Summary: Ghostscript API headers
%description devel
Ghostscript development files.

%prep
%if 0%{?reuse_prepared}
%setup -q -D -T -n ghostscript-10.08.0
%else
%setup -q -n ghostscript-10.08.0
%endif
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --without-x --disable-gtk --with-drivers=ALL
make %{?_smp_mflags} so
%install
make DESTDIR=%{buildroot} soinstall
%check
export LD_LIBRARY_PATH="$PWD/sobin"
sobin/gsc -dSAFER -dBATCH -dNOPAUSE -sDEVICE=nullpage -c '20 22 add 42 ne { /bad cvx exec } if'
sobin/gsc -dSAFER -dBATCH -dNOPAUSE -sDEVICE=png16m -r72 -g64x64 -sOutputFile=sample.png -c '0.5 setgray 0 0 64 64 rectfill showpage'
test -s sample.png

%post -n libgs -p /sbin/ldconfig
%postun -n libgs -p /sbin/ldconfig

%files
/usr/share/doc/ghostscript/
%license LICENSE
/usr/bin/*
/usr/share/ghostscript/
/usr/share/man/*/*
%files -n libgs
/usr/lib64/libgs.so.*
%files devel
/usr/include/ghostscript/
/usr/lib64/libgs.so
