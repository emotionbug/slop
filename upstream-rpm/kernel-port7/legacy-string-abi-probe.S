/* SPDX-License-Identifier: GPL-2.0-only */
/* Compile-only probe: exercise Kbuild's assembly-export DWARF declaration. */
#include <linux/export.h>
#include <linux/linkage.h>

SYM_FUNC_START(strncpy)
	ret
SYM_FUNC_END(strncpy)
EXPORT_SYMBOL(strncpy)
