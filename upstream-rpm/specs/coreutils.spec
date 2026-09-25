Name: coreutils
Version: 9.12
Release: 2.linuxoss%{?dist}
Summary: coreutils upstream EL8 evaluation build
License: GPLv3+
URL: https://www.gnu.org/software/coreutils/
Source0: coreutils-9.12.tar.xz
Source1: el8-DIR_COLORS
Source2: el8-DIR_COLORS.256color
Source3: el8-DIR_COLORS.lightbgcolor
Source4: el8-colorls.sh
Source5: el8-colorls.csh
BuildRequires: gcc, make, gmp-devel, libacl-devel, libattr-devel, libcap-devel, libselinux-devel, openssl-devel, perl, gettext
Vendor: Linux OSS local build
Requires: coreutils-common = %{version}-%{release}
Conflicts: coreutils-single
# Preserve EL8's exact legacy file capabilities across the /usr merge.
Provides: /bin/basename /bin/cat /bin/chgrp /bin/chmod /bin/chown /bin/cp /bin/cut
Provides: /bin/date /bin/dd /bin/df /bin/echo /bin/env /bin/false /bin/ln /bin/ls
Provides: /bin/mkdir /bin/mknod /bin/mktemp /bin/mv /bin/nice /bin/pwd /bin/readlink
Provides: /bin/rm /bin/rmdir /bin/sleep /bin/sort /bin/stty /bin/sync /bin/touch
Provides: /bin/true /bin/uname

%description
Upstream build for EL8 evaluation. Target deployment requires separate review.

%package common
Summary: Common documentation and locale data for GNU coreutils
BuildArch: noarch
%description common
Common upstream files and the EL8 color configuration defaults.

%prep
%setup -q -n coreutils-9.12

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --libexecdir=/usr/libexec --enable-no-install-program=hostname,kill,uptime --enable-install-program=arch --with-selinux
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir
install -d %{buildroot}%{_sbindir}
mv %{buildroot}%{_bindir}/chroot %{buildroot}%{_sbindir}/chroot
ln -s ../sbin/chroot %{buildroot}%{_bindir}/chroot
install -Dm0644 %{SOURCE1} %{buildroot}/etc/DIR_COLORS
install -Dm0644 %{SOURCE2} %{buildroot}/etc/DIR_COLORS.256color
install -Dm0644 %{SOURCE3} %{buildroot}/etc/DIR_COLORS.lightbgcolor
install -Dm0644 %{SOURCE4} %{buildroot}/etc/profile.d/colorls.sh
install -Dm0644 %{SOURCE5} %{buildroot}/etc/profile.d/colorls.csh

%check
make %{?_smp_mflags} check

%post common
if [ -x /sbin/install-info ]; then
  /sbin/install-info %{_infodir}/coreutils.info.gz %{_infodir}/dir || :
fi

%preun common
if [ "$1" = 0 ] && [ -x /sbin/install-info ]; then
  /sbin/install-info --delete %{_infodir}/coreutils.info.gz %{_infodir}/dir || :
fi

%files
%license COPYING
%{_bindir}/*
%{_sbindir}/chroot
%{_libexecdir}/coreutils/

%files common
%license COPYING
%doc README NEWS
%{_mandir}/man1/*
%{_infodir}/coreutils.info*
%{_datadir}/locale/*/LC_MESSAGES/coreutils.mo
%{_datadir}/locale/*/LC_TIME/coreutils.mo
%config(noreplace) /etc/DIR_COLORS
%config(noreplace) /etc/DIR_COLORS.256color
%config(noreplace) /etc/DIR_COLORS.lightbgcolor
%config(noreplace) /etc/profile.d/colorls.sh
%config(noreplace) /etc/profile.d/colorls.csh
