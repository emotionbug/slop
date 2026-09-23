Name: tar
Epoch: 2
Version: 1.35
Release: 2.linuxoss%{?dist}
Summary: GNU tar, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/tar/
Source0: tar-1.35.tar.xz
Patch0: tar-security-tar-1.35-revert-fix-savannah-bug-633567.patch
Patch1: tar-security-CVE-2026-5704.patch
Patch2: tar-security-CVE-2025-45582-1.patch
Patch3: tar-security-CVE-2025-45582-2.patch
Patch4: tar-security-CVE-2025-45582-3.patch
Patch5: tar-security-CVE-2025-45582-4.patch
Patch6: tar-security-CVE-2025-45582-5.patch
Patch7: tar-security-CVE-2025-45582-6.patch
Patch8: tar-security-CVE-2025-45582-7.patch
Patch9: tar-security-CVE-2025-45582-8.patch
Patch10: tar-security-CVE-2025-45582-9.patch
Patch11: tar-security-CVE-2025-45582-10.patch
Patch12: tar-security-CVE-2025-45582-gnulib-1.patch
Patch13: tar-security-CVE-2025-45582-gnulib-2.patch
Patch14: tar-security-CVE-2025-45582-gnulib-3.patch
Patch15: tar-security-CVE-2025-45582-gnulib-4.patch
Patch16: tar-security-CVE-2025-45582-gnulib-5.patch
Patch17: tar-security-CVE-2025-45582-gnulib-6.patch
Patch18: tar-security-CVE-2026-5704-2.patch
Patch19: tar-security-CVE-2026-5704-3.patch
Patch20: tar-security-CVE-2026-5704-4.patch
Patch21: tar-security-CVE-2026-5704-5.patch
Patch22: tar-acl-prefix.patch
Patch23: tar-exclude17.patch
Patch24: tar-exclude18.patch
BuildRequires: gcc, make, libselinux-devel, libacl-devel, libattr-devel
Vendor: Linux OSS local build
%description
GNU tar with ACL, SELinux and extended attribute support. This latest release
alone is not an assertion that every currently reported tar CVE is fixed.
%prep
%setup -q
patch --fuzz=0 -p1 < %{PATCH23}
patch --fuzz=0 -p1 < %{PATCH24}
patch --fuzz=0 -p1 < %{PATCH0}
patch --fuzz=0 -p1 < %{PATCH1}
patch --fuzz=0 -p1 < %{PATCH2}
patch --fuzz=0 -p1 < %{PATCH3}
patch --fuzz=0 -p1 < %{PATCH4}
patch --fuzz=0 -p1 < %{PATCH5}
patch --fuzz=0 -p1 < %{PATCH6}
patch --fuzz=0 -p1 < %{PATCH7}
patch --fuzz=0 -p1 < %{PATCH8}
patch --fuzz=0 -p1 < %{PATCH9}
patch --fuzz=0 -p1 < %{PATCH10}
patch --fuzz=0 -p1 < %{PATCH11}
patch --fuzz=0 -p1 < %{PATCH12}
patch --fuzz=0 -p1 < %{PATCH13}
patch --fuzz=0 -p1 < %{PATCH14}
patch --fuzz=0 -p1 < %{PATCH15}
patch --fuzz=0 -p1 < %{PATCH16}
patch --fuzz=0 -p1 < %{PATCH17}
patch --fuzz=0 -p1 < %{PATCH18}
patch --fuzz=0 -p1 < %{PATCH19}
patch --fuzz=0 -p1 < %{PATCH20}
patch --fuzz=0 -p1 < %{PATCH21}
# Upstream ACL namespace fix 08c3fc2e has contexts changed by the security
# backports above. Apply the same three identifier renames to that exact tree.
# Keep the original upstream patch in the SRPM as the review source.
python3.11 - <<'PY'
import pathlib,re
p=pathlib.Path('src/xattrs.c');text=p.read_text()
pattern=r'\bacl_(?:get_file_at|set_file_at|delete_def_file_at)\b'
updated,count=re.subn(pattern,lambda m:'tar_'+m.group(),text)
assert count == 15, count
p.write_text(updated)
PY
# The backported openat2 declaration uses gnulib's newer four-argument macro.
# This release has the three-argument form; retain the nonnull attribute on
# the resulting declaration, outside that macro invocation.
python3.11 - <<'PY'
import pathlib,re
p=pathlib.Path('gnu/fcntl.in.h');text=p.read_text()
pattern=r'(_GL_FUNCDECL_SYS \(openat2, int,\s*\(int fd, char const \*file, struct open_how const \*how,\s*size_t size\)),\s*(_GL_ARG_NONNULL \(\(2, 3\)\))\);'
updated,count=re.subn(pattern,r'\1) \2;',text)
assert count==1,count
p.write_text(updated)
PY
%build
export PATH=/opt/linux-oss/build-tools/bin:$PATH
# EL8 backported openat2 headers can contain struct open_how without the
# Linux 5.12 RESOLVE_CACHED constant. Supply its UAPI value for gnulib.
export CPPFLAGS='-DRESOLVE_CACHED=0x20'
autoreconf -fi
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
%{_mandir}/man1/tar.1*
%{_infodir}/tar.info*
%{_datadir}/locale/*/LC_MESSAGES/tar.mo
