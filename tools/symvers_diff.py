#!/usr/bin/env python3
"""对比基线与新内核的 vmlinux.symvers。

基线里的每个符号都必须存在且 CRC 相同；新文件多出来的符号只报告，不算失败
（新增的内建功能可以导出新符号，不影响已有 KMI）。
"""
import sys


def load(path):
    syms = {}
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                try:
                    syms[parts[1]] = int(parts[0], 16)
                except ValueError:
                    pass
    return syms


def main():
    base = load(sys.argv[1])
    new = load(sys.argv[2])
    missing = [s for s in base if s not in new]
    diff = [(s, base[s], new[s]) for s in base if s in new and base[s] != new[s]]
    extra = [s for s in new if s not in base]
    print(f"baseline={len(base)} new={len(new)} missing={len(missing)} "
          f"crc_diff={len(diff)} extra={len(extra)}")
    for s in missing[:20]:
        print(f"MISSING {s}")
    for s, a, b in diff[:20]:
        print(f"DIFF {s}: {a:#x} -> {b:#x}")
    for s in extra[:20]:
        print(f"EXTRA {s}")
    return 1 if missing or diff else 0


if __name__ == "__main__":
    sys.exit(main())
