# Security agents and the upstream kernel

Investigated 2026-09-26. This document does not authorize or perform an agent,
firewall, bootloader, or kernel change. The existing installer still rejects
unassessed external modules before the RPM transaction.

## What the stop means

`Active external modules need a 7.2.7 rebuild` is a conservative preflight stop,
not the result of an attempted module build or a completed ABI comparison.
It means vendor-supported modules or a source port and runtime validation are
needed before deploying this upstream kernel. Installing kernel-devel alone
does not supply proprietary driver sources.

- `gc_enforcement`: Guardicore enforcement. A `weak-updates` link can reuse a
  module across compatible RHEL kernel updates; this does not establish
  compatibility with Linux 7.2. A GPL field is a useful source-request lead,
  but does not prove that the matching build source is locally present.
- `dsa_filter` and `dsa_filter_hook`: Deep Security network protection drivers.
  `modinfo <name>` can fail even while the module is loaded. Trend Micro documents
  files under `/opt/ds_agent/<kernel>/`; inspect files by path before concluding
  that the agent or its drivers were removed.

## Available routes and limits

1. **Vendor-supported EL8 security update:** select a matching kernel/KSP/agent
   combination and validate Guardicore module compatibility. The Trend Micro
   public table currently includes `4.18.0-553.168.1.el8_10.x86_64`. This is a
   candidate, not proof that an installed agent already has that KSP or that
   Guardicore supports it. Obtain RHEL RPMs from authorized Red Hat or internal
   channels. Rocky/Alma RPMs are different vendor packages, even at the same EVR.
2. **Keep Linux 7.2.7:** obtain matching driver sources/build instructions or
   explicit vendor support. No matching public enforcement-driver source was
   found in this investigation. Trend Micro explicitly excludes customized
   kernels from its normal KSP support scope. Upgrading the agent is not evidence
   that this restriction is removed. A GPL tag on Guardicore alone cannot solve
   the separate Deep Security driver dependency.
3. **Move protection outside the guest:** Deep Security Virtual Appliance has
   VMware NSX integration for network protection. This requires VMware/security
   administrators, suitable infrastructure/licensing, and policy migration plus
   actual traffic validation. It is not an SSH-only host command and does not
   automatically replace Guardicore policy enforcement.

Changing vermagic, forcing module loading, copying old weak-updates links to a
new upstream kernel, or merely masking agent services does not establish ABI
or policy compatibility. No such workaround is implemented here.

## One read-only collection

Run the standalone script with RHEL 8's existing platform-python. It writes JSON
only to stdout, queries installed package/module metadata, locates selected
driver files and potential source filenames, and reads imported symbol CRCs.
It makes no network requests, performs no package changes, and never invokes
agent control commands or loads/unloads modules. Do not publish the report to
the public repository; keep it with private server evidence.

```bash
sudo /usr/libexec/platform-python inspect-security-kmods.py > security-kmods.json
```

Optional absolute product directories may be appended if the installation is
outside the discovered paths. The JSON reports search errors/truncation, loaded
module srcversion versus disk srcversion when available, and explicit query
failures. It does not dump keys, agent policies, general configs, or log contents.
Source names are not proof of complete usable sources. Matching imported CRCs
are a prerequisite for reuse, not a runtime or vendor-support guarantee.

## Sources

- [Deep Security kernel scope and KSP behavior](https://help.deepsecurity.trendmicro.com/20_0/on-premise/agent-linux-kernel-support.html)
- [Current supported kernel list](https://files.trendmicro.com/documentation/guides/deep_security/Kernel%20Support/20.0/Deep_Security_20_0_kernels_EN.html)
- [Deep Security driver functions](https://success.trendmicro.com/en-US/solution/KA-0013040)
- [Trend Micro driver file locations](https://success.trendmicro.com/en-US/solution/KA-0013751)
- [Deep Security Virtual Appliance and NSX](https://help.deepsecurity.trendmicro.com/20_0/on-premise/release-notes-dsva.html)
- [Guardicore module identification](https://access.redhat.com/solutions/7074175)
- [Reported panic on unloading gc_enforcement](https://access.redhat.com/solutions/6977610)

No vendor request has been submitted, no commercial agent files have been
redistributed, and no actual-server kernel/agent compatibility test has run.

## Collector validation

The collector ran using EL8 platform-python 3.6 in an isolated container with
network disabled and a read-only root filesystem. JSON parsing passed. Two
focused tests passed: a loaded driver missing from the modinfo name index but
discoverable by file path (including symlink deduplication and symbol metadata),
and a missing query tool reported without aborting collection. Fixture driver
data was mocked; this is collector validation, not an agent compatibility test.
