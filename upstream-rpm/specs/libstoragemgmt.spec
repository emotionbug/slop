BuildRequires: procps-ng
BuildRequires: chrpath, valgrind, python3-pytest
Name: libstoragemgmt
Version: 1.11.0
Release: 1.linuxoss%{?dist}
Summary: libstoragemgmt upstream EL8 evaluation build
License: LGPLv2+
URL: https://github.com/libstorage/libstoragemgmt
Source0: libstoragemgmt-1.11.0.tar.gz
BuildRequires: gcc, gcc-c++, make, glib2-devel, libudev-devel, libconfig-devel, libxml2-devel, json-c-devel, python3-devel, libtirpc-devel, check-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package devel
Summary: devel files
%description devel
devel files.

%package -n python3-libstoragemgmt
Summary: Storage management Python API
%description -n python3-libstoragemgmt
Storage management Python API and plugins.

%prep
%setup -q -n libstoragemgmt-1.11.0

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static PYTHON=/usr/libexec/platform-python --without-smispy --without-ledmon --with-test
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
# Bounded upstream IPC and Python tests; daemon/storage-device suite is not run.
test/test_ipc
PYTHONPATH="%{buildroot}/usr/lib/python3.6/site-packages:%{buildroot}/usr/lib64/python3.6/site-packages:$PWD/plugin/megaraid_plugin" LD_LIBRARY_PATH="%{buildroot}/usr/lib64" /usr/libexec/platform-python -m pytest -q test/test_megaraid.py test/test_transport.py

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING.LIB
/usr/bin/*
/usr/lib64/libstoragemgmt.so.*
/usr/libexec/*
/usr/lib/systemd/*
/usr/lib/sysusers.d/*
/usr/lib/tmpfiles.d/*
/usr/share/man/*/*
%config(noreplace) /etc/*
%files devel
/usr/include/libstoragemgmt/
/usr/lib64/libstoragemgmt.so
/usr/lib64/pkgconfig/*
%files -n python3-libstoragemgmt
/usr/lib/python3.6/site-packages/*
/usr/lib64/python3.6/site-packages/*
