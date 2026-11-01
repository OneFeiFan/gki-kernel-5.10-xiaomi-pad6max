#!/usr/bin/env python3
"""按 android-bootimg(BootImagePatchOption) 的布局规则重打包 boot v4：
- 保留原 header（更新 kernel/ramdisk/signature 大小）
- 保留 signature 块
- 保留并修补 AVB tail / vbmeta / footer
用法: bootimg_repack.py <原始boot.img> <新ramdisk(已压缩)> <输出boot.img> [新kernel(Image)]
不给新 kernel 时沿用原镜像里的 kernel。
"""
import struct
import sys


def align(x, a):
    return (x + a - 1) // a * a


def main() -> int:
    src, ramdisk_path, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    new_kernel_path = sys.argv[4] if len(sys.argv) > 4 else None
    with open(src, "rb") as f:
        data = f.read()
    with open(ramdisk_path, "rb") as f:
        rd = f.read()

    if data[:8] != b"ANDROID!":
        raise SystemExit("不是 Android boot image")

    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<IIII", data, 8)
    header_version = struct.unpack_from("<I", data, 40)[0]
    signature_size = struct.unpack_from("<I", data, 1580)[0]
    if header_version != 4:
        raise SystemExit(f"只支持 boot v4，当前 v{header_version}")

    page = 4096
    off = align(header_size, page)
    kernel = data[off:off + kernel_size]
    if new_kernel_path:
        with open(new_kernel_path, "rb") as f:
            kernel = f.read()
        print(f"替换 kernel: {kernel_size} -> {len(kernel)} 字节")
    off = align(off + kernel_size, page)
    off = align(off + ramdisk_size, page)          # 跳过旧 ramdisk
    signature = data[off:off + signature_size]
    off = align(off + signature_size, page)
    tail = off

    avb = None
    footer = bytearray(data[-64:])
    if footer[:4] == b"AVBf":
        orig_size, vbmeta_off, vbmeta_size = struct.unpack_from(">QQQ", footer, 12)
        avb_header = data[vbmeta_off:vbmeta_off + vbmeta_size]
        if avb_header[:4] != b"AVB0":
            raise SystemExit("AVB footer 存在但 vbmeta 无效")
        if orig_size < tail:
            raise SystemExit(f"AVB original_image_size({orig_size}) < tail({tail})")
        avb_tail = data[tail:orig_size]
        avb = (avb_tail, avb_header)
        print(f"AVB: tail={len(avb_tail)} vbmeta_off={vbmeta_off} vbmeta_size={vbmeta_size} "
              f"orig_size={orig_size}")
    else:
        print("无 AVB footer，按无 AVB 处理")

    out = bytearray(len(data))
    header = bytearray(data[:page])
    struct.pack_into("<I", header, 8, len(kernel))
    struct.pack_into("<I", header, 12, len(rd))
    struct.pack_into("<I", header, 1580, len(signature))
    out[0:page] = header

    pos = page
    out[pos:pos + len(kernel)] = kernel
    pos = align(pos + len(kernel), page)
    out[pos:pos + len(rd)] = rd
    pos = align(pos + len(rd), page)
    out[pos:pos + len(signature)] = signature
    pos = align(pos + len(signature), page)

    if avb:
        avb_tail, avb_header = avb
        out[pos:pos + len(avb_tail)] = avb_tail
        pos = align(pos + len(avb_tail), page)
        total_size = pos
        pos = align(pos, 4096)
        avb_header_off = pos
        out[pos:pos + len(avb_header)] = avb_header
        pos += len(avb_header)
        zero_end = len(data) - 64
        if pos > zero_end:
            raise SystemExit(f"没有空间放 AVB: payload_end={pos} footer={zero_end}")
        struct.pack_into(">Q", footer, 12, total_size)
        struct.pack_into(">Q", footer, 20, avb_header_off)
        out[zero_end:] = footer

    with open(dst, "wb") as f:
        f.write(out)
    print(f"kernel={len(kernel)} ramdisk={len(rd)} signature={len(signature)} "
          f"payload_end={pos} total={len(out)} -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
