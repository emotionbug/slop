%global debug_package %{nil}
%global prefix /opt/linux-oss/kernel-uapi-7.2.7
Name:           linuxoss-kernel-uapi
Version:        7.2.7
Release:        1.linuxoss%{?dist}
Summary:        Private Linux UAPI headers for the isolated glibc builder
License:        GPL-2.0-only WITH Linux-syscall-note
URL:            https://www.kernel.org/
Vendor:         Linux OSS local build
Source0:        linux-7.2.7.tar.xz
BuildRequires:  gcc, make, rsync
%description
Private build-only Linux userspace API headers. This package does not replace
the server's kernel-headers RPM or modify the running kernel.
%prep
%setup -q -n linux-%{version}
%build
make %{?_smp_mflags} headers_install INSTALL_HDR_PATH="$PWD/uapi"
%check
test -f uapi/include/linux/version.h
test -f uapi/include/asm/unistd_64.h
cat > check-uapi.c <<'C'
#include <linux/version.h>
#include <linux/mman.h>
#include <linux/futex.h>
#if LINUX_VERSION_CODE != KERNEL_VERSION(7, 2, 7)
#error Wrong kernel header version
#endif
int main(void) { return MAP_PRIVATE != 2 || FUTEX_WAIT != 0; }
C
gcc -Iuapi/include check-uapi.c -o check-uapi
./check-uapi
%install
mkdir -p %{buildroot}%{prefix}
cp -a uapi/include %{buildroot}%{prefix}/
%files
%license COPYING LICENSES/exceptions/Linux-syscall-note
%{prefix}/
%changelog
* Thu Sep 24 2026 Linux OSS local build - 7.2.7-1.linuxoss
- Keep current Linux UAPI headers private to the glibc build environment.
