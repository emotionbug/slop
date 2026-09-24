%global debug_package %{nil}
%global prefix /opt/linux-oss/pip-26.2.1
Name: linuxoss-pip26
Version: 26.2.1
Release: 1.linuxoss%{?dist}
Summary: Private pip for Python 3.11, separate from EL8 platform Python
License: MIT
URL: https://pip.pypa.io/
Source0: pip-26.2.1.tar.gz
Source1: flit_core-3.12.0.tar.gz
BuildRequires: python3.11-devel
Requires: python3.11
BuildArch: noarch
Vendor: Linux OSS local build
%description
Private pip for Python 3.11. Does not replace the platform-python or Python 3.6
pip packages used by EL8. Installation and system remediation are not implied.
%prep
%setup -q -n pip-26.2.1 -a 1
%build
PYTHONPATH="$PWD/flit_core-3.12.0" /usr/bin/python3.11 -m flit_core.wheel
%install
mkdir -p %{buildroot}%{prefix}/site-packages %{buildroot}%{prefix}/bin
/usr/bin/python3.11 -m zipfile -e dist/pip-26.2.1-py3-none-any.whl %{buildroot}%{prefix}/site-packages
cat > %{buildroot}%{prefix}/bin/pip26 <<'PY'
#!/usr/bin/python3.11
import sys
sys.path.insert(0, '/opt/linux-oss/pip-26.2.1/site-packages')
from pip._internal.cli.main import main
raise SystemExit(main())
PY
chmod 0755 %{buildroot}%{prefix}/bin/pip26
%check
PYTHONPATH=src /usr/bin/python3.11 -m pip --version
PYTHONPATH=src /usr/bin/python3.11 -m pip debug --verbose > pip-debug.txt
%files
%license LICENSE.txt AUTHORS.txt
%{prefix}/
