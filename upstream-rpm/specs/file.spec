Name: file
Version: 5.48
Release: 1.linuxoss%{?dist}
Summary: file upstream EL8 evaluation
License: BSD
URL: https://www.darwinsys.com/file/
Source0: file-5.48.tar.gz
BuildRequires: gcc, make, zlib-devel, bzip2-devel, xz-devel, libzstd-devel, python3-devel, python3-setuptools
Vendor: Linux OSS local build
Requires: file-libs%{?_isa} = %{version}-%{release}

%description
Upstream source build. Target ABI and runtime qualification are separate.

%package libs
Summary: libs files from file
%description libs
libs files from file.

%package devel
Summary: devel files from file
Requires: file-libs%{?_isa} = %{version}-%{release}
%description devel
devel files from file.

%package -n python3-magic
BuildArch: noarch
Summary: python3-magic files from file
Requires: file-libs%{?_isa} = %{version}-%{release}
%description -n python3-magic
python3-magic files from file.

%prep
%setup -q -n file-5.48

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --enable-zlib --enable-bzlib --enable-xzlib --enable-zstdlib
make %{?_smp_mflags}
(cd python && python3 setup.py build)

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name "*.la" -delete
(cd python && python3 setup.py install --root=%{buildroot} --prefix=/usr)

%check
make %{?_smp_mflags} check

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files
%license COPYING
%{_bindir}/file
%{_mandir}/man1/file.1*

%files libs
%{_libdir}/libmagic.so.*
%{_datadir}/misc/magic*
%{_mandir}/man4/magic.4*

%files devel
%{_includedir}/magic.h
%{_libdir}/libmagic.so
%{_libdir}/pkgconfig/libmagic.pc
%{_mandir}/man3/*

%files -n python3-magic
%{python3_sitelib}/magic*
%{python3_sitelib}/__pycache__/magic.*.pyc
%{python3_sitelib}/file_magic-*.egg-info/
