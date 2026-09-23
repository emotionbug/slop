Name: nano
Version: 9.2
Release: 1.linuxoss%{?dist}
Summary: nano upstream EL8 candidate
License: GPLv3+
URL: https://www.nano-editor.org/
Source0: nano-9.2.tar.xz
BuildRequires: gcc, make, ncurses-devel, gettext
Vendor: Linux OSS local build

%description
Upstream source build for EL8 compatibility evaluation.

%prep
%setup -q -n nano-9.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --enable-utf8
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
install -Dm0644 doc/sample.nanorc %{buildroot}%{_sysconfdir}/nanorc
%check
make %{?_smp_mflags} check

%files
%license COPYING COPYING.DOC
%doc README NEWS
%{_docdir}/nano/*.html
%{_bindir}/nano
%{_bindir}/rnano
%config(noreplace) %{_sysconfdir}/nanorc
%{_datadir}/nano/
%{_datadir}/locale/*/LC_MESSAGES/nano.mo
%{_mandir}/man1/*
%{_mandir}/man5/*
%{_infodir}/nano.info*
