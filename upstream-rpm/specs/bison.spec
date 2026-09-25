Name: bison
Version: 3.8.2
Release: 4.linuxoss%{?dist}
Summary: GNU parser generator, upstream EL8 candidate
License: GPLv3+
URL: https://www.gnu.org/software/bison/
Source0: bison-3.8.2.tar.xz
Patch0: bison-CVE-2026-56389.patch
Patch1: bison-CVE-2026-56390-upstream.patch
BuildRequires: gcc, gcc-c++, make, m4, perl
BuildRequires: bison >= 3.8.2
Requires: m4
Vendor: Linux OSS local build
%description
GNU Bison parser generator with its upstream language and parser tests.
%prep
%setup -q
patch --fuzz=0 -p1 < %{PATCH0}
# The upstream commit contains generated files from an unreleased snapshot.
# Apply its exact grammar-source change and regenerate using release 3.8.2.
python3.11 - %{PATCH1} > output-paths-grammar.patch <<'PY'
import pathlib,sys
patch=pathlib.Path(sys.argv[1]).read_text()
parts=patch.split('diff --git ')
matching=[part for part in parts[1:] if part.startswith('a/src/parse-gram.y b/src/parse-gram.y\n')]
assert len(matching)==1
print('diff --git '+matching[0].split('\n-- \n')[0])
PY
patch --fuzz=0 -p1 < output-paths-grammar.patch
%build
# Release tarballs can skip maintainer regeneration. Generate explicitly so
# the grammar security patch is certainly in the compiled C parser.
/usr/bin/bison --defines -Werror -Wall,dangling-alias --report=all --no-lines \
  -o src/parse-gram.c src/parse-gram.y
grep -q valid_output_file_name src/parse-gram.c
export CFLAGS='-O2 -g -gdwarf-4 -fstack-protector-strong -fcf-protection -D_FORTIFY_SOURCE=2'
export CXXFLAGS="$CFLAGS"
export LDFLAGS='-Wl,--build-id -Wl,-z,relro,-z,now'
./configure --prefix=/usr --libdir=/usr/lib64
make %{?_smp_mflags}
%install
make DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_infodir}/dir
# EL8 byacc owns the generic yacc entry point and its manual. Keep Bison's
# own binary and liby.a; Bison's yacc-compatible mode remains `bison -y`.
rm -f %{buildroot}%{_bindir}/yacc %{buildroot}%{_mandir}/man1/yacc.1*
%check
make %{?_smp_mflags} check
%files
%license COPYING
%doc NEWS README
%{_bindir}/bison
%{_libdir}/liby.a
%{_datadir}/bison/
%{_datadir}/aclocal/bison-i18n.m4
%{_datadir}/locale/*/LC_MESSAGES/bison*.mo
%{_docdir}/bison/
%{_mandir}/man1/bison.1*
%{_infodir}/bison.info*
