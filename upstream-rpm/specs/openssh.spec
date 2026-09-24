Name: openssh
%global debug_package %{nil}
Version: 10.3p1
Release: 1.linuxoss%{?dist}
Summary: openssh upstream EL8 evaluation build
License: BSD
URL: https://www.openssh.com/
Source0: openssh-10.3p1.tar.gz
BuildRequires: gcc, make, zlib-devel, openssl-devel, pam-devel, libselinux-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package clients
Summary: clients files
Requires: openssh%{?_isa} = %{version}-%{release}
%description clients
clients files.

%package server
Summary: server files
Requires: openssh%{?_isa} = %{version}-%{release}
%description server
server files.

%prep
%setup -q -n openssh-10.3p1

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-L/opt/linux-oss/openssl-4.0.2/lib64 -Wl,-rpath,/opt/linux-oss/openssl-4.0.2/lib64 -Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static --sysconfdir=/etc/ssh --libexecdir=/usr/libexec/openssh --with-pam --with-selinux --with-privsep-path=/var/empty/sshd --with-ssl-dir=/opt/linux-oss/openssl-4.0.2
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install-nokeys
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
# The entire build is a single-user disposable container; /tmp is its private tmpfs.
TEST_SSH_UNSAFE_PERMISSIONS=1 make tests

%files
%license LICENCE
/usr/bin/ssh-keygen
/usr/share/man/man1/ssh-keygen.*
/usr/libexec/openssh/ssh-keysign
/usr/libexec/openssh/ssh-pkcs11-helper
/usr/libexec/openssh/ssh-sk-helper
%files clients
/usr/bin/scp
/usr/bin/sftp
/usr/bin/ssh
/usr/bin/ssh-add
/usr/bin/ssh-agent
/usr/bin/ssh-keyscan
/usr/share/man/man1/*
%exclude /usr/share/man/man1/ssh-keygen.*
/usr/share/man/man5/ssh_config.*
%config(noreplace) /etc/ssh/ssh_config
%files server
/usr/sbin/sshd
/usr/libexec/openssh/sshd-*
/usr/libexec/openssh/sftp-server
/usr/share/man/man5/sshd_config.*
/usr/share/man/man8/*
%config(noreplace) /etc/ssh/sshd_config
%config(noreplace) /etc/ssh/moduli
/usr/share/man/man5/moduli.5*
