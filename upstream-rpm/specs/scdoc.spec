Name: scdoc
Version: 1.11.3
Release: 1.linuxoss%{?dist}
Summary: Small manual page compiler for the isolated RPM builder
License: MIT
URL: https://sr.ht/~sircmpwn/scdoc/
Source0: scdoc-1.11.3.tar.gz
BuildRequires: gcc, make
Vendor: Linux OSS local build

%description
Pinned upstream scdoc used to build manual pages for the RPM evaluation tool.

%prep
%setup -q
%build
make %{?_smp_mflags} PREFIX=/usr LDFLAGS='-Wl,-z,relro,-z,now'
%install
make PREFIX=/usr LDFLAGS='-Wl,-z,relro,-z,now' DESTDIR=%{buildroot} install
%check
make LDFLAGS='-Wl,-z,relro,-z,now' check
%files
%license COPYING
/usr/bin/scdoc
/usr/share/man/man1/scdoc.1*
/usr/share/man/man5/scdoc.5*
/usr/share/pkgconfig/scdoc.pc
