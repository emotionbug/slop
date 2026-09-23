%global prefix /opt/linux-oss/openssl-4.0.2
Name:           linuxoss-openssl4
Version:        4.0.2
Release:        1.linuxoss%{?dist}
Summary:        OpenSSL 4 for API migration and reverse-dependency rebuild tests
License:        Apache-2.0
URL:            https://www.openssl-library.org/
Vendor:         Linux OSS local build
Source0:        openssl-4.0.2.tar.gz
BuildRequires:  gcc, make, perl, perl-Text-Template, perl-Test-Simple

%description
Private OpenSSL 4 build used to port and test reverse dependencies.
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
* Wed Sep 23 2026 Linux OSS local build - 4.0.2-1.linuxoss
- Build latest stable API for staged integration tests.
