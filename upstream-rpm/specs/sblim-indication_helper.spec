Name: sblim-indication_helper
Version: 0.5.0
Release: 1.linuxoss%{?dist}
Summary: CMPI indication helper for isolated SBLIM evaluation
License: EPL-1.0
URL: https://sourceforge.net/projects/sblim/
Source0: sblim-indication_helper-0.5.0.tar.bz2
BuildRequires: gcc, gcc-c++, make, sblim-cmpi-devel
Vendor: Linux OSS local build
%description
Upstream helper, used for SBLIM provider build and load validation.
%package devel
Summary: CMPI indication helper development files
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
Headers and linker symlink.
%prep
%setup -q
%build
CC=/usr/bin/gcc CXX=/usr/bin/g++ ./configure --prefix=/usr --libdir=/usr/lib64 --disable-static --with-pic
make -j2
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
%check
LD_LIBRARY_PATH="$PWD/.libs" /usr/bin/python3.11 - <<'PY'
import ctypes,glob
paths=glob.glob('.libs/libind_helper.so')
assert paths
ctypes.CDLL(paths[0])
PY
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license COPYING
/usr/lib64/libind_helper.so.*
%files devel
/usr/include/sblim/
/usr/lib64/libind_helper.so
