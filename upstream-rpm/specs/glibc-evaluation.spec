%global debug_package %{nil}
%global prefix /opt/linux-oss/glibc-2.44
Name:           linuxoss-glibc-evaluation
Version:        2.44
Release:        1.linuxoss%{?dist}
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
../configure --prefix=%{prefix} --libdir=%{prefix}/lib \
  --localedir=/usr/share/locale \
  --enable-kernel=4.18.0 --with-headers=/opt/linux-oss/kernel-uapi-7.2.7/include \
  --enable-stack-protector=strong --disable-werror PYTHON=/usr/bin/python3.11
make %{?_smp_mflags}

%check
export PATH=/opt/rh/gcc-toolset-14/root/usr/bin:$PATH
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

%files
%license COPYING COPYING.LIB LICENSES
%{prefix}/

%changelog
* Wed Sep 23 2026 Linux OSS local build - 2.44-1.linuxoss
- Compile and test upstream libc separately before system ABI migration.
