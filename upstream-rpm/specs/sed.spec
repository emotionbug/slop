Name: sed
Version: 4.10
Release: 2.linuxoss%{?dist}
Summary: GNU stream editor, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/sed/
Source0: sed-4.10.tar.xz
BuildRequires: gcc, make, libselinux-devel, libacl-devel
Vendor: Linux OSS local build
# EL8 /bin is a symlink to /usr/bin, but RPM file dependencies use exact paths.
Provides: /bin/sed
%description
GNU sed with the upstream regression suite and EL8 runtime validation.
%prep
%setup -q
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_infodir}/dir
%check
make %{?_smp_mflags} check
%files
%license COPYING
%doc NEWS README
%{_bindir}/sed
%{_mandir}/man1/sed.1*
%{_infodir}/sed.info*
%{_datadir}/locale/*/LC_MESSAGES/sed.mo
