// SPDX-License-Identifier: GPL-2.0-only
/* Lab compatibility provider. Does not establish vendor module compatibility. */
#include <linux/export.h>
#include <linux/types.h>

char *strncpy(char *dest, const char *src, size_t count);

/* Keep the legacy API's exact semantics, including non-terminated truncation.
 * Its caller must supply a writable destination of at least count bytes.
 * Substituting strscpy would change the return value and padding/truncation.
 */
char *strncpy(char *dest, const char *src, size_t count)
{
	size_t pos = 0;

	while (pos < count) {
		char value = src[pos];

		dest[pos++] = value;
		if (!value)
			break;
	}
	while (pos < count)
		dest[pos++] = '\0';
	return dest;
}
EXPORT_SYMBOL(strncpy);
