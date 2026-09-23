Name: libtheora
Version: 1.2.0
Release: 1.linuxoss%{?dist}
Epoch: 1
Summary: libtheora upstream EL8 evaluation
License: BSD
URL: https://www.theora.org/
Source0: libtheora-1.2.0.tar.gz
BuildRequires: gcc, make, libogg-devel, libvorbis-devel, libpng-devel, SDL-devel
Vendor: Linux OSS local build

%description
Upstream source build. Target ABI and runtime qualification are separate.

%package devel
Summary: devel files from libtheora
Requires: %{name}%{?_isa} = %{epoch}:%{version}-%{release}
%description devel
devel files from libtheora.

%package -n theora-tools
Summary: theora-tools files from libtheora
Requires: %{name}%{?_isa} = %{epoch}:%{version}-%{release}
%description -n theora-tools
theora-tools files from libtheora.

%prep
%setup -q -n libtheora-1.2.0

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --disable-oggtest --disable-vorbistest
make %{?_smp_mflags}


%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name "*.la" -delete
mkdir -p %{buildroot}%{_bindir}
install -m0755 examples/.libs/encoder_example %{buildroot}%{_bindir}/theora_encode
install -m0755 examples/.libs/dump_video %{buildroot}%{_bindir}/theora_dump_video
install -m0755 examples/.libs/png2theora %{buildroot}%{_bindir}/png2theora
install -m0755 examples/.libs/player_example %{buildroot}%{_bindir}/theora_player
rm -rf %{buildroot}%{_datadir}/doc/libtheora-1.2.0

%check
make %{?_smp_mflags} check

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%license LICENSE COPYING
%{_libdir}/libtheora*.so.*

%files devel
%{_includedir}/theora/
%{_libdir}/libtheora*.so
%{_libdir}/pkgconfig/theora*.pc
%{_datadir}/doc/libtheora/

%files -n theora-tools
%{_bindir}/*
