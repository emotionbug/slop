%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude (^(ld-linux-x86-64[.]so[.]2|libBrokenLocale[.]so[.]1|libCNS[.]so|libGB[.]so|libISOIR165[.]so|libJIS[.]so|libJISX0213[.]so|libKSC[.]so|libanl[.]so[.]1|libc[.]so[.]6|libc_malloc_debug[.]so[.]0|libdl[.]so[.]2|libm[.]so[.]6|libmemusage[.]so|libmvec[.]so[.]1|libnsl[.]so[.]1|libnss_compat[.]so[.]2|libnss_db[.]so[.]2|libnss_dns[.]so[.]2|libnss_files[.]so[.]2|libnss_hesiod[.]so[.]2|libpcprofile[.]so|libpthread[.]so[.]0|libresolv[.]so[.]2|librt[.]so[.]1|libthread_db[.]so[.]1|libutil[.]so[.]1)[(])
%global __strip /opt/rh/gcc-toolset-14/root/usr/bin/strip
%global __objdump /opt/rh/gcc-toolset-14/root/usr/bin/objdump
%global prefix /opt/linux-oss/glibc-2.44
Name:           linuxoss-glibc-evaluation
Version:        2.44
Release: 2.linuxoss%{?dist}
Summary:        Private glibc build for ABI and runtime evaluation
License:        LGPLv2+ and GPLv2+
URL:            https://www.gnu.org/software/libc/
Vendor:         Linux OSS local build
Source0:        glibc-2.44.tar.xz
BuildRequires:  gcc-toolset-14-gcc, gcc-toolset-14-gcc-c++, gcc-toolset-14-binutils
BuildRequires:  make, bison, python3.11, texinfo, libselinux-devel, linuxoss-kernel-uapi = 7.2.7

%description
Private glibc runtime for testing the latest implementation before preparing
system replacement packages. Installing it alone does not remediate the
existing system glibc. Applications require the private loader explicitly.

%prep
%if 0%{?reuse_prepared}
test -d %{_builddir}/glibc-%{version}/build
%setup -q -T -D -n glibc-%{version}
%else
%setup -q -n glibc-%{version}
%endif

%build
export PATH=/opt/rh/gcc-toolset-14/root/usr/bin:$PATH
mkdir -p build
cd build
%if 0%{?reuse_configured}
# Packaging-only retries may reuse configuration after build-rpm.sh verifies
# every original source file. Refuse a cache configured with different paths.
expected='--prefix=%{prefix} --libdir=%{prefix}/lib --sysconfdir=/etc --localedir=/usr/share/locale --enable-kernel=4.18.0 --with-headers=/opt/linux-oss/kernel-uapi-7.2.7/include --enable-stack-protector=strong --disable-werror PYTHON=/usr/bin/python3.11'
test "$(/bin/sh ./config.status --config)" = "$expected"
%else
../configure --prefix=%{prefix} --libdir=%{prefix}/lib \
  --sysconfdir=/etc --localedir=/usr/share/locale \
  --enable-kernel=4.18.0 --with-headers=/opt/linux-oss/kernel-uapi-7.2.7/include \
  --enable-stack-protector=strong --disable-werror PYTHON=/usr/bin/python3.11
%endif
make %{?_smp_mflags}

%check
export PATH=/opt/rh/gcc-toolset-14/root/usr/bin:$PATH
# The private-prefix test subprocess loader also needs GCC's unwind runtime.
# Keep it in the test build directory; it is not installed into the RPM.
# See glibc bug 32869 (tst-setvbuf2 / pthread_cancel).
install -m 0644 "$(gcc -print-file-name=libgcc_s.so.1)" build/libgcc_s.so.1
export TIMEOUTFACTOR=4
%if 0%{?reuse_prepared}
# Retain the old failure evidence, then rerun failed tests with the repaired
# runtime search path/time allowance. No tests or assertions are excluded.
prior=$(mktemp -d /output/prior-failed-tests.XXXXXX)
if test -f build/tests.sum; then cp build/tests.sum "$prior/"; fi
python3.11 - "$prior" <<'PY'
import pathlib,shutil,sys
root=pathlib.Path('build'); destination=pathlib.Path(sys.argv[1])
for result in root.rglob('*.test-result'):
    if not any(line.startswith('FAIL:') for line in result.read_text(errors='replace').splitlines()):
        continue
    for original in (result, result.with_suffix('.out')):
        if not original.is_file():continue
        target=destination/original.relative_to(root)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(original,target);original.unlink()
PY
# Regenerate disposable test roots after configure path changes.
%if !0%{?reuse_configured}
rm -rf build/testroot.root build/testroot.pristine
%endif
%endif
# The upstream test root copies the shell's dependencies, but not nscd's
# SELinux dependencies. Supply those two unchanged EL8 libraries only in the
# disposable root; the tested libc and pthread implementation remain 2.44.
make -C build "$PWD/build/testroot.pristine/install.stamp"
for library in libselinux.so.1 libpcre2-8.so.0 libgcc_s.so.1; do
  install -m 0755 "/usr/lib64/$library" "build/testroot.pristine%{prefix}/lib/$library"
done
# Some upstream container tests call /sbin/ldconfig and PATH getent even
# with a private --prefix. Provide the newly built tools at those paths only
# inside the disposable test root. Otherwise they fail with ENOENT.
mkdir -p build/testroot.pristine/sbin build/testroot.pristine/usr/bin
install -m 0755 build/elf/ldconfig build/testroot.pristine/sbin/ldconfig
install -m 0755 build/nss/getent build/testroot.pristine/usr/bin/getent
make -C build %{?_smp_mflags} check

%install
make -C build install_root=%{buildroot} install
# Keep the standard locale-directory string, which is exported as a sized
# GLIBC_2.2.5 data symbol. Store the evaluation build's translations privately;
# this RPM must not overwrite the host's message catalogs.
if test -d %{buildroot}/usr/share/locale; then
  mkdir -p %{buildroot}%{prefix}/share
  mv %{buildroot}/usr/share/locale %{buildroot}%{prefix}/share/locale
fi
# Runtime reads the host's standard /etc configuration, but evaluation RPM
# payload must not overwrite any of those files.
if test -d %{buildroot}/etc; then
  mkdir -p %{buildroot}%{prefix}/share/evaluation-config
  cp -a %{buildroot}/etc/. %{buildroot}%{prefix}/share/evaluation-config/
  rm -rf %{buildroot}/etc
fi

%files
%license COPYING.LIB COPYING.LESSERv2 COPYINGv2 COPYINGv3 LICENSES
%{prefix}/

%changelog
* Wed Sep 23 2026 Linux OSS local build - 2.44-1.linuxoss
- Compile and test upstream libc separately before system ABI migration.
