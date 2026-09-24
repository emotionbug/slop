%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude (^lib(crypto|ssl)[.]so|^(librpm_sequoia[.]so[.]1)[(])
Name: linuxoss-rpm-sequoia
Version: 1.10.2
Release: 2.linuxoss%{?dist}
Summary: linuxoss-rpm-sequoia upstream EL8 evaluation build
License: LGPLv2+
URL: https://github.com/rpm-software-management/rpm-sequoia
Source1: rpm-sequoia-1.10.2-vendor.tar.xz
Source0: rpm-sequoia-1.10.2.tar.gz
BuildRequires: rust, cargo, clang-devel, linuxoss-openssl35
Requires: linuxoss-openssl35 >= 3.5.8
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%global __provides_exclude ^(librpm_sequoia[.]so|pkgconfig[(].*)
%global prefix /opt/linux-oss/rpm-sequoia-1.10.2
%prep
%setup -q -n rpm-sequoia-1.10.2
tar -xJf %{SOURCE1}
%build
export OPENSSL_DIR=/opt/linux-oss/openssl-3.5.8
export OPENSSL_LIB_DIR=$OPENSSL_DIR/lib64
export PREFIX=%{prefix} LIBDIR=%{prefix}/lib64
export CARGO_HOME="$PWD/.cargo-home"
export RUSTFLAGS='-C debuginfo=1 -C link-arg=-Wl,-z,relro,-z,now -C link-arg=-Wl,-rpath,/opt/linux-oss/openssl-3.5.8/lib64'
cargo build --release --locked --offline --no-default-features --features crypto-openssl -j2
%install
mkdir -p %{buildroot}%{prefix}/lib64/pkgconfig
cp -a target/release/librpm_sequoia.so* %{buildroot}%{prefix}/lib64/
cp target/release/rpm-sequoia.pc %{buildroot}%{prefix}/lib64/pkgconfig/
%check
export OPENSSL_DIR=/opt/linux-oss/openssl-3.5.8 OPENSSL_LIB_DIR=/opt/linux-oss/openssl-3.5.8/lib64
LD_LIBRARY_PATH=$OPENSSL_LIB_DIR cargo test --release --locked --offline --no-default-features --features crypto-openssl -j2
%files
%license LICENSE*
%{prefix}/
