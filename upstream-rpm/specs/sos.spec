%global debug_package %{nil}
%global __python3 /usr/bin/python3.11
Name: sos
Version: 4.12.0
Release: 1.linuxoss%{?dist}
Summary: sos upstream EL8 evaluation build
License: GPLv2+
URL: https://github.com/sosreport/sos
Source0: sos-4.12.0.tar.gz
BuildRequires: make, python3.11-devel, python3.11-setuptools, python3-pexpect, python3-pyyaml
BuildArch: noarch
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n sos-4.12.0
%build
/usr/bin/python3.11 setup.py build
%install
/usr/bin/python3.11 setup.py install --skip-build --root=%{buildroot} --prefix=/usr
mkdir -p %{buildroot}/etc %{buildroot}/usr/lib/tmpfiles.d
mv %{buildroot}/usr/config/sos.conf %{buildroot}/etc/sos.conf
mv %{buildroot}/usr/config/tmpfilesd-sos-rh.conf %{buildroot}/usr/lib/tmpfiles.d/sos.conf
rmdir %{buildroot}/usr/config
%check
/usr/bin/python3.11 -m compileall -q sos
PYTHONPATH="$PWD" /usr/bin/python3.11 bin/sos --version
%files
%license LICENSE
/usr/bin/*
%config(noreplace) /etc/sos.conf
/usr/lib/tmpfiles.d/sos.conf
/usr/lib/python3.11/site-packages/*
/usr/share/*
