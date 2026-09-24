BuildRequires: linuxoss-openssl35 >= 3.5.8, glib2-devel >= 2.58
%global prefix /opt/linux-oss/subscription-manager-1.30.16
%global __provides_exclude_from ^/opt/linux-oss/subscription-manager-1\.30\.16/.*$
%global __brp_mangle_shebangs %{nil}
Name: linuxoss-subscription-manager-evaluation
Version: 1.30.16
Release: 1.linuxoss%{?dist}
Summary: Private RHSM client compilation evaluation for Python 3.11
License: GPL-2.0-only
URL: https://github.com/candlepin/subscription-manager
Source0: subscription-manager-1.30.16.tar.gz
BuildRequires: gcc, make, glib2-devel, openssl-devel, python3.11-devel, python3.11-setuptools, gettext
Requires: python3.11
Requires: linuxoss-openssl35 >= 3.5.8
%global __requires_exclude ^lib(crypto|ssl)\.so\.3
Vendor: Linux OSS local build
%description
Compilation evaluation in a private prefix. Does not register the machine or
enable subscriptions. DNF plugin, D-Bus, service and account integration have
not been validated and this is not an EL8 subscription-manager replacement.
%prep
%setup -q -n subscription-manager-subscription-manager-1.30.16-1
%build
export CFLAGS='-O2 -g -I/opt/linux-oss/openssl-3.5.8/include'
export LDFLAGS='-Wl,--build-id -L/opt/linux-oss/openssl-3.5.8/lib64 -Wl,-rpath,/opt/linux-oss/openssl-3.5.8/lib64'
make -j2 PYTHON=/usr/bin/python3.11 PREFIX=%{prefix} VERSION=1.30.16-1
%install
/usr/bin/python3.11 setup.py install --skip-build --root=%{buildroot} --prefix=%{prefix} --pkg-version=1.30.16-1
mkdir -p %{buildroot}%{prefix}/sbin
install -m0755 bin/rhsmcertd %{buildroot}%{prefix}/sbin/
%check
/usr/bin/python3.11 -m compileall -q build
# Loader dependency check only; credentials and registration are never exercised.
find build -name '*.so' -exec ldd {} \; > loader-check.txt
if grep -q 'not found' loader-check.txt; then cat loader-check.txt; exit 1; fi
%files
%license LICENSE
%{prefix}/
