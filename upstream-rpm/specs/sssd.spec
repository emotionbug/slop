%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude ((^lib(crypto|ssl)[.]so[.]3|^(_py3hbac[.]so|_py3sss[.]so|_py3sss_murmur[.]so|_py3sss_nss_idmap[.]so|cifs_idmap_sss[.]so|libifp_iface[.]so|libifp_iface_sync[.]so|libipa_hbac[.]so[.]0|libnss_sss[.]so[.]2|libsss_ad[.]so|libsss_autofs[.]so|libsss_cert[.]so|libsss_certmap[.]so[.]0|libsss_child[.]so|libsss_crypt[.]so|libsss_debug[.]so|libsss_idmap[.]so[.]0|libsss_iface[.]so|libsss_iface_sync[.]so|libsss_ipa[.]so|libsss_krb5[.]so|libsss_krb5_common[.]so|libsss_ldap[.]so|libsss_ldap_common[.]so|libsss_nss_idmap[.]so[.]0|libsss_proxy[.]so|libsss_sbus[.]so|libsss_sbus_sync[.]so|libsss_simple[.]so|libsss_sudo[.]so|libsss_util[.]so|memberof[.]so|pam_sss[.]so|pam_sss_gss[.]so|sss[.]so|sssd_krb5_idp_plugin[.]so|sssd_krb5_localauth_plugin[.]so|sssd_krb5_locator_plugin[.]so|sssd_pac_plugin[.]so|winbind_idmap_sss[.]so)[(])|^(_py3hbac[.]so|_py3sss[.]so|_py3sss_murmur[.]so|_py3sss_nss_idmap[.]so|cifs_idmap_sss[.]so|libifp_iface[.]so|libifp_iface_sync[.]so|libipa_hbac[.]so[.]0|libnss_sss[.]so[.]2|libsss_ad[.]so|libsss_autofs[.]so|libsss_cert[.]so|libsss_certmap[.]so[.]0|libsss_child[.]so|libsss_crypt[.]so|libsss_debug[.]so|libsss_idmap[.]so[.]0|libsss_iface[.]so|libsss_iface_sync[.]so|libsss_ipa[.]so|libsss_krb5[.]so|libsss_krb5_common[.]so|libsss_ldap[.]so|libsss_ldap_common[.]so|libsss_nss_idmap[.]so[.]0|libsss_proxy[.]so|libsss_sbus[.]so|libsss_sbus_sync[.]so|libsss_simple[.]so|libsss_sudo[.]so|libsss_util[.]so|memberof[.]so|pam_sss[.]so|pam_sss_gss[.]so|sss[.]so|sssd_krb5_idp_plugin[.]so|sssd_krb5_localauth_plugin[.]so|sssd_krb5_locator_plugin[.]so|sssd_pac_plugin[.]so|winbind_idmap_sss[.]so)[(])
BuildRequires: samba-winbind-clients, libnfsidmap-devel, libunistring-devel, libsemanage-devel, libselinux-devel, valgrind-devel
BuildRequires: cifs-utils-devel
BuildRequires: bind-utils, softhsm
Name: linuxoss-sssd-evaluation
Version: 2.13.1
Release: 3.linuxoss%{?dist}
Summary: linuxoss-sssd-evaluation upstream EL8 evaluation build
License: GPLv3+
URL: https://github.com/SSSD/sssd
Source0: sssd-2.13.1.tar.gz
BuildRequires: gcc, make, libini_config-devel, libdhash-devel, libldb-devel, libtalloc-devel, libtevent-devel, libtdb-devel, libnl3-devel, libjose-devel, c-ares-devel, jansson-devel, popt-devel, openldap-devel, krb5-devel, pam-devel, python3-devel, systemd-devel, libcmocka-devel, samba-devel, libsmbclient-devel
Requires: linuxoss-openssl35 >= 3.5.8
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%global prefix /opt/linux-oss/sssd-2.13.1
%global __brp_mangle_shebangs %{nil}
%prep
%setup -q -n sssd-2.13.1
%build
export PKG_CONFIG_PATH=/opt/linux-oss/openssl-3.5.8/lib64/pkgconfig
export CPPFLAGS="-D_GNU_SOURCE -I/opt/linux-oss/openssl-3.5.8/include"
export LDFLAGS='-Wl,--build-id -Wl,-rpath,%{prefix}/lib64:%{prefix}/lib64/sssd -L/opt/linux-oss/openssl-3.5.8/lib64 -Wl,-rpath,/opt/linux-oss/openssl-3.5.8/lib64'
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong'
./configure --prefix=%{prefix} --libdir=%{prefix}/lib64 --sysconfdir=%{prefix}/etc --localstatedir=%{prefix}/var --disable-static --disable-rpath --with-python3-bindings --without-python2-bindings --without-manpages --without-passkey --without-subid --with-id-provider-idp=no --with-initscript=systemd --with-syslog=journald --with-ldb-lib-dir=%{prefix}/lib64/ldb/modules/ldb --with-tmpfilesdir=%{prefix}/lib/tmpfiles.d --with-udevrulesdir=%{prefix}/lib/udev/rules.d --with-systemd-sysusersdir=%{prefix}/lib/sysusers.d --with-init-dir=%{prefix}/lib/systemd/system --with-tapset-install-dir=%{prefix}/share/systemtap/tapset
make -j2
%install
make DESTDIR=%{buildroot} install
find %{buildroot} -name '*.la' -delete
find %{buildroot}%{prefix} -type f -exec grep -IlZ -m1 '^#!/usr/bin/python$' {} + | xargs -0 -r sed -i '1s|^#!/usr/bin/python$|#!/usr/bin/python3|'
%check
export LD_LIBRARY_PATH=/opt/linux-oss/openssl-3.5.8/lib64
make -j2 check
%files
%license COPYING
%{prefix}/
