%global debug_package %{nil}
Name: xdg-utils
Version: 1.2.1
Release: 1.linuxoss%{?dist}
Summary: xdg-utils upstream EL8 evaluation build
License: MIT
URL: https://www.freedesktop.org/wiki/Software/xdg-utils/
Source0: xdg-utils-1.2.1.tar.gz
BuildRequires: make, autoconf, automake, xmlto, docbook-style-xsl
BuildArch: noarch
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n xdg-utils-v1.2.1
%build
./configure --prefix=/usr
make
%install
make DESTDIR=%{buildroot} install
%check
for script in %{buildroot}/usr/bin/*; do sh -n "$script"; "$script" --version; done
%files
%license LICENSE
/usr/bin/*
/usr/share/man/*/*
