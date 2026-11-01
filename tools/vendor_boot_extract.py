#!/usr/bin/env python3
"""解析 vendor_boot v4，导出各 vendor ramdisk 片段。
用法: vendor_boot_extract.py <vendor_boot.img> <输出目录>
"""
import os
import struct
import sys


def align(x, a):
    return (x + a - 1) // a * a


def main() -> int:
    img, outdir = sys.argv[1], sys.argv[2]
    with open(img, "rb") as f:
        data = f.read()
    if data[:8] != b"VNDRBOOT":
        raise SystemExit("不是 vendor_boot")
    (header_version, page_size, kernel_addr, ramdisk_addr, vrd_size) = struct.unpack_from("<IIIII", data, 8)
    tags_addr = struct.unpack_from("<I", data, 28 + 2048)[0]
    name = data[2080:2096].split(b"\0")[0].decode()
    header_size, dtb_size, dtb_addr = struct.unpack_from("<IIQ", data, 2096)
    table_size, entry_num, entry_size, bootconfig_size = struct.unpack_from("<IIII", data, 2112)
    print(f"version={header_version} page={page_size} header={header_size} name={name}")
    print(f"vendor_ramdisk_size={vrd_size} dtb_size={dtb_size} table_size={table_size} "
          f"entries={entry_num} entry_size={entry_size} bootconfig={bootconfig_size}")

    rd_off = align(header_size, page_size)
    dtb_off = align(rd_off + vrd_size, page_size)
    table_off = align(dtb_off + dtb_size, page_size)
    bootconfig_off = align(table_off + table_size, page_size)
    print(f"rd_off={rd_off} dtb_off={dtb_off} table_off={table_off} bootconfig_off={bootconfig_off}")

    os.makedirs(outdir, exist_ok=True)
    for i in range(entry_num):
        off = table_off + i * entry_size
        rsize, roff, rtype = struct.unpack_from("<III", data, off)
        rname = data[off + 12:off + 44].split(b"\0")[0].decode()
        blob = data[rd_off + roff: rd_off + roff + rsize]
        path = os.path.join(outdir, f"rd{i:02d}_{rname or 'unnamed'}.bin")
        with open(path, "wb") as f:
            f.write(blob)
        magic = blob[:4].hex()
        print(f"  [{i}] name={rname!r} type={rtype} size={rsize} offset={roff} magic={magic} -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
