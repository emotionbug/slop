Name: libssh
Version: 0.12.2
Release: 1.linuxoss%{?dist}
Summary: libssh upstream EL8 evaluation
License: LGPLv2+
URL: https://www.libssh.org/
Source0: libssh-0.12.2.tar.xz
BuildRequires: gcc, cmake, openssl-devel, zlib-devel, krb5-devel, libcmocka-devel
Vendor: Linux OSS local build
Requires: libssh-config = %{version}-%{release}

%description
Upstream source build. Target ABI and runtime qualification are separate.

%package config
Summary: System crypto policy and OpenSSH configuration includes for libssh
BuildArch: noarch
%description config
Preserves the Red Hat EL8 configuration paths and policy includes.
These configuration files contain no independently rebuilt security library.

%package devel
Summary: devel files from libssh
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files from libssh.

%prep
%setup -q -n libssh-0.12.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_SHARED_LIBS=ON -DUNIT_TESTING=ON -DWITH_GSSAPI=ON -DGLOBAL_CLIENT_CONFIG=/etc/libssh/libssh_client.config
cmake --build build --parallel %{?_smp_build_ncpus}


%install
DESTDIR=%{buildroot} cmake --install build
find %{buildroot} -name "*.la" -delete
rm -f %{buildroot}%{_libdir}/*.a
install -d %{buildroot}%{_sysconfdir}/libssh
cat > %{buildroot}%{_sysconfdir}/libssh/libssh_client.config <<'EOF'
# Parse system-wide crypto configuration file
Include /etc/crypto-policies/back-ends/libssh.config
# Parse OpenSSH configuration file for consistency
Include /etc/ssh/ssh_config
EOF
cat > %{buildroot}%{_sysconfdir}/libssh/libssh_server.config <<'EOF'
# Parse system-wide crypto configuration file
Include /etc/crypto-policies/back-ends/libssh.config
EOF

%check
ctest --test-dir build --output-on-failure --parallel 2

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license COPYING
%{_libdir}/libssh.so.*

%files config
%dir %{_sysconfdir}/libssh
%config(noreplace) %{_sysconfdir}/libssh/libssh_client.config
%config(noreplace) %{_sysconfdir}/libssh/libssh_server.config

%files devel
%{_includedir}/libssh/
%{_libdir}/libssh.so
%{_libdir}/pkgconfig/libssh.pc
%{_libdir}/cmake/libssh/
