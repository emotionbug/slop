%global debug_package %{nil}
Name: python3-dataclasses
Version: 0.8
Release: 2.linuxoss%{?dist}
Summary: Official dataclasses backport for the EL8 Python 3.6 runtime
License: Apache-2.0
URL: https://pypi.org/project/dataclasses/
Source0: dataclasses-0.8.tar.gz
Patch0: dataclasses-bpo-36470.patch
BuildArch: noarch
BuildRequires: python3-devel, python3-setuptools
Requires: python(abi) = 3.6
Vendor: Linux OSS local build
%description
Upstream backport used by current firewalld on the EL8 Python 3.6 runtime.
%prep
%setup -q -n dataclasses-0.8
%patch0 -p1
%build
/usr/libexec/platform-python setup.py build
%install
/usr/libexec/platform-python setup.py install --skip-build --root=%{buildroot} --prefix=/usr
%check
PYTHONPATH="$PWD" /usr/libexec/platform-python -m unittest discover -s test
PYTHONPATH="$PWD" /usr/libexec/platform-python - <<'PY'
from dataclasses import dataclass, InitVar, replace
@dataclass
class Rule:
    value: int = 1
    text: InitVar[str] = None
assert replace(Rule(), value=2).value == 2
print('bpo-36470 default InitVar replacement regression passed')
PY
%files
%license LICENSE.txt
/usr/lib/python3.6/site-packages/*
