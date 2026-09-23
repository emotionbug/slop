Name: tar
Epoch: 2
Version: 1.35
Release: 1.linuxoss%{?dist}
Summary: GNU tar, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/tar/
Source0: tar-1.35.tar.xz
Patch0: tar-acl-prefix.patch
BuildRequires: gcc, make, libselinux-devel, libacl-devel, libattr-devel
Vendor: Linux OSS local build
%description
GNU tar with ACL, SELinux and extended attribute support. This latest release
alone is not an assertion that every currently reported tar CVE is fixed.
%prep
%setup -q
patch --fuzz=0 -p1 < %{PATCH0}
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --with-rmt=/usr/sbin/rmt
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_infodir}/dir
%check
make %{?_smp_mflags} check
%files
%license COPYING
%doc NEWS README
%{_bindir}/tar
%{_infodir}/tar.info*
%{_datadir}/locale/*/LC_MESSAGES/tar.mo
%{_libexecdir}/tar/
