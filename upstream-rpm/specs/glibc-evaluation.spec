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
BuildRequires:  make, bison, python3.11, texinfo, kernel-headers

%description
Private glibc runtime for testing the latest implementation before preparing
system replacement packages. Installing it alone does not remediate the
existing system glibc. Applications require the private loader explicitly.

%prep
%setup -q -n glibc-%{version}

%build
export PATH=/opt/rh/gcc-toolset-14/root/usr/bin:$PATH
mkdir build
cd build
../configure --prefix=%{prefix} --libdir=%{prefix}/lib \
  --enable-kernel=4.18.0 --with-headers=/usr/include \
  --enable-stack-protector=strong --disable-werror PYTHON=/usr/bin/python3.11
make %{?_smp_mflags}

%check
export PATH=/opt/rh/gcc-toolset-14/root/usr/bin:$PATH
make -C build %{?_smp_mflags} check

%install
make -C build install_root=%{buildroot} install

%files
%license COPYING COPYING.LIB LICENSES
%{prefix}/

%changelog
* Wed Sep 23 2026 Linux OSS local build - 2.44-1.linuxoss
- Compile and test upstream libc separately before system ABI migration.
