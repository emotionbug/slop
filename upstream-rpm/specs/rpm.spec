BuildRequires: linuxoss-bootstrap-gcc >= 16.2.0, binutils >= 2.35, audit-libs-devel, dbus-devel, elfutils-devel, elfutils-libelf-devel
Name: linuxoss-rpm6-evaluation
Version: 6.1.0
Release: 1.linuxoss%{?dist}
Summary: linuxoss-rpm6-evaluation upstream EL8 evaluation build
License: GPLv2+ and LGPLv2+
URL: https://rpm.org/
Source0: rpm-6.1.0.tar.gz
BuildRequires: gcc-c++, cmake, make, lua-devel, libarchive-devel, file-devel, popt-devel, sqlite-devel, linuxoss-rpm-sequoia, libgcrypt-devel, scdoc
Requires: linuxoss-rpm-sequoia >= 1.10.2, linuxoss-bootstrap-gcc >= 16.2.0
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%global prefix /opt/linux-oss/rpm-6.1.0
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude ^(librpm.*[.]so|libstdc[+][+][.]so)
%prep
%setup -q -n rpm-rpm-6.1.0-release
%build
export CC=gcc CXX=g++
export CFLAGS="-O2 -g -gdwarf-4 -fstack-protector-strong"
export CXXFLAGS="$CFLAGS"
export LDFLAGS="-Wl,--build-id -Wl,-z,relro,-z,now"
export PKG_CONFIG_PATH=/opt/linux-oss/rpm-sequoia-1.10.2/lib64/pkgconfig:/opt/linux-oss/openssl-3.5.8/lib64/pkgconfig
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=%{prefix} -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_PYTHON=OFF -DENABLE_OPENMP=OFF -DENABLE_BDB_RO=ON -DENABLE_TESTSUITE=OFF -DCMAKE_INSTALL_RPATH='%{prefix}/lib64;/opt/linux-oss/rpm-sequoia-1.10.2/lib64;/opt/linux-oss/bootstrap/gcc-16.2.0/lib64' -DWITH_READLINE=OFF -DWITH_DBUS=OFF
cmake --build build -j2
%install
DESTDIR=%{buildroot} cmake --install build
%check
export RPM_CONFIGDIR=%{buildroot}%{prefix}/lib/rpm
# Query/transaction smoke uses an empty private database, never the builder host database.
build/tools/rpm --version
mkdir -p "$PWD/test-rpmdb"
build/tools/rpmdb --dbpath "$PWD/test-rpmdb" --initdb
test -z "$(build/tools/rpmquery --dbpath "$PWD/test-rpmdb" -a)"
%files
%license COPYING*
%{prefix}/
