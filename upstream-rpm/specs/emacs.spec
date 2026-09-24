Name: emacs
Epoch: 1
Version: 31.1
Release: 1.linuxoss%{?dist}
Summary: emacs upstream EL8 evaluation build
License: GPLv3+
URL: https://www.gnu.org/software/emacs/
Source0: emacs-31.1.tar.xz
BuildRequires: gcc, make, ncurses-devel, gnutls-devel, libxml2-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package filesystem
Summary: filesystem files
%description filesystem
filesystem files.

%prep
%setup -q -n emacs-31.1

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --without-x --without-dbus --without-sound --without-gpm --without-native-compilation --with-json --with-modules
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
mkdir -p %{buildroot}/usr/share/emacs/site-lisp
%check
src/emacs --batch -Q --eval '(unless (= (+ 20 22) 42) (kill-emacs 1))'
src/emacs --batch -Q --eval '(unless (equal (json-serialize [1 2 3]) "[1,2,3]") (kill-emacs 1))'

%files
%license COPYING
/usr/bin/*
/usr/include/emacs-module.h
/usr/lib/systemd/user/emacs.service
/usr/libexec/emacs/
/usr/share/emacs/31.1/
/usr/share/info/*
/usr/share/man/*/*
/usr/share/applications/*
/usr/share/icons/*
/usr/share/metainfo/*
%files filesystem
%dir /usr/share/emacs
/usr/share/emacs/site-lisp/
