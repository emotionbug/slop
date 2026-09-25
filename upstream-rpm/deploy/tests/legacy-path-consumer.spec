Name: linuxoss-test-legacy-consumer
Version: 1
Release: 1%{?dist}
Summary: Test fixture for existing EL8 legacy executable-path dependencies
License: MIT
BuildArch: noarch
# os-prober requires /bin/sed; sudo and selinux-policy also use legacy paths.
Requires: /bin/sed /bin/chmod /bin/awk /bin/gawk /bin/cpio /bin/tar /bin/gtar
%description
Disposable-container test fixture. Never deploy this RPM to the target server.
%install
mkdir -p %{buildroot}%{_datadir}/linuxoss-test-legacy-consumer
echo fixture > %{buildroot}%{_datadir}/linuxoss-test-legacy-consumer/fixture
%files
%{_datadir}/linuxoss-test-legacy-consumer
