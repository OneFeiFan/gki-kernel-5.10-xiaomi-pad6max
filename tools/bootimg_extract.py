#!/usr/bin/env python3
"""按 Android boot header v3/v4 解析 boot.img，导出 kernel / ramdisk 原始数据。"""
import os
import struct
import sys


def main() -> int:
    img_path, outdir = sys.argv[1], sys.argv[2]
    with open(img_path, "rb") as f:
        data = f.read()

    if data[:8] != b"ANDROID!":
        print("不是 Android boot image")
        return 2

    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<IIII", data, 8)
    header_version = struct.unpack_from("<I", data, 40)[0]
    signature_size = 0
    if header_version >= 4 and header_size >= 1584:
        signature_size = struct.unpack_from("<I", data, 1580)[0]

    print(f"header_version={header_version} header_size={header_size}")
    print(f"kernel_size={kernel_size} ramdisk_size={ramdisk_size} "
          f"os_version=0x{os_version:08x} signature_size={signature_size}")

    page = 4096
    kernel_off = page
    ramdisk_off = kernel_off + ((kernel_size + page - 1) // page) * page

    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "kernel"), "wb") as f:
        f.write(data[kernel_off:kernel_off + kernel_size])
    with open(os.path.join(outdir, "ramdisk"), "wb") as f:
        f.write(data[ramdisk_off:ramdisk_off + ramdisk_size])

    print(f"kernel  magic: {data[kernel_off:kernel_off + 8].hex()}")
    print(f"ramdisk magic: {data[ramdisk_off:ramdisk_off + 8].hex()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
