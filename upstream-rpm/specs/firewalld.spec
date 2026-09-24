%global debug_package %{nil}
BuildRequires: intltool, docbook-style-xsl, libxslt
Name: firewalld
Version: 2.5.2
Release: 1.linuxoss%{?dist}
Summary: firewalld upstream EL8 evaluation build
License: GPLv2+
URL: https://firewalld.org/
Source0: firewalld-2.5.2.tar.bz2
BuildRequires: make, gettext, glib2-devel, python3-devel, python3-dbus, python3-gobject-base, python3-dataclasses >= 0.8-2.linuxoss
Requires: python3-firewall = %{version}-%{release}, firewalld-filesystem = %{version}-%{release}, nftables
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%package filesystem
Summary: filesystem files
%description filesystem
filesystem files.

%package -n python3-firewall
Summary: Firewalld Python bindings
Requires: python3-nftables, python3-dataclasses >= 0.8-2.linuxoss, python3-dbus, python3-gobject-base
%description -n python3-firewall
Python support modules for firewalld.

%prep
%setup -q -n firewalld-2.5.2

%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

./configure --prefix=/usr --libdir=/usr/lib64 --sysconfdir=/etc --disable-static PYTHON=/usr/libexec/platform-python --with-systemd-unitdir=/usr/lib/systemd/system
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
rm -f %{buildroot}%{_infodir}/dir

%check
# Exercise the same offline configuration parser as firewall-offline-cmd.
# The CLI's root requirement is retained in the shipped executable.
PYTHONPATH="%{buildroot}/usr/lib/python3.6/site-packages" /usr/libexec/platform-python - <<'PY'
from firewall import config
from firewall.core.fw import Firewall
from firewall.core.io.functions import check_on_disk_config
config.set_system_config_paths('%{buildroot}/etc/firewalld')
config.set_default_config_paths('%{buildroot}/usr/lib/firewalld')
fw=Firewall(offline=True)
fw.start()
check_on_disk_config(fw)
print('Offline firewall configuration validation passed')
PY

%files
%license COPYING
/usr/bin/*
/usr/sbin/*
/usr/lib/firewalld/
/usr/lib/systemd/*
/usr/share/*
%config(noreplace) /etc/firewalld/*
%config(noreplace) /etc/firewall/applet.conf
%config(noreplace) /etc/logrotate.d/firewalld
%config(noreplace) /etc/modprobe.d/firewalld-sysctls.conf
%config(noreplace) /etc/sysconfig/firewalld
/etc/xdg/autostart/firewall-applet.desktop
%files filesystem
%dir /etc/firewalld
%files -n python3-firewall
/usr/lib/python3.6/site-packages/firewall/
