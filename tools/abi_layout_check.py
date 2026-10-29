#!/usr/bin/env python3
"""检查关键结构体的大小和偏移是否与 5.10.272 GKI 原厂布局一致。

期望值来自 AOSP GKI 5.10.272 基线（out-final）。cfs_rq 保留原厂
android_vendor_data1 的偏移 344，CFS 带宽指针放在尾部填充的 472，因此不需要
布局例外；ipc_ids 和 netns_ipv4 也必须保持原厂布局。
"""
import re
import subprocess
import sys

EXPECTED = {
    "ipc_ids": {"size": 272, "fields": {"key_ht": 104}},
    "netns_ipv4": {"size": 960, "fields": {"tcp_death_row": 640}},
    "cfs_rq": {
        "size": 512,
        "fields": {"cfs_bandwidth": 472, "android_vendor_data1": 344},
    },
    "task_group": {"size": 448, "fields": {}},
}


def struct_sizes(vmlinux):
    out = subprocess.run(["pahole", "-s", vmlinux],
                         capture_output=True, text=True, check=True).stdout
    sizes = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 2 or parts[0] not in EXPECTED:
            continue
        try:
            sizes.setdefault(parts[0], int(parts[1]))
        except ValueError:
            pass
    return sizes


def struct_fields(vmlinux, name):
    out = subprocess.run(["pahole", "-C", name, vmlinux],
                         capture_output=True, text=True, check=True).stdout
    fields = {}
    for line in out.splitlines():
        match = re.search(
            r"\b([A-Za-z_]\w*)(?:\[[^\]]*\])?;\s*/\*\s*(\d+)\s+(\d+)\s*\*/",
            line)
        if match:
            fields.setdefault(match.group(1), int(match.group(2)))
    return fields


def main():
    vmlinux = sys.argv[1] if len(sys.argv) > 1 else "out-zram/dist/vmlinux"
    sizes = struct_sizes(vmlinux)
    failures = []
    for name, expected in EXPECTED.items():
        size = sizes.get(name)
        if size != expected["size"]:
            failures.append("%s: size %s != %d" %
                            (name, size, expected["size"]))
        fields = struct_fields(vmlinux, name)
        for field, offset in expected["fields"].items():
            got = fields.get(field)
            if got != offset:
                failures.append("%s.%s: offset %s != %d" %
                                (name, field, got, offset))
    if failures:
        print("LAYOUT FAIL: " + vmlinux)
        for item in failures:
            print("  " + item)
        return 1
    print("LAYOUT OK: " + vmlinux)
    print("  cfs_rq matches stock; CFS pointer at 472 in the tail padding")
    return 0


if __name__ == "__main__":
    sys.exit(main())
