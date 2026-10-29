#!/usr/bin/env python3
"""检查构建出的 .config 是否缺少必需项。

0001 关掉了 Common/build.sh 里严格的 defconfig 检查，所以每次构建后需要单独
验证生成的 .config。
"""
import sys

REQUIRED = [
    "CONFIG_SYSVIPC",
    "CONFIG_POSIX_MQUEUE",
    "CONFIG_CGROUPS",
    "CONFIG_MEMCG",
    "CONFIG_CGROUP_SCHED",
    "CONFIG_CGROUP_DEVICE",
    "CONFIG_CGROUP_FREEZER",
    "CONFIG_CGROUP_PIDS",
    "CONFIG_CGROUP_PERF",
    "CONFIG_CGROUP_NET_CLASSID",
    "CONFIG_CGROUP_NET_PRIO",
    "CONFIG_UTS_NS",
    "CONFIG_IPC_NS",
    "CONFIG_USER_NS",
    "CONFIG_PID_NS",
    "CONFIG_NET_NS",
    "CONFIG_CHECKPOINT_RESTORE",
    "CONFIG_UNIX_DIAG",
    "CONFIG_PACKET_DIAG",
    "CONFIG_NETLINK_DIAG",
    "CONFIG_FHANDLE",
    "CONFIG_SECCOMP",
    "CONFIG_SECCOMP_FILTER",
    "CONFIG_BLK_DEV_THROTTLING",
    "CONFIG_ZSMALLOC",
    "CONFIG_ZRAM",
    "CONFIG_NF_TABLES",
    "CONFIG_IP_VS",
    "CONFIG_IP_NF_NAT",
    "CONFIG_IP6_NF_NAT",
    "CONFIG_IP_SCTP",
    "CONFIG_BRIDGE",
    "CONFIG_NET_CLS_CGROUP",
    "CONFIG_BLK_DEV_LOOP",
    "CONFIG_NTSYNC",
    "CONFIG_MACVLAN",
    "CONFIG_IPVLAN",
    "CONFIG_VXLAN",
    "CONFIG_TUN",
    "CONFIG_VETH",
    "CONFIG_EXT4_FS",
    "CONFIG_BTRFS_FS",
    "CONFIG_FUSE_FS",
    "CONFIG_OVERLAY_FS",
    "CONFIG_CFS_BANDWIDTH",
]

FORBIDDEN = [
    "CONFIG_MODULE_SIG",
]


def load(path):
    opts = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("CONFIG_") and "=" in line:
                key, value = line.split("=", 1)
                opts[key] = value
    return opts


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "out-zram/common/.config"
    opts = load(path)
    missing = [k for k in REQUIRED if opts.get(k) != "y"]
    forbidden = [k for k in FORBIDDEN if opts.get(k) == "y"]
    if missing or forbidden:
        print("CONFIG FAIL: " + path)
        for key in missing:
            print("  missing: %s" % key)
        for key in forbidden:
            print("  must not be y: %s" % key)
        return 1
    print("CONFIG OK: %d required options, %s" % (len(REQUIRED), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
