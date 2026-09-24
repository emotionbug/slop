%global debug_package %{nil}
%global __strip /bin/true
Name: nss
Version: 3.130
Release: 1.linuxoss%{?dist}
Summary: nss upstream EL8 evaluation build
License: MPL-2.0
URL: https://firefox-source-docs.mozilla.org/security/nss/
Source0: nss-3.130-with-nspr-4.39.tar.gz
BuildRequires: gcc, gcc-c++, make, zlib-devel, sqlite-devel, perl
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package softokn
Summary: softokn files
%description softokn
softokn files.

%package softokn-freebl
Summary: softokn-freebl files
%description softokn-freebl
softokn-freebl files.

%package util
Summary: util files
%description util
util files.

%package tools
Summary: tools files
%description tools
tools files.

%package devel
Summary: devel files
%description devel
devel files.

%prep
%if 0%{?reuse_prepared}
%setup -q -D -T -n nss-3.130
%else
%setup -q -n nss-3.130
%endif
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

make -C nss %{?_smp_mflags} nss_build_all BUILD_OPT=1 USE_64=1 NSS_USE_SYSTEM_SQLITE=1 NSS_ENABLE_WERROR=0
%install
obj=$(find dist -maxdepth 1 -type d -name '*.OBJ' | head -n 1)
test -n "$obj"
mkdir -p %{buildroot}/usr/lib64 %{buildroot}/usr/bin %{buildroot}/usr/include/nss
cp -a "$obj"/lib/lib{nss3,nssdbm3,nssckbi,nssutil3,smime3,ssl3,softokn3,freebl3,freeblpriv3}.so %{buildroot}/usr/lib64/
find "$obj/lib" -maxdepth 1 -name '*.chk' -exec cp -t %{buildroot}/usr/lib64 -- {} +
for t in certutil cmsutil crlutil modutil pk12util signtool signver ssltap; do cp "$obj/bin/$t" %{buildroot}/usr/bin/; done
cp -a dist/public/nss/*.h %{buildroot}/usr/include/nss/
%check
obj=$(find dist -maxdepth 1 -type d -name '*.OBJ' | head -n 1)
export LD_LIBRARY_PATH="$PWD/$obj/lib"
testdb=$(mktemp -d "$PWD/nss-testdb.XXXXXX")
"$obj/bin/certutil" -N --empty-password -d "sql:$testdb"
for t in der_gtest freebl_gtest util_gtest; do "$obj/bin/$t" -w -d "sql:$testdb" -s "$PWD/nss/gtests/$t"; done

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%post softokn -p /sbin/ldconfig
%postun softokn -p /sbin/ldconfig

%post softokn-freebl -p /sbin/ldconfig
%postun softokn-freebl -p /sbin/ldconfig

%post util -p /sbin/ldconfig
%postun util -p /sbin/ldconfig

%files
%license nss/COPYING
/usr/lib64/libnss3.so
/usr/lib64/libnssckbi.so
/usr/lib64/libsmime3.so
/usr/lib64/libssl3.so
%files softokn
/usr/lib64/libsoftokn3.so
/usr/lib64/libsoftokn3.chk
/usr/lib64/libnssdbm3.so
/usr/lib64/libnssdbm3.chk
%files softokn-freebl
/usr/lib64/libfreebl3.so
/usr/lib64/libfreeblpriv3.so
/usr/lib64/libfreebl3.chk
/usr/lib64/libfreeblpriv3.chk
%files util
/usr/lib64/libnssutil3.so
%files tools
/usr/bin/*
%files devel
/usr/include/nss/
