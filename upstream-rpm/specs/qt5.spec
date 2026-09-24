%global debug_package %{nil}
Name: qt5-srpm-macros
Version: 5.15.18
Release: 1.linuxoss%{?dist}
Summary: Fedora Qt5 source packaging macro, without Qt runtime libraries
License: GPL-3.0-only
URL: https://src.fedoraproject.org/rpms/qt5
Source0: macros.qt5-srpm
BuildArch: noarch
Vendor: Linux OSS local build
%description
Commit-pinned Fedora macro data. Contains no Qt runtime library and does not
assert remediation of CVEs in the Qt runtime.
%prep
%build
%install
install -D -m0644 %{SOURCE0} %{buildroot}/usr/lib/rpm/macros.d/macros.qt5-srpm
%check
rpm --macros %{SOURCE0} --eval '%%qt5_qtwebengine_arches' > evaluated.txt
test -s evaluated.txt
%files
/usr/lib/rpm/macros.d/macros.qt5-srpm
