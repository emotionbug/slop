Name: device-mapper-persistent-data
Version: 1.3.4
Release: 1.linuxoss%{?dist}
Summary: device-mapper-persistent-data upstream EL8 evaluation build
License: GPLv3
URL: https://github.com/jthornber/thin-provisioning-tools
Source1: thin-provisioning-tools-1.3.4-vendor.tar.xz
Source0: thin-provisioning-tools-1.3.4.tar.gz
BuildRequires: rust, cargo, gcc, make, device-mapper-devel, systemd-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%global debug_package %{nil}
%prep
%setup -q -n thin-provisioning-tools-1.3.4
tar -xJf %{SOURCE1}
%build
export CARGO_HOME="$PWD/.cargo-home"
export RUSTFLAGS='-C debuginfo=1 -C link-arg=-Wl,-z,relro,-z,now'
cargo build --release --locked --offline -j 2 --bin pdata_tools
%install
make DESTDIR=%{buildroot} PREFIX=/usr STRIP=true install
%check
# Pure library algorithms; block-device and root integration require a VM.
cargo test --release --locked --offline -j 2 --lib
target/release/pdata_tools thin_metadata_size --version
%files
%license COPYING
/usr/sbin/*
/usr/share/man/man8/*
