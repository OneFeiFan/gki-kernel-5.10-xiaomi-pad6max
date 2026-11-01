#!/usr/bin/env python3
"""生成 Docker 全家桶配置映射表（5.10 适用性 + 当前值 + check-config 状态）。"""
import os
import re
import sys

HOME = os.path.expanduser("~")
KERNEL = os.path.join(HOME, "kernel-dev")
REF = os.path.join(HOME, "kernel-sources/refs/kernel-workshop-docker/patch/fulldocker/defconfig_append")
CFG = os.path.join(HOME, "kernel-sources/out-final/common/.config")
CHECK = os.path.join(HOME, "kernel-sources/docker-check-final.txt")
OUT = os.path.join(KERNEL, ".claude/plans/gki-docker/config-map.md")


def kconfig_symbols():
    syms = set()
    pat = re.compile(r"^\s*(?:menu)?config\s+([A-Za-z0-9_]+)")
    for root, dirs, files in os.walk(KERNEL):
        dirs[:] = [d for d in dirs if d not in (".git", "out")]
        for name in files:
            if not name.startswith("Kconfig"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        m = pat.match(line)
                        if m:
                            syms.add(m.group(1))
            except OSError:
                pass
    return syms


def parse_config(path):
    status = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r"(CONFIG_[A-Za-z0-9_]+)=(.*)", line)
            if m:
                status[m.group(1)[7:]] = m.group(2).strip()
                continue
            m = re.match(r"# (CONFIG_[A-Za-z0-9_]+) is not set", line)
            if m:
                status[m.group(1)[7:]] = "n"
    return status


def parse_check(path):
    result = {}
    section = "other"
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Generally Necessary" in line:
                section = "required"
            elif "Optional Features" in line:
                section = "optional"
            m = re.search(r"(CONFIG_[A-Za-z0-9_]+): (enabled|missing|disabled)", line)
            if m:
                result[m.group(1)[7:]] = (section, m.group(2))
    return result


def classify(name):
    groups = [
        ("cgroup", r"CGROUP|MEMCG|CFS_BANDWIDTH|BLK_CGROUP|CPUSETS|BLK_DEV_THROTTLING"),
        ("ipvs", r"^IP_VS|XT_MATCH_IPVS"),
        ("sctp", r"SCTP"),
        ("nftables", r"^NF_TABLES|^NFT_|NF_DUP|NF_FWD|NF_LOG|NF_TCP|^NF_NAT"),
        ("bridge", r"BRIDGE"),
        ("ipv6-nat", r"^IP6_NF"),
        ("netfilter-xt", r"NETFILTER|^IP_NF|XT_"),
        ("tunnel-virt", r"VXLAN|L2TP|MACVLAN|MACVTAP|IPVLAN|IPVTAP|VLAN_8021Q|GRE|FOU|MPLS|NSH|HSR|ILA|SEG6|RPL"),
        ("tc", r"NET_SCH|NET_CLS|NET_ACT|NET_EMATCH|^CLS_|PSAMPLE"),
        ("fs-block", r"BTRFS|CEPH|ZRAM|BLK_DEV|CHECKPOINT|FHANDLE|^KEYS|USERFAULTFD|DEVTMPFS|OVERLAY"),
    ]
    for group, pat in groups:
        if re.search(pat, name):
            return group
    return "other"


def main() -> int:
    syms = kconfig_symbols()
    cfg = parse_config(CFG)
    check = parse_check(CHECK)
    ref = []
    with open(REF, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r"CONFIG_([A-Za-z0-9_]+)=", line)
            if m:
                ref.append(m.group(1))
    ref = sorted(set(ref))

    missing_510 = [s for s in ref if s not in syms]
    rows = []
    for s in ref:
        cur = cfg.get(s, "n")
        docker = check.get(s, ("-", "not-checked"))
        rows.append((s, s in syms, cur, docker[0], docker[1], classify(s)))

    lines = []
    lines.append("# 参考项目配置 → 5.10 映射表\n")
    lines.append(f"生成时间：2026-10-25  \n参考配置总数：{len(ref)}  \n5.10 存在：{len(ref) - len(missing_510)}  \n5.10 不存在：{len(missing_510)}\n")
    lines.append("## 5.10 不存在的 8 项\n")
    lines.append("| 配置 | 说明 |")
    lines.append("|---|---|")
    notes = {
        "CGROUP_MISC": "5.10 无 misc 控制器，可忽略",
        "IPV6_IOAM6_LWTUNNEL": "5.10 无 IOAM6，非 Docker 必需",
        "IP_VS_TWOS": "5.10 IPVS 无 TWOS 调度器，可忽略",
        "NETFILTER_NETLINK_HOOK": "5.10 无 netlink hook，非必需",
        "NETFILTER_XTABLES_COMPAT": "5.10 无 32 位 xtables 兼容，64 位设备不需要",
        "NFT_REJECT_NETDEV": "5.10 nftables 无 netdev reject，非必需",
        "ZRAM_BACKEND_DEFLATE": "5.10 zram 用不同配置命名，非 Docker 相关",
        "ZRAM_BACKEND_ZSTD": "5.10 zram 用不同配置命名，非 Docker 相关",
    }
    for s in missing_510:
        lines.append(f"| `CONFIG_{s}` | {notes.get(s, '')} |")
    lines.append("")

    for group in ["cgroup", "nftables", "bridge", "ipv6-nat", "ipvs", "sctp", "netfilter-xt", "tunnel-virt", "tc", "fs-block", "other"]:
        grow = [r for r in rows if r[5] == group]
        if not grow:
            continue
        lines.append(f"## {group}\n")
        lines.append("| 配置 | 5.10 | 当前值 | Docker检查 | 建议 |")
        lines.append("|---|---|---|---|---|")
        for s, exists, cur, sec, res, _ in grow:
            if not exists:
                continue
            advice = ""
            if res == "missing":
                advice = "需开启"
            elif res == "enabled":
                advice = "已满足"
            elif cur != "n":
                advice = "已开(非Docker强制)"
            else:
                advice = "按需"
            lines.append(f"| `CONFIG_{s}` | Y | {cur} | {sec}/{res} | {advice} |")
        lines.append("")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    missing_required = sorted(s for s in ref if s in syms and check.get(s, ("-", ""))[1] == "missing" and check.get(s)[0] == "required")
    missing_optional = sorted(s for s in ref if s in syms and check.get(s, ("-", ""))[1] == "missing" and check.get(s)[0] == "optional")
    print(f"wrote {OUT}")
    print(f"ref={len(ref)} exists={len(ref)-len(missing_510)} missing510={len(missing_510)}")
    print(f"docker required missing ({len(missing_required)}): {', '.join(missing_required)}")
    print(f"docker optional missing ({len(missing_optional)}): {', '.join(missing_optional)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
