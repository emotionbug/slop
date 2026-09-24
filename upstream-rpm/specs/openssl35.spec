%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude (^lib(crypto|ssl)[.]so|^(libcrypto[.]so[.]3|libssl[.]so[.]3)[(])
%global __provides_exclude ^(lib(crypto|ssl)[.]so|pkgconfig[(].*)
%global prefix /opt/linux-oss/openssl-3.5.8
Name:           linuxoss-openssl35
Version:        3.5.8
Release: 2.linuxoss%{?dist}
Summary:        OpenSSL 3.5 LTS for API migration and reverse-dependency rebuild tests
License:        Apache-2.0
URL:            https://www.openssl-library.org/
Vendor:         Linux OSS local build
Source0:        openssl-3.5.8.tar.gz
BuildRequires:  gcc, make, perl, perl-Text-Template, perl-Test-Simple

%description
Private OpenSSL 3.5 LTS build used to port and test reverse dependencies.
It does not replace libcrypto.so.1.1, libssl.so.1.1 or the system crypto policy.
Installing it alone does not remediate the original OpenSSL packages.

%prep
%setup -q -n openssl-%{version}

%build
./Configure linux-x86_64 shared --prefix=%{prefix} --libdir=lib64 \
  --openssldir=%{prefix}/ssl -Wl,-rpath,%{prefix}/lib64 \
  -O2 -g -fstack-protector-strong -D_FORTIFY_SOURCE=2
make %{?_smp_mflags}

%check
make %{?_smp_mflags} test

%install
make DESTDIR=%{buildroot} install_sw install_ssldirs

%files
%license LICENSE.txt
%doc README.md CHANGES.md
%{prefix}/

%changelog
* Wed Sep 23 2026 Linux OSS local build - 3.5.8-1.linuxoss
- Build latest stable API for staged integration tests.
