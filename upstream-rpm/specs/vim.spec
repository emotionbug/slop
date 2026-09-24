Name: vim
Version: 9.2.1125
Epoch: 2
Release: 1.linuxoss%{?dist}
Summary: vim upstream EL8 evaluation build
License: Vim
URL: https://github.com/vim/vim
Source0: vim-9.2.1125.tar.gz
BuildRequires: gcc, make, ncurses-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package common
Summary: common files
%description common
common files.

%package enhanced
Summary: enhanced files
%description enhanced
enhanced files.

%package minimal
Summary: minimal files
%description minimal
minimal files.

%package filesystem
Summary: filesystem files
%description filesystem
filesystem files.

%prep
%setup -q -n vim-9.2.1125
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --with-features=tiny --disable-gui --without-x --disable-nls --disable-channel --disable-netbeans
make %{?_smp_mflags}
cp src/vim vim-tiny
make distclean
./configure --prefix=/usr --with-features=huge --disable-gui --without-x --enable-multibyte --disable-pythoninterp --disable-python3interp
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
install -m0755 vim-tiny %{buildroot}/usr/bin/vi
mkdir -p %{buildroot}/usr/share/vim/vimfiles
find %{buildroot}/usr/share/vim -type f -name '*.py' -exec chmod 0644 {} +
%check
VIMRUNTIME="$PWD/runtime" src/vim -u NONE -i NONE -N -es -c 'call writefile([string(6 * 7)], "vim-smoke.txt")' -c 'qa!'
grep -qx 42 vim-smoke.txt
src/vim --version | grep '9.2'
./vim-tiny --version | grep 'Tiny version'
%files
%license LICENSE
%files common
/usr/share/vim/vim92/
%files enhanced
/usr/bin/*
%exclude /usr/bin/vi
/usr/share/man/*
/usr/share/applications/*
/usr/share/icons/*
%files minimal
/usr/bin/vi
%files filesystem
%dir /usr/share/vim
%dir /usr/share/vim/vimfiles
