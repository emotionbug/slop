Name: bzip2
Version: 1.0.8
Release: 2.linuxoss%{?dist}
Summary: Bzip2 compression utilities with the upstream recovery bounds fix
License: BSD
URL: https://sourceware.org/bzip2/
Source0: bzip2-1.0.8.tar.gz
Patch0: bzip2-CVE-2026-42250.patch
Patch1: bzip2recover-race-open-output.patch
BuildRequires: gcc, make, python3.11
Requires: bzip2-libs%{?_isa} = %{version}-%{release}
Vendor: Linux OSS local build
%description
Bzip2 compression utilities with CVE-2026-42250 fixed. EL8's existing
libbz2.so.1 SONAME is retained; runtime compatibility is tested separately.
%package libs
Summary: Shared bzip2 compression library
%description libs
Shared compression library retaining the EL8 SONAME.
%package devel
Summary: Bzip2 development headers and link
Requires: bzip2-libs%{?_isa} = %{version}-%{release}
%description devel
Headers and unversioned link for the shared bzip2 library.
%prep
%setup -q
patch --fuzz=0 -p1 < %{PATCH0}
patch --fuzz=0 -p1 < %{PATCH1}
%build
flags='-O2 -g -gdwarf-4 -fPIC -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2 -D_FILE_OFFSET_BITS=64'
make %{?_smp_mflags} CC=/usr/bin/gcc CFLAGS="$flags"
# Link the shared object with the SONAME used by the installed RHEL package.
/usr/bin/gcc -shared -Wl,-soname,libbz2.so.1 -Wl,--build-id,-z,relro,-z,now \
  -Wl,--undefined=__bss_start,--undefined=_edata,--undefined=_end \
  -o libbz2.so.1.0.8 blocksort.o huffman.o crctable.o randtable.o compress.o decompress.o bzlib.o
ln -s libbz2.so.1.0.8 libbz2.so.1
/usr/bin/gcc $flags -Wl,--build-id,-z,relro,-z,now -o bzip2-shared bzip2.c ./libbz2.so.1.0.8
%install
make install PREFIX=%{buildroot}/usr
install -d %{buildroot}%{_datadir}
mv %{buildroot}/usr/man %{buildroot}%{_mandir}
rm -f %{buildroot}/usr/lib/libbz2.a
rmdir %{buildroot}/usr/lib
install -d %{buildroot}%{_libdir}
install -m 0755 libbz2.so.1.0.8 %{buildroot}%{_libdir}/
ln -s libbz2.so.1.0.8 %{buildroot}%{_libdir}/libbz2.so.1
ln -s libbz2.so.1 %{buildroot}%{_libdir}/libbz2.so
install -m 0755 bzip2-shared %{buildroot}%{_bindir}/bzip2
# Upstream installs independent copies for bunzip2/bzcat; keep one ELF image.
rm -f %{buildroot}%{_bindir}/bunzip2 %{buildroot}%{_bindir}/bzcat
ln -s bzip2 %{buildroot}%{_bindir}/bunzip2
ln -s bzip2 %{buildroot}%{_bindir}/bzcat
ln -sfn bzdiff %{buildroot}%{_bindir}/bzcmp
ln -sfn bzgrep %{buildroot}%{_bindir}/bzegrep
ln -sfn bzgrep %{buildroot}%{_bindir}/bzfgrep
ln -sfn bzmore %{buildroot}%{_bindir}/bzless
mkdir -p %{buildroot}%{_libdir}/pkgconfig
cat > %{buildroot}%{_libdir}/pkgconfig/bzip2.pc <<'PC'
prefix=/usr
libdir=/usr/lib64
includedir=/usr/include

Name: bzip2
Description: Bzip2 compression library
Version: 1.0.8
Libs: -L${libdir} -lbz2
Cflags: -I${includedir}
PC
%check
make test
for level in 1 9; do
  LD_LIBRARY_PATH=$PWD ./bzip2-shared -$level -c sample1.ref > sample.test.bz2
  LD_LIBRARY_PATH=$PWD ./bzip2-shared -dc sample.test.bz2 > sample.test.out
  cmp sample1.ref sample.test.out
done
%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig
%files
%license LICENSE
%doc CHANGES README
%{_bindir}/*
%{_mandir}/man1/*
%files libs
%license LICENSE
%{_libdir}/libbz2.so.1*
%files devel
%{_includedir}/bzlib.h
%{_libdir}/libbz2.so
%{_libdir}/pkgconfig/bzip2.pc
