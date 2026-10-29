#!/usr/bin/env python3
"""批量扫描目录下所有 .ko 的 __versions CRC 是否与内核 vmlinux.symvers 匹配。
用法: crc_scan.py <vmlinux.symvers> <目录> [更多目录...]
只报告有 CRC 不一致的模块；missing 视为由其它模块提供，不计失败。
"""
import glob
import os
import struct
import sys


def elf_section(path, want):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        return None
    e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
    e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
    e_shstrndx = struct.unpack_from("<H", data, 0x3E)[0]

    def sh(i):
        fields = struct.unpack_from("<IIQQQQIIQQ", data, e_shoff + i * e_shentsize)
        return {"name_off": fields[0], "offset": fields[4], "size": fields[5]}

    strtab = sh(e_shstrndx)

    def name_of(s):
        start = strtab["offset"] + s["name_off"]
        return data[start:data.index(b"\0", start)].decode()

    for i in range(e_shnum):
        s = sh(i)
        if name_of(s) == want:
            return data[s["offset"]:s["offset"] + s["size"]]
    return None


def load_symvers(path):
    kern = {}
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                try:
                    kern[parts[1]] = int(parts[0], 16)
                except ValueError:
                    pass
    return kern


def main() -> int:
    symvers, dirs = sys.argv[1], sys.argv[2:]
    kern = load_symvers(symvers)
    total = bad_modules = no_versions = 0
    total_mismatch = 0
    for d in dirs:
        for ko in sorted(glob.glob(os.path.join(d, "**", "*.ko"), recursive=True)):
            total += 1
            vers = elf_section(ko, "__versions")
            if vers is None:
                no_versions += 1
                continue
            bad = []
            for i in range(0, len(vers) - 63, 64):
                crc = struct.unpack_from("<Q", vers, i)[0]
                name = vers[i + 8:i + 64].split(b"\0")[0].decode("ascii", "replace")
                if not name or name not in kern:
                    continue
                if kern[name] != crc:
                    bad.append(name)
            if bad:
                bad_modules += 1
                total_mismatch += len(bad)
                print(f"FAIL {os.path.basename(ko)} mismatch={len(bad)}: {', '.join(bad[:6])}")
    print(f"--- modules={total} no_versions={no_versions} failing={bad_modules} "
          f"mismatched_symbols={total_mismatch} ---")
    return 1 if bad_modules else 0


if __name__ == "__main__":
    sys.exit(main())
