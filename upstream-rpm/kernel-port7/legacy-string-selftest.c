// SPDX-License-Identifier: GPL-2.0-only
/* Runs in an isolated 7.2.7 VM, not on the operating server. */
#include <linux/init.h>
#include <linux/mm.h>
#include <linux/module.h>
#include <linux/string.h>
#include <linux/vmalloc.h>

extern char *strncpy(char *dest, const char *src, size_t count);

static int __init legacy_string_init(void)
{
	char dst[32];
	char *page;
	int failed = 0;
	size_t i;

	/* Exact bounds, padding, truncation, empty input, return pointer. */
	memset(dst, 0x5a, sizeof(dst));
	failed |= strncpy(dst + 1, "ab", 8) != dst + 1;
	failed |= memcmp(dst + 1, "ab\0\0\0\0\0\0", 8) != 0;
	failed |= dst[0] != 0x5a || dst[9] != 0x5a;
	memset(dst, 0x5a, sizeof(dst));
	failed |= strncpy(dst + 1, "abcdef", 3) != dst + 1;
	failed |= memcmp(dst + 1, "abc", 3) != 0 || dst[4] != 0x5a;
	failed |= dst[0] != 0x5a;
	memset(dst, 0x5a, sizeof(dst));
	strncpy(dst + 1, "", 8);
	for (i = 1; i <= 8; i++)
		failed |= dst[i] != 0;
	failed |= dst[0] != 0x5a || dst[9] != 0x5a;

	/* vmalloc supplies a guard page after the mapping. A read beyond count,
	 * or a read after the first NUL, faults instead of hiding an overread.
	 */
	page = vmalloc(PAGE_SIZE);
	if (!page)
		return -ENOMEM;
	page[PAGE_SIZE - 2] = 'q';
	page[PAGE_SIZE - 1] = 'r';
	memset(dst, 0x5a, sizeof(dst));
	strncpy(dst + 1, page + PAGE_SIZE - 2, 2);
	failed |= dst[0] != 0x5a || dst[1] != 'q' || dst[2] != 'r' || dst[3] != 0x5a;
	page[PAGE_SIZE - 1] = '\0';
	memset(dst, 0x5a, sizeof(dst));
	strncpy(dst + 1, page + PAGE_SIZE - 2, 16);
	failed |= dst[0] != 0x5a || dst[1] != 'q' || dst[17] != 0x5a;
	for (i = 2; i <= 16; i++)
		failed |= dst[i] != 0;
	/* With zero count neither pointer should be dereferenced. */
	failed |= strncpy(dst, page + PAGE_SIZE, 0) != dst;
	failed |= dst[0] != 0x5a;
	vfree(page);
	if (failed) {
		pr_err("PORTLAB7_LEGACY_STRING_SELFTEST_FAILED\n");
		return -EINVAL;
	}
	pr_info("PORTLAB7_LEGACY_STRING_SELFTEST_PASSED\n");
	return 0;
}

static void __exit legacy_string_exit(void) {}
module_init(legacy_string_init);
module_exit(legacy_string_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("7.2.7 laboratory legacy string API and boundary checks");
