#!/usr/bin/env python3
"""对比内核模块 __versions 里的 CRC 与内核 vmlinux.symvers。
用法: crc_check.py <module.ko> <vmlinux.symvers>
"""
import struct
import sys


def elf_section(path, want):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise SystemExit("不是 ELF64 little-endian")
    e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
    e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
    e_shstrndx = struct.unpack_from("<H", data, 0x3E)[0]

    def sh(i):
        off = e_shoff + i * e_shentsize
        fields = struct.unpack_from("<IIQQQQIIQQ", data, off)
        return {
            "name_off": fields[0], "type": fields[1], "offset": fields[4],
            "size": fields[5], "entsize": fields[9],
        }

    strtab = sh(e_shstrndx)

    def name_of(s):
        start = strtab["offset"] + s["name_off"]
        end = data.index(b"\0", start)
        return data[start:end].decode()

    for i in range(e_shnum):
        s = sh(i)
        if name_of(s) == want:
            return data[s["offset"]:s["offset"] + s["size"]]
    return None


def main() -> int:
    ko, symvers = sys.argv[1], sys.argv[2]
    vers = elf_section(ko, "__versions")
    if vers is None:
        print(f"{ko}: 没有 __versions（可能未启用 modversions）")
        return 0
    entries = []
    for i in range(0, len(vers) - 63, 64):
        crc = struct.unpack_from("<Q", vers, i)[0]
        name = vers[i + 8:i + 64].split(b"\0")[0].decode("ascii", "replace")
        if name:
            entries.append((crc, name))

    kern = {}
    with open(symvers) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                try:
                    kern[parts[1]] = int(parts[0], 16)
                except ValueError:
                    pass

    bad = []
    missing = []
    for crc, name in entries:
        if name not in kern:
            missing.append(name)
        elif kern[name] != crc:
            bad.append((name, crc, kern[name]))

    print(f"{ko}: entries={len(entries)} mismatch={len(bad)} missing={len(missing)}")
    for name, c, k in bad[:20]:
        print(f"  MISMATCH {name}: ko={c:#x} kernel={k:#x}")
    for name in missing[:10]:
        print(f"  MISSING {name}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
