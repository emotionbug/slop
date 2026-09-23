Name: patch
Version: 2.8
Release: 1.linuxoss%{?dist}
Summary: GNU patch, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/patch/
Source0: patch-2.8.tar.xz
BuildRequires: gcc, make, libattr-devel, libacl-devel
Vendor: Linux OSS local build
%description
Apply textual changes with GNU patch and its upstream regression tests.
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
%check
make %{?_smp_mflags} check
%files
%license COPYING
%doc NEWS README
%{_bindir}/patch
%{_mandir}/man1/patch.1*
