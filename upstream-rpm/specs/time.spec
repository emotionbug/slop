Name: time
Version: 1.10
Release: 1.linuxoss%{?dist}
Summary: GNU command resource measurement tool
License: GPLv3+
URL: https://www.gnu.org/software/time/
Source0: time-1.10.tar.gz
BuildRequires: gcc, make, texinfo
Vendor: Linux OSS local build
%description
Latest upstream GNU time, built for EL8 compatibility evaluation.
%prep
%setup -q
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_infodir}/dir
%check
make %{?_smp_mflags} check
%files
%license COPYING
%{_bindir}/time
%{_infodir}/time.info*
