Name:           rsync
Version:        3.5.1
Release:        1.linuxoss%{?dist}
Summary:        Upstream rsync build for EL8 compatibility evaluation
License:        GPLv3+ and BSD
URL:            https://rsync.samba.org/
Vendor:         Linux OSS local build
Source0:        rsync-3.5.1.tar.gz
Source1:        xxHash-0.8.4.tar.gz
BuildRequires:  gcc, gcc-c++, make, libacl-devel, libattr-devel
BuildRequires:  openssl-devel, zlib-devel, libzstd-devel, lz4-devel
BuildRequires:  libidn2-devel, acl, attr
BuildRequires:  python3.11
Provides:       bundled(xxhash) = 0.8.4

# No daemon service is installed or enabled by this evaluation package.
# Existing rsync-daemon packages can require a matching EVR: DNF must resolve it.
%description
An upstream rsync build for compatibility evaluation on EL8.
This is a locally maintained package, not a Red Hat package.
xxHash is bundled statically and must be tracked in vulnerability assessments.

%prep
%setup -q -a 1

%build
make -C xxHash-0.8.4 %{?_smp_mflags} libxxhash.a CFLAGS="%{optflags} -fPIC"
export CPPFLAGS="-I$PWD/xxHash-0.8.4"
export LDFLAGS="%{?build_ldflags} -L$PWD/xxHash-0.8.4"
%configure --disable-md2man
make %{?_smp_mflags}

%check
mkdir -p check-bin
ln -s /usr/bin/python3.11 check-bin/python3
export PATH="$PWD/check-bin:$PATH"
make check

%install
make install DESTDIR=%{buildroot}

%files
%license COPYING xxHash-0.8.4/LICENSE
%doc NEWS.md README.md
%{_bindir}/rsync
%{_bindir}/rsync-ssl
%{_mandir}/man1/rsync.1*
%{_mandir}/man1/rsync-ssl.1*
%{_mandir}/man5/rsyncd.conf.5*

%changelog
* Wed Sep 23 2026 Linux OSS local build - 3.5.1-1.linuxoss
- Build upstream release and run upstream tests for EL8 evaluation.
