Name: tmux
Version: 3.7c
Release: 1.linuxoss%{?dist}
Summary: tmux upstream EL8 candidate
License: ISC and BSD
URL: https://github.com/tmux/tmux
Source0: tmux-3.7c.tar.gz
BuildRequires: gcc, make, libevent-devel, ncurses-devel
Vendor: Linux OSS local build

%description
Upstream source build for EL8 compatibility evaluation.

%prep
%setup -q -n tmux-3.7c

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
make %{?_smp_mflags} check

%files
%license COPYING
%doc README CHANGES
%{_bindir}/tmux
%{_mandir}/man1/tmux.1*
