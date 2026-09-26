#!/bin/bash
set -euo pipefail
cd /lab
mkdir -p reference source results
dpkg-deb -x /input/.validation/trendmicro-ksp-20260926/linux-headers-7.0.0-31_7.0.0-31.31_all.deb reference
dpkg-deb -x /input/.validation/trendmicro-ksp-20260926/linux-headers-7.0.0-31-generic_7.0.0-31.31_amd64.deb reference
if [ ! -f source/linux-7.2.7/Makefile ]; then
    tar -xJf /input/upstream-rpm/sources/linux-7.2.7.tar.xz -C source
fi
cp /input/.validation/trendmicro-ksp-20260926/ubuntu31-data/config source/linux-7.2.7/.config
cd source/linux-7.2.7
scripts/config --disable RUST --set-str SYSTEM_TRUSTED_KEYS '' --set-str SYSTEM_REVOCATION_KEYS ''
make CC=gcc-15 HOSTCC=gcc-15 olddefconfig
make -j6 CC=gcc-15 HOSTCC=gcc-15 modules_prepare
cp .config /lab/results/linux-7.2.7-ubuntu-config
printf 'Prepared sources and reference headers.\n'
