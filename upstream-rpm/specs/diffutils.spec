Name: diffutils
Version: 3.12
Release: 2.linuxoss%{?dist}
Summary: GNU file comparison utilities, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/diffutils/
Source0: diffutils-3.12.tar.xz
Patch0: diffutils-CVE-2026-53910-1.patch
Patch1: diffutils-CVE-2026-53910-2.patch
BuildRequires: gcc, make
Vendor: Linux OSS local build
%description
GNU diff, diff3, cmp and sdiff with their upstream regression tests.
%prep
%setup -q
patch --fuzz=0 -p1 < %{PATCH0}
patch --fuzz=0 -p1 < %{PATCH1}
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
%{_bindir}/cmp
%{_bindir}/diff
%{_bindir}/diff3
%{_bindir}/sdiff
%{_mandir}/man1/*
%{_infodir}/diffutils.info*
%{_datadir}/locale/*/LC_MESSAGES/diffutils.mo
