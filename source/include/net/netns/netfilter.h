/* SPDX-License-Identifier: GPL-2.0 */
#ifndef __NETNS_NETFILTER_H
#define __NETNS_NETFILTER_H

#include <linux/netfilter_defs.h>
#include <linux/android_kabi.h>

struct proc_dir_entry;
struct nf_logger;
struct nf_queue_handler;

#ifdef CONFIG_NETFILTER_FAMILY_BRIDGE
/*
 * Bridge hooks live outside struct netns_nf so its layout (and the genksyms
 * CRCs of the symbols reaching it) stays identical to the stock kernel.
 */
struct netns_nf_additional_info {
	struct nf_hook_entries __rcu *hooks_bridge[NF_INET_NUMHOOKS];
};
#endif

struct netns_nf {
#if defined CONFIG_PROC_FS
	struct proc_dir_entry *proc_netfilter;
#endif
	const struct nf_queue_handler __rcu *queue_handler;
	const struct nf_logger __rcu *nf_loggers[NFPROTO_NUMPROTO];
#ifdef CONFIG_SYSCTL
	struct ctl_table_header *nf_log_dir_header;
#endif
	struct nf_hook_entries __rcu *hooks_ipv4[NF_INET_NUMHOOKS];
	struct nf_hook_entries __rcu *hooks_ipv6[NF_INET_NUMHOOKS];
#ifdef CONFIG_NETFILTER_FAMILY_ARP
	struct nf_hook_entries __rcu *hooks_arp[NF_ARP_NUMHOOKS];
#endif
#if IS_ENABLED(CONFIG_NF_DEFRAG_IPV4)
	bool			defrag_ipv4;
#endif
#if IS_ENABLED(CONFIG_NF_DEFRAG_IPV6)
	bool			defrag_ipv6;
#endif

#if defined(CONFIG_NETFILTER_FAMILY_BRIDGE) && !defined(__GENKSYMS__)
	/*
	 * Reuse the old KABI reserve slot for a pointer to the per-net bridge
	 * hook array.  Size (248) and offset (240) stay unchanged; genksyms
	 * still sees the stock reserve field.
	 */
	union {
		struct netns_nf_additional_info *additional_info;
		ANDROID_KABI_RESERVE(1);
	};
#else
	ANDROID_KABI_RESERVE(1);
#endif
};
#endif
