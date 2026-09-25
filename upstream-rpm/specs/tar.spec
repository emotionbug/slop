Name: tar
Epoch: 2
Version: 1.35
Release: 4.linuxoss%{?dist}
Summary: GNU tar, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/tar/
Source0: tar-1.35.tar.xz
Source1: tar-1.35-13.el10_2.src.rpm
BuildRequires: gcc, make, libselinux-devel, libacl-devel, libattr-devel
Vendor: Linux OSS local build
Provides: /bin/tar /bin/gtar
%description
GNU tar with ACL, SELinux and extended attribute support. This latest release
alone is not an assertion that every currently reported tar CVE is fixed.
%prep
%setup -q
# Reproduce the official, pinned GNU tar 1.35 backport sequence. The EL10
# source RPM is only a source container; no EL10 binary is installed.
mkdir vendor-patches
(cd vendor-patches; rpm2cpio %{SOURCE1} | cpio -idm --quiet '*.patch')
patch --fuzz=0 -p1 < vendor-patches/tar-1.28-loneZeroWarning.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.28-vfatTruncate.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.29-wildcards.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.28-atime-rofs.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.28-document-exclude-mistakes.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.33-fix-capabilities-test.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-padding-zeros.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.30-disk-read-error.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-fix-spurious-diagnostic-during-extraction-of-.-with-keep-newer-files.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-add-forgotten-tests-from-upstream.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-revert-fix-savannah-bug-633567.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-Fix-Savane-bug-64581.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-no-overwrite-dir-no-overwrite-even-temporarily.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-CVE-2025-45582.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-tar-one-top-level-DIR-must-be-relative.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-Avoid-acl_-prefix-for-functions.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-CVE-2026-5704.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-fix-absolute-one-top-level.patch
patch --fuzz=0 -p1 < vendor-patches/tar-1.35-CVE-2026-18477.patch
%build
export PATH=/opt/linux-oss/build-tools/bin:$PATH
# EL8 backported openat2 headers can contain struct open_how without the
# Linux 5.12 RESOLVE_CACHED constant. Supply its UAPI value for gnulib.
export CPPFLAGS='-DRESOLVE_CACHED=0x20'
autoreconf -v
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --with-rmt=/usr/sbin/rmt
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
ln -s tar %{buildroot}%{_bindir}/gtar
rm -f %{buildroot}%{_infodir}/dir
%check
make %{?_smp_mflags} check
%files
%license COPYING
%doc NEWS README
%{_bindir}/tar
%{_bindir}/gtar
%{_mandir}/man1/tar.1*
%{_infodir}/tar.info*
%{_datadir}/locale/*/LC_MESSAGES/tar.mo
