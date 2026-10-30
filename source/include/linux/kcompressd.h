/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_KCOMPRESSD_H
#define _LINUX_KCOMPRESSD_H

#include <linux/nodemask.h>
#include <linux/wait.h>
#include <linux/kfifo.h>
#include <linux/sched.h>

#define KCOMPRESS_FIFO_SIZE 256

/*
 * Kept out of struct pglist_data so the GKI layout and CRCs stay stock.
 * Indexed by node id, like node_data.
 */
struct kcompress_t {
	wait_queue_head_t kcompressd_wait;
	struct task_struct *kcompressd;
	struct kfifo kcompress_fifo;
};

extern struct kcompress_t kcompress_data[MAX_NUMNODES];

int kcompressd(void *p);

#endif /* _LINUX_KCOMPRESSD_H */
