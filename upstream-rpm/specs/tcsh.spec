Name: tcsh
Version: 6.24.16
Release: 1.linuxoss%{?dist}
Summary: C shell required by the optional Vim vim132 tool
License: BSD
URL: https://www.tcsh.org/
Source0: tcsh-6.24.16.tar.gz
Vendor: Linux OSS local build
BuildRequires: gcc, make, ncurses-devel
Provides: /bin/csh /bin/tcsh
%description
Upstream tcsh built on EL8. No default shell or /etc/shells changes are made.
%prep
%setup -q
%build
%configure --disable-rpath
make %{?_smp_mflags}
%check
make check
./tcsh -f -c 'echo 42' | grep -qx 42
%install
install -D -m0755 tcsh %{buildroot}%{_bindir}/tcsh
ln -s tcsh %{buildroot}%{_bindir}/csh
install -D -m0644 tcsh.man %{buildroot}%{_mandir}/man1/tcsh.1
ln -s tcsh.1 %{buildroot}%{_mandir}/man1/csh.1
%files
%license Copyright
%doc README.md
%{_bindir}/tcsh
%{_bindir}/csh
%{_mandir}/man1/tcsh.1*
%{_mandir}/man1/csh.1*
