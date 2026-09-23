Name: cpio
Version: 2.15
Release: 2.linuxoss%{?dist}
Summary: GNU cpio, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/cpio/
Source0: cpio-2.15.tar.gz
Patch0: cpio-CVE-2026-66484.patch
Patch1: cpio-CVE-2026-66485.patch
Patch2: cpio-CVE-2026-66486.patch
BuildRequires: gcc, make
Vendor: Linux OSS local build
%description
GNU cpio with the upstream test suite. Unreleased upstream security fixes
require separate review; changing the release number is not remediation proof.
%prep
%setup -q
patch --fuzz=0 -p1 < %{PATCH0}
patch --fuzz=0 -p1 < %{PATCH1}
# Ubuntu's patch includes one context line from its unrelated device-link
# fix. Restore that context to the original GNU release; keep every security
# change unchanged and still require a zero-fuzz application.
python3.11 - %{PATCH2} > quote-release-context.patch <<'PY'
import pathlib,sys
patch=pathlib.Path(sys.argv[1]).read_text()
before='              else if ((archive_format == arf_ustar) && (file_hdr.c_nlink > 1))'
assert patch.count(before)==1
print(patch.replace(before,' \t      else if (archive_format == arf_ustar)'),end='')
PY
patch --fuzz=0 -p1 < quote-release-context.patch
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
%{_bindir}/cpio
%{_mandir}/man1/cpio.1*
%{_infodir}/cpio.info*
%{_datadir}/locale/*/LC_MESSAGES/cpio.mo
