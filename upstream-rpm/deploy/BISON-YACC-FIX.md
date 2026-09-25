# 20260925-4: Bison and byacc coexistence

The RPM transaction test found that Bison release 3 owned `/usr/bin/yacc` and
`/usr/share/man/man1/yacc.1.gz`, which are already owned by EL8 byacc. The
transaction stopped before package installation. This was an omission in the
custom Bison spec's file list.

Bison 3.8.2 release **4.linuxoss.el8** excludes only that generic wrapper and
manual from its installation staging directory and RPM. `/usr/bin/bison`, the
Bison documentation, skeletons and `/usr/lib64/liby.a` remain. `bison -y` provides
Bison's Yacc-compatible mode. The existing byacc executable and manual remain
owned by byacc, with no alternatives switch or package removal.

The upstream source and both pinned security patches are unchanged. The build
still regenerates the grammar parser with Bison 3.8.2 before compilation, keeping
the output/header path fix in the compiled code. Only one of the 77 installation
RPMs changes. This packaging fix itself is not a new vulnerability fix.

## Validation

The complete upstream check phase passed in the unprivileged, network-disabled
EL8 builder: 13 example tests passed; the main suite had 712 successful tests and
64 skips, with no failures. A disposable UBI 8.10 runtime used Rocky EL8 reference Bison
3.0.4-10.el8 and byacc 1.9.20170709-4.el8, obtained with signature verification,
because those tools are absent from the UBI repositories. These reference packages
match the relevant EL8 version/file contract; they are not the target server's
exact Red Hat binary artifacts and are not included in the install kit.

The old custom Bison RPM reproduced both reported file conflicts. With release 4,
the applicable installer transaction completed 41 upgrades and two required
dependency installations, and DNF check passed.
byacc's executable/manual hashes and file ownership were unchanged. Both
`bison -y` and `yacc` generated parser output, and `liby.a` remained present.

The installed new Bison also passed the three benign security regression checks:
grammar-controlled external program execution, output path traversal and header
path traversal. The two named CVE assessments were re-reviewed against the
unchanged patches and tested new RPM. Native Trivy retains the old artifact and
adds the exact new RPM/header/payload hashes; a new catalogue and WASM module are
distributed. The advisory feed is unchanged; no new feed refresh or claim of
complete vulnerability coverage is implied.

The offline Trivy 0.74.0 run identified the new Bison release and matched its two
named patched CVEs to the new RPM/payload hashes. No artifact/payload mismatch
assessments occurred. The fixture reported 43 custom packages, 19 matched fixed
evidence rows, 390 under-investigation rows and 43 coverage/payload gaps. These
counts describe the container, not the target server or zero remaining CVEs.

Actual target-server installation, Java/Tomcat operation and post-installation
vulnerability counts remain separate from the container validation.

## Distribution

- [Installer and Bison RPM/SRPM](https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-4)
- [Earlier symbol policy correction](SYMBOL-POLICY-FIX.md)
- [Earlier legacy executable-path correction](LEGACY-PATH-FIX.md)

There is no force/replacefiles/skip-broken option, automatic package removal,
automatic JVM restart or automatic reboot in this correction.
