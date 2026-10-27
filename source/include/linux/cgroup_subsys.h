/* SPDX-License-Identifier: GPL-2.0 */
/*
 * List of cgroup subsystems.
 *
 * DO NOT ADD ANY SUBSYSTEM WITHOUT EXPLICIT ACKS FROM CGROUP MAINTAINERS.
 */

/*
 * This file *must* be included with SUBSYS() defined.
 */

#if IS_ENABLED(CONFIG_CPUSETS)
SUBSYS(cpuset)
#endif

#if IS_ENABLED(CONFIG_CGROUP_SCHED)
SUBSYS(cpu)
#endif

#if IS_ENABLED(CONFIG_CGROUP_CPUACCT)
SUBSYS(cpuacct)
#endif

#if IS_ENABLED(CONFIG_BLK_CGROUP)
SUBSYS(io)
#endif

#if IS_ENABLED(CONFIG_MEMCG)
SUBSYS(memory)
#endif

#if IS_ENABLED(CONFIG_CGROUP_FREEZER)
SUBSYS(freezer)
#endif

#if IS_ENABLED(CONFIG_CGROUP_NET_PRIO)
SUBSYS(net_prio)
#endif

#if IS_ENABLED(CONFIG_CGROUP_HUGETLB)
SUBSYS(hugetlb)
#endif

#if IS_ENABLED(CONFIG_CGROUP_RDMA)
SUBSYS(rdma)
#endif

/*
 * The following subsystems are not supported on the default hierarchy.
 */
#if IS_ENABLED(CONFIG_CGROUP_DEBUG)
SUBSYS(debug)
#endif

/*
 * Controllers added after the 5.10 KMI are kept at the end so that their
 * subsystem ids are >= CGROUP_SUBSYS_MAIN_COUNT; their state lives in the
 * ext structures instead of struct css_set / struct cgroup.
 * CONFIG_CGROUP_DEBUG must stay disabled: it would shift this boundary.
 *
 * genksyms must not see these entries: they would change the
 * enum cgroup_subsys_id members and CGROUP_SUBSYS_COUNT, which genksyms
 * folds into the CRCs of symbols touching struct css_set / struct cgroup.
 */
#if IS_ENABLED(CONFIG_CGROUP_DEVICE) && !defined(__GENKSYMS__)
SUBSYS(devices)
#endif

#if IS_ENABLED(CONFIG_CGROUP_PIDS) && !defined(__GENKSYMS__)
SUBSYS(pids)
#endif

/*
 * perf_event keeps the stock KMI: its cgrp pointer is split across two u32
 * fields placed in stock layout holes in include/linux/perf_event.h, and
 * those fields are hidden from genksyms.
 */
#if IS_ENABLED(CONFIG_CGROUP_PERF) && !defined(__GENKSYMS__)
SUBSYS(perf_event)
#endif

#if IS_ENABLED(CONFIG_CGROUP_NET_CLASSID) && !defined(__GENKSYMS__)
SUBSYS(net_cls)
#endif

/*
 * DO NOT ADD ANY SUBSYSTEM WITHOUT EXPLICIT ACKS FROM CGROUP MAINTAINERS.
 */
