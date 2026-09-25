# 20260925-2: EL8 legacy executable-path dependencies

The first installer stopped before changing packages because an installed
`os-prober` required `/bin/sed`. Our sed RPM owned `/usr/bin/sed` but omitted the
original EL8 `Provides: /bin/sed`. Although `/bin` points to `/usr/bin` on EL8,
RPM resolves the declared file capability by its exact path. This was a packaging
omission, not a reason to remove os-prober or bypass dependencies.

[RPM dependency documentation](https://rpm.org/docs/4.19.x/manual/dependencies.html)
explains explicit file-path Provides.

The same audit found related omissions in four other source packages. The corrected
77-RPM set replaces these six binary RPMs; all other binary RPM hashes remain unchanged:

| RPM | New release | Restored capability |
|---|---|---|
| sed 4.10 | 2.linuxoss.el8 | `/bin/sed` |
| coreutils 9.12 | 2.linuxoss.el8 | 31 original `/bin/*` aliases, including `/bin/chmod` |
| coreutils-common 9.12 | 2.linuxoss.el8 | Version-aligned companion of coreutils |
| gawk 5.4.1 | 2.linuxoss.el8 | `/bin/awk`, `/bin/gawk` |
| cpio 2.15 | 3.linuxoss.el8 | `/bin/cpio` |
| tar 1.35 | 3.linuxoss.el8 | `/bin/tar`, `/bin/gtar`; adds `/usr/bin/gtar -> tar` |

Programs continue to reside under `/usr`. Upstream source and existing security
patches are unchanged and hash-pinned in `sources.lock.json`. These are rebuilt RPMs,
so RPM/header/payload hashes are recorded anew; binary identity is not claimed.
This packaging change itself is not a new CVE fix.

## Validation

- Original package-provided path capabilities were compared against all 77 final RPM
  headers/file lists: no missing original explicit path capabilities remained.
- A disposable UBI 8.10 fixture requires `/bin/sed`, `/bin/chmod`, `/bin/awk`,
  `/bin/gawk`, `/bin/cpio`, `/bin/tar`, and `/bin/gtar`. The old sed reproduces the
  exact path-dependency failure. The updated installer keeps that consumer installed
  and completes 38 upgrades plus 2 hard-dependency additions. This checks os-prober's
  dependency contract; it does not run bootloader discovery or modify a bootloader.
- DNF check, provider queries, sed editing/symlink/mode handling, gawk MPFR and extension
  execution, and tar content/symlink round-trip passed after installation.
- The new cpio binary passed the existing bounded hardlink-escape, terminal-escape,
  and long-path-stack regression inputs. Only those named CVEs retain fixed evidence.
- sed upstream suites: 58/75 and 225/287 pass, the rest skipped, no failures.
- coreutils suites: 583/761 and 486/603 pass, the rest skipped, no failures.
- gawk: upstream `ALL TESTS PASSED`; cpio: all 17 tests successful.
- tar: 223 successful, 26 skipped, no failures on tmpfs. The first overlay-filesystem
  run failed timestamp-sensitive tests 129 and 192; final validation reran the full
  suite on tmpfs. gawk's initial locale/seccomp environment failures were resolved by
  installing locale data and allowing personality only within the unprivileged,
  network-disabled build container (seccomp was disabled for that test container).

The native Trivy catalogue retains original v3 artifacts and adds the six exact new
RPM/SRPM records. Existing named-CVE reviews were re-examined against the unchanged
pinned security sources and newly built/tested binaries; they are keyed to the new
RPM hashes. The Go fixtures now select one installed version per name/architecture
and separately verify that retained old/new artifact records match. Coverage gaps,
other CVEs, and the unresolved tar findings remain visible.

The offline Trivy integration run completed with 40 installed custom RPMs, including
all six rebuilt RPMs. No artifact-mismatch or payload-mismatch assessments occurred.
17 named fixed-evidence rows and 325 review CVE rows were reported; these are fixture
results, not target-server findings or proof of complete vulnerability coverage.

Actual target-server installation, Java/Tomcat runtime, boot and live-process reload
remain unverified. The installer still refuses unresolved dependencies, unmatched
removals and downgrades; it does not reboot or restart Java/Tomcat automatically.

[Corrected installation release](https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-2)
includes the installer, 77 RPMs and the refreshed Trivy integration. The separate
source bundle contains the five updated SRPMs, six binary RPMs and their manifest.
Unchanged source RPMs remain in the original candidate release.
