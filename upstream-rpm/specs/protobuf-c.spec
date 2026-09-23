Name: protobuf-c
Version: 1.5.2
Release: 1.linuxoss%{?dist}
Summary: protobuf-c upstream EL8 evaluation build
License: BSD
URL: https://github.com/protobuf-c/protobuf-c
Source0: protobuf-c-1.5.2.tar.gz
BuildRequires: gcc-c++, make, protobuf-devel, protobuf-compiler
Vendor: Linux OSS local build

%description
Upstream build for EL8 evaluation. Target deployment requires separate review.

%package devel
Summary: devel files for %{name}
Requires: %{name}%{?_isa} = %{version}-%{release}
%description devel
devel files for %{name}.

%package compiler
Summary: compiler files for %{name}
Requires: %{name}%{?_isa} = %{version}-%{release}
%description compiler
compiler files for %{name}.

%prep
%setup -q -n protobuf-c-1.5.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE
%doc README.md
%{_libdir}/libprotobuf-c.so.*

%files devel
%{_includedir}/protobuf-c/
%{_includedir}/google/protobuf-c/
%{_libdir}/libprotobuf-c.so
%{_libdir}/pkgconfig/libprotobuf-c.pc

%files compiler
%{_bindir}/protoc-c
%{_bindir}/protoc-gen-c
