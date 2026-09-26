// SPDX-License-Identifier: GPL-2.0-only
/* Execute the unmodified extracted reparse_buf_ptr() with guard-page inputs.
 * The small type/trace shims below do not emulate the SMB transport or kernel.
 */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
struct smb2_ioctl_rsp { u32 OutputOffset, OutputCount; };
struct reparse_data_buffer { u32 ReparseTag; u16 ReparseDataLength, Reserved; };
struct kvec { void *iov_base; size_t iov_len; };
#define le32_to_cpu(v) (v)
#define le16_to_cpu(v) (v)
#define check_add_overflow(a, b, p) __builtin_add_overflow((a), (b), (p))
#define ERR_PTR(v) ((void *)(intptr_t)(v))
#define smb_EIO2(trace, a, b) (-EIO)
#include "smb-reparse-extracted.h"

static void exercise(unsigned int count, unsigned int payload, int expected_error)
{
	size_t page = (size_t)sysconf(_SC_PAGESIZE);
	char *area = mmap(NULL, 2 * page, PROT_READ | PROT_WRITE,
			 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	assert(area != MAP_FAILED);
	assert(mprotect(area + page, page, PROT_NONE) == 0);
	struct smb2_ioctl_rsp *io = (void *)area;
	io->OutputOffset = page - count;
	io->OutputCount = count;
	if (count >= sizeof(struct reparse_data_buffer)) {
		struct reparse_data_buffer *buf = (void *)(area + page - count);
		buf->ReparseDataLength = payload;
	}
	struct kvec iov = {area, page};
	struct reparse_data_buffer *got = reparse_buf_ptr(&iov);
	if (expected_error)
		assert(got == ERR_PTR(-EIO));
	else
		assert((char *)got == area + page - count);
	munmap(area, 2 * page);
}

int main(void)
{
#ifdef NEGATIVE_CONTROL
	pid_t child = fork();
	assert(child >= 0);
	/* Five available bytes place the second byte of ReparseDataLength in
	 * the guard page. The vulnerable ordering reads it before count >= 8.
	 */
	if (child == 0) { exercise(5, 0, 1); _exit(0); }
	int status;
	assert(waitpid(child, &status, 0) == child);
	assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGSEGV);
	puts("SMB_REPARSE_VULNERABLE_CONTROL_FAULT_CONFIRMED");
#else
	for (unsigned int n = 0; n < 8; n++)
		exercise(n, 0, 1);
	exercise(8, 0, 0);
	exercise(8, 1, 1);
	exercise(16, 8, 0);
	exercise(16, 9, 1);
	exercise(16, UINT16_MAX, 1);
	struct smb2_ioctl_rsp io = {UINT32_MAX - 3, 8};
	struct kvec iov = {&io, sizeof(io)};
	assert(reparse_buf_ptr(&iov) == ERR_PTR(-EIO));
	io.OutputOffset = 0;
	io.OutputCount = sizeof(io) + 1;
	assert(reparse_buf_ptr(&iov) == ERR_PTR(-EIO));
	puts("CVE_2026_89632_EXACT_SOURCE_BOUNDARIES_PASSED");
#endif
	return 0;
}
