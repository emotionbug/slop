%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude (^lib(crypto|ssl)[.]so|^(libpython3[.]14[.]so[.]1[.]0|libpython3[.]so)[(])
%global __brp_mangle_shebangs %{nil}
Name: linuxoss-python314
Version: 3.14.7
Release: 2.linuxoss%{?dist}
Summary: linuxoss-python314 upstream EL8 evaluation build
License: Python-2.0
URL: https://www.python.org/
Source0: Python-3.14.7.tar.xz
BuildRequires: gcc, make, linuxoss-openssl35, zlib-devel, bzip2-devel, xz-devel, libffi-devel, sqlite-devel, readline-devel, gdbm-devel
Requires: linuxoss-openssl35 >= 3.5.8
Vendor: Linux OSS local build

%description
Parallel runtime under /opt. It does not replace platform-python or remediate that installed EL8 package.
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%global prefix /opt/linux-oss/python-3.14.7
%prep
%setup -q -n Python-3.14.7
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
# Keep Python's legacy SSL API with the supported OpenSSL 3.5 LTS line.
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

export LDFLAGS="-L/opt/linux-oss/openssl-3.5.8/lib64 $LDFLAGS -Wl,-rpath,%{prefix}/lib -Wl,-rpath,/opt/linux-oss/openssl-3.5.8/lib64"
export PKG_CONFIG_PATH=/opt/linux-oss/openssl-3.5.8/lib64/pkgconfig
./configure --prefix=%{prefix} --enable-shared --with-openssl=/opt/linux-oss/openssl-3.5.8 --with-openssl-rpath=auto --with-ensurepip=no
make %{?_smp_mflags}
LD_LIBRARY_PATH="$PWD:/opt/linux-oss/openssl-3.5.8/lib64" ./python -c "import ssl,hashlib; assert ssl.OPENSSL_VERSION.startswith('OpenSSL 3.5.')"
%install
make DESTDIR=%{buildroot} altinstall
%check
LD_LIBRARY_PATH="$PWD:/opt/linux-oss/openssl-3.5.8/lib64" ./python -m test -j 2 test_json test_ssl test_hashlib test_sqlite3 test_zlib test_bz2 test_lzma
%files
%license LICENSE
%{prefix}/
