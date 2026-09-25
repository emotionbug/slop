# 20260925-3: interpret symbol findings in the planned transaction

The version-2 installer treated every occurrence of a removed symbol name as a
blocking ABI dependency. This blocked unrelated `strlcpy`/`strlcat` consumers that
have their own unchanged direct dependency providing those symbols. It also blocked
an old CUPS library that is itself retired by the same `cups-libs` upgrade.

This release changes the installer and its audit interpretation. All 77 RPMs and
the native Trivy module, catalogue and advisory data are byte-identical to version 2.
No vulnerability status or CVE evidence is newly marked fixed by this change.

## What the installer now checks

- Retain raw `symbol-audit.json`. Record every discovered alias of matched inodes,
  including hard links, so a surviving file is not hidden by inode deduplication.
- Include libraries from outgoing RPM file lists when selecting export removals.
  A removed library must still have its remaining consumers checked even if its
  path is absent from the incoming RPMs.
- Account for a retiring consumer only when all discovered resolved aliases are
  non-config, non-ghost files owned solely by outgoing RPMs and are absent from
  incoming file lists. A surviving/unowned hard link still blocks installation.
- For the reviewed unversioned `strlcpy`/`strlcat` removals from `libmagic.so.1`,
  require a matching strong, visible export in an unambiguous, same-architecture,
  RPM-owned direct DT_NEEDED dependency that is unchanged by this transaction.
  Versioned imports, COPY relocations, consumer RPATH/RUNPATH, loader environment
  overrides, active ld.so.preload entries, ambiguous paths and changed providers
  do not qualify. Other symbol-name matches continue to block.
- Keep pre-existing dangling symlinks as warnings after confirming that the link
  still exists and its target does not. They have no existing target ELF to inspect.
  The link is not deleted/repaired and the associated component is not declared
  healthy. Permission failures, missing ordinary paths and readelf errors block.
- Add an existing `/usr/src` directory to the scan so kernel build/source links
  are covered. Other directory targets outside declared roots still block.

Decisions and supporting paths/providers appear in `symbol-audit-policy.json`.
This is static ELF evidence, not execution-time loader tracing or proof about
running/deleted mappings, dlopen, JNI, environment-dependent loading, future plugins
or paths outside the declared roots. Restart and application checks remain the
operator's responsibility; the installer performs no automatic reboot/JVM restart.

## Validation

19 ELF audit/diagnostic/policy tests passed on EL8 Python 3.6. They cover an unchanged
direct provider, a provider replaced by the transaction, a missing provider,
versioned imports, loader environment overrides, unknown provider removals, retiring
consumers, surviving hard links, dangling links and uncovered/unreadable paths.

A disposable UBI 8.10 container installed Red Hat `cups-libs-2.2.6-68.el8_10` and
its avahi dependency. An external ELF fixture importing the retired `cgiGetSize`
export was detected and blocked before RPM changes; the package inventory was
unchanged. The old CUPS-internal consumer was separately accounted for, and a
kernel-source-style link was covered by the added source root.

After removing only that disposable external test fixture, the installer completed
40 upgrades plus two hard dependency installations. The retired `libcupscgi.so.1`
was absent, the new `libcups.so.2` loaded, the deliberately dangling link remained,
DNF check passed, and the legacy `/bin/sed`, `/bin/awk`, `/bin/tar` dependency fixture
remained installed. These are container results, not target-server installation or
Java/Tomcat runtime results. The Trivy scan was not repeated because its inputs and
all RPMs were unchanged; target results still require a post-installation scan.

## Distribution

- [Installer v3](https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-3)
- [Unchanged v2 RPM/source updates](https://github.com/emotionbug/slop/releases/tag/linuxoss-install-20260925-2)
- [Original candidate RPM/SRPM release](https://github.com/emotionbug/slop/releases/tag/upstream-rpm-candidates-20260924-7)

Server-specific audits, paths, identities and configuration are not distributed.
