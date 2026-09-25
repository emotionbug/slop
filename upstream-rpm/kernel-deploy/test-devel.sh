#!/usr/bin/env bash
# Test only in a disposable EL8 container after installing the matching devel RPM.
set -Eeuo pipefail
[[ -f /run/.containerenv || -f /.dockerenv ]] || exit 2
kver=7.2.7-linuxoss+
work=$(mktemp -d /tmp/linuxoss-devel-test.XXXXXXXX)
cd "$work"
cat > kernel_api.c <<'EOF'
#include <linux/init.h>
#include <linux/module.h>
static int __init sample_init(void) { pr_info("linuxoss devel fixture\n"); return 0; }
static void __exit sample_exit(void) {}
module_init(sample_init);
module_exit(sample_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Build-only kernel-devel compatibility fixture");
EOF
printf '%s\n' 'obj-m := kernel_api.o' > Makefile
make -C "/lib/modules/$kver/build" M="$work" modules
modinfo ./kernel_api.ko
[[ $(modinfo -F vermagic ./kernel_api.ko) == "$kver "* ]]
echo KERNEL_DEVEL_EL8_EXTERNAL_MODULE_BUILD_PASSED
