Name:           libarchive
Version:        3.8.9
Release:        1.linuxoss%{?dist}
Summary:        Multi-format archive library, upstream EL8 candidate
License:        BSD-2-Clause AND BSD-3-Clause AND Public-Domain
URL:            https://www.libarchive.org/
Vendor:         Linux OSS local build
Source0:        libarchive-3.8.9.tar.xz
BuildRequires:  gcc, make, zlib-devel, bzip2-devel, xz-devel, libzstd-devel
BuildRequires:  lz4-devel, openssl-devel, libxml2-devel, libacl-devel, libattr-devel

%description
Multi-format archive library with its upstream parser and CLI regression tests.

%package devel
Summary:        Archive library development files
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description devel
Headers, link metadata and API manual pages for libarchive.

%package -n bsdtar
Summary:        BSD archive utilities
Requires:       %{name}%{?_isa} = %{version}-%{release}
%description -n bsdtar
bsdtar, bsdcpio, bsdcat and bsdunzip from libarchive.

%prep
%setup -q
%build
%configure --disable-static --enable-shared --enable-acl --enable-xattr \
  --with-zlib --with-bz2lib --with-lzma --with-zstd --with-lz4 --without-lzo2 \
  --with-openssl --with-xml2
make %{?_smp_mflags}
%check
make %{?_smp_mflags} check
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%license COPYING
%doc NEWS README.md
%{_libdir}/libarchive.so.13*
%{_mandir}/man5/*
%files devel
%{_includedir}/archive*.h
%{_libdir}/libarchive.so
%{_libdir}/pkgconfig/libarchive.pc
%{_mandir}/man3/*
%files -n bsdtar
%{_bindir}/bsd*
%{_mandir}/man1/*

%changelog
* Thu Sep 24 2026 Linux OSS local build - 3.8.9-1.linuxoss
- Build pinned upstream release with compression, crypto, XML and ACL support.
