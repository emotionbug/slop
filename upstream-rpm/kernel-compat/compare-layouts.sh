#!/bin/bash
set -euo pipefail
cd /lab
for name in ubuntu-7.0.0-31 linux-7.2.7; do
    mkdir -p "probe-$name" "results/$name"
    cp /input/upstream-rpm/kernel-compat/layout-probe.c "probe-$name/probe.c"
    printf 'obj-m := probe.o\nccflags-y += -g -fno-eliminate-unused-debug-types\n' > "probe-$name/Makefile"
    if [ "$name" = ubuntu-7.0.0-31 ]; then
        kernel=/lab/reference/usr/src/linux-headers-7.0.0-31-generic
    else
        kernel=/lab/source/linux-7.2.7
    fi
    make -C "$kernel" M="/lab/probe-$name" CC=gcc-15 HOSTCC=gcc-15 probe.o
    for type in sk_buff net_device sock socket net task_struct nf_hook_ops nf_hook_state nf_queue_entry proto proc_ops; do
        pahole -C "$type" "probe-$name/probe.o" > "results/$name/$type.layout.txt"
    done
    printf '%s\n' nf_register_net_hook nf_unregister_net_hook skb_copy skb_clone dev_queue_xmit proc_create_data init_net |
        /lab/source/linux-7.2.7/scripts/gendwarfksyms/gendwarfksyms -T "results/$name/apis.symtypes" "probe-$name/probe.o" > "results/$name/apis.crcs"
done
diff -u results/ubuntu-7.0.0-31/apis.crcs results/linux-7.2.7/apis.crcs > results/apis.diff || [ "$?" -eq 1 ]
printf 'Layout and API comparison completed; no module loaded.\n'
