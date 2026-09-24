%global debug_package %{nil}
%global __provides_exclude_from ^/opt/linux-oss/.*
%global __requires_exclude (^perl[(].*|^(libperl[.]so)[(])
%global __provides_exclude ^perl.*
Name: linuxoss-perl544
Version: 5.44.0
Release: 2.linuxoss%{?dist}
Summary: linuxoss-perl544 upstream EL8 evaluation build
License: Artistic and GPLv1+
URL: https://www.perl.org/
Source0: perl-5.44.0.tar.xz
BuildRequires: gcc, make, gdbm-devel
Vendor: Linux OSS local build

%description
Parallel runtime under /opt. Existing EL8 Perl modules and system Perl are not replaced.
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%global prefix /opt/linux-oss/perl-5.44.0
%prep
%setup -q -n perl-5.44.0
%build
sh Configure -des -Dprefix=%{prefix} -Duseshrplib -Dusethreads -Dcc=gcc -Dccflags='-O2 -g -gdwarf-4 -fstack-protector-strong' -Dldflags='-Wl,-z,relro,-z,now' -Dman1dir=%{prefix}/share/man/man1 -Dman3dir=%{prefix}/share/man/man3
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
%check
make test
%files
%license Copying Artistic
%{prefix}/
