#!/usr/bin/env bash
# Invoke in a disposable UBI 8 validation container with /packages read-only.
set -euo pipefail
[[ $(id -u) == 0 && $# -gt 0 ]] || exit 2
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
rpms=()
sed_baseline_user_xattr='not-tested'
for package in "$@"; do
  case "$package" in sed|diffutils|patch|gawk|bison|cpio|tar) ;; *) exit 2 ;; esac
  mapfile -t matches < <(find "/packages/$package" -maxdepth 1 -name "$package-[0-9]*.x86_64.rpm" -type f)
  [[ ${#matches[@]} == 1 ]] || exit 1
  rpms+=("${matches[0]}")
  rpm -q "$package" || echo "UBI_BASELINE_NOT_AVAILABLE:$package; validation is a fresh install"
  if [[ $package == sed ]]; then
    baseline=$(mktemp -d /tmp/sed-baseline.XXXXXX)
    echo old > "$baseline/file"
    setfattr -n user.linuxoss -v preserved "$baseline/file"
    sed -i s/old/new/ "$baseline/file"
    sed_baseline_user_xattr=$(getfattr --only-values -n user.linuxoss "$baseline/file" 2>/dev/null || true)
  fi
done
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False --setopt=install_weak_deps=False install "${rpms[@]}"
dnf --disableplugin=subscription-manager --disablerepo='*' check
work=$(mktemp -d /tmp/gnu-utility-validation.XXXXXX)
cd "$work"
for package in "$@"; do
  case "$package" in
    sed)
      [[ $(sed --version | head -1) == *4.10 ]]
      printf 'alpha 10\nbeta 20\n' > input
      printf 'alpha 11\nbeta 21\n' > expected
      sed -E 's/([0-9])0/\11/' input > actual
      cmp expected actual
      cp input target; chmod 0640 target; ln -s target link
      setfacl -m u:12345:r target
      setfattr -n user.linuxoss -v preserved target
      sed -i --follow-symlinks 's/alpha/changed/' link
      [[ -L link && $(stat -c %a target) == 640 ]]
      grep -q '^changed 10$' target
      getfacl -cp target | grep -q '^user:12345:r--$'
      user_xattr=$(getfattr --only-values -n user.linuxoss target 2>/dev/null || true)
      [[ $user_xattr == "$sed_baseline_user_xattr" ]]
      # GNU sed's in-place replacement removes user.* attributes in both the
      # UBI baseline and new build. Record it instead of claiming preservation.
      printf 'SED_USER_XATTR_BASELINE_AND_NEW=%s\n' "${user_xattr:-removed}"
      echo UBI_SED_FUNCTIONAL_ACL_SYMLINK_OK
      ;;
    diffutils)
      [[ $(diff --version | head -1) == *3.12 ]]
      printf 'one\ntwo\n' > old; printf 'one\nthree\n' > new
      cmp old old; diff old old
      set +e
      diff -u --label a/file --label b/file old new > change.diff; status=$?
      set -e
      [[ $status == 1 ]]
      grep -q '^-two$' change.diff; grep -q '^+three$' change.diff
      diff3 -m old old new > merged; cmp new merged
      python3 /recipe/validate-diffutils-cve.py /usr/bin/diff3
      echo UBI_DIFFUTILS_STATUS_AND_MERGE_OK
      ;;
    patch)
      [[ $(patch --version | head -1) == *2.8 ]]
      mkdir -p patchtest; printf 'old\n' > patchtest/file
      printf '%s\n' '--- a/file' '+++ b/file' '@@ -1 +1 @@' '-old' '+new' > update.patch
      patch --dry-run -d patchtest -p1 < update.patch
      patch -d patchtest -p1 < update.patch
      grep -qx new patchtest/file
      patch -R -d patchtest -p1 < update.patch
      grep -qx old patchtest/file
      echo UBI_PATCH_APPLY_REVERSE_OK
      ;;
    gawk)
      [[ $(gawk --version | head -1) == *5.4.1* ]]
      [[ $(printf 'a,3\nb,7\n' | gawk -F, '{s+=$2} END{print s}') == 10 ]]
      [[ $(gawk -M 'BEGIN{printf "%.0f\n",2^100}') == 1267650600228229401496703205376 ]]
      [[ $(gawk 'BEGIN{a[2]="z";a[1]="a";n=asort(a);print n,a[1],a[2]}') == '2 a z' ]]
      gawk -l filefuncs 'BEGIN{if(stat(".",s)!=0 || s["type"]!="directory")exit 1}'
      echo UBI_GAWK_BIGNUM_ARRAY_EXTENSION_OK
      ;;
    bison)
      [[ $(bison --version | head -1) == *3.8.2 ]]
      cat > parser.y <<'PARSER'
%{
#include <stdio.h>
int yylex(void); void yyerror(const char *s);
%}
%token NUM
%%
start: NUM '+' NUM { if ($1+$3!=42) YYABORT; };
%%
int yylex(void) { static int i; const int t[]={NUM,'+',NUM,0};
  int r=t[i++];if(r==NUM)yylval=21;return r; }
void yyerror(const char *s){fprintf(stderr,"%s\n",s);}
int main(void){return yyparse();}
PARSER
      bison -Wall -Werror -o parser.c parser.y
      gcc -O2 parser.c -o parser; ./parser
      echo UBI_BISON_GENERATED_PARSER_OK
      ;;
    cpio|tar)
      mkdir -p "$package-input" "$package-out"
      printf 'archive content\n' > "$package-input/file"
      ln "$package-input/file" "$package-input/hard"
      ln -s file "$package-input/link"
      if [[ $package == tar ]]; then
        chmod 0640 tar-input/file
        setfacl -m u:12345:r tar-input/file
        setfattr -n user.linuxoss -v preserved tar-input/file
      fi
      if [[ $package == cpio ]]; then
        (cd cpio-input && printf '%s\n' file hard link | cpio -o -H newc) > archive.cpio
        (cd cpio-out && cpio -idm --no-absolute-filenames < ../archive.cpio)
      else
        tar --acls --xattrs -cf archive.tar -C tar-input .
        tar --acls --xattrs -xf archive.tar -C tar-out
      fi
      cmp "$package-input/file" "$package-out/file"
      [[ $(readlink "$package-out/link") == file ]]
      [[ $(stat -c %i "$package-out/file") == $(stat -c %i "$package-out/hard") ]]
      if [[ $package == tar ]]; then
        [[ $(stat -c %a tar-out/file) == 640 ]]
        [[ $(getfattr --only-values -n user.linuxoss tar-out/file) == preserved ]]
        getfacl -cp tar-out/file | grep -q '^user:12345:r--$'
        echo UBI_TAR_ACL_XATTR_MODE_OK
      fi
      echo "UBI_${package^^}_ARCHIVE_LINK_ROUNDTRIP_OK"
      ;;
  esac
done
dnf --disableplugin=subscription-manager --disablerepo='*' check
echo UBI_SELECTED_GNU_UTILITY_CANDIDATES_OK
