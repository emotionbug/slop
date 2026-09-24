Name: perl-DBI
Version: 1.653
Release: 1.linuxoss%{?dist}
Summary: perl-DBI upstream EL8 evaluation build
License: GPL+ or Artistic
URL: https://metacpan.org/dist/DBI
Source0: DBI-1.653.tgz
BuildRequires: gcc, make, perl-devel, perl-ExtUtils-MakeMaker, perl-Test-Simple
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%prep
%setup -q -n DBI-1.653
%build
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='-D_FORTIFY_SOURCE=2'
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'

perl Makefile.PL INSTALLDIRS=vendor CC=/usr/bin/gcc
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} pure_install
find %{buildroot} -name '.packlist' -delete
find %{buildroot} -name '*.bs' -empty -delete
%check
make test
%files
%license LICENSE
/usr/lib64/perl5/vendor_perl/*
/usr/share/man/man3/*
/usr/share/man/man1/*
/usr/bin/*
