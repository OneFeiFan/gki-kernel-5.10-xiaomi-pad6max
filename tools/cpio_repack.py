#!/usr/bin/env python3
"""还原 Magisk 改过的 ramdisk cpio：
- 用原厂 init 替换 magiskinit
- 删除 .backup/ 和 overlay.d/（Magisk 添加的内容）
其余条目原样保留。
用法: cpio_repack.py <原始.cpio> <原厂init> <输出.cpio>
"""
import sys


def iter_entries(data):
    off = 0
    while off + 110 <= len(data):
        magic = data[off:off + 6]
        if magic not in (b"070701", b"070702"):
            raise SystemExit(f"bad cpio magic at {off}: {magic!r}")
        fields = [int(data[off + 6 + i * 8:off + 6 + (i + 1) * 8], 16) for i in range(13)]
        namesize = fields[11]
        name_start = off + 110
        name = data[name_start:name_start + namesize - 1].decode("utf-8", "replace")
        data_start = (name_start + namesize + 3) & ~3
        size = fields[6]
        yield fields, name, data[data_start:data_start + size]
        if name == "TRAILER!!!":
            return
        off = (data_start + size + 3) & ~3


def pack(fields, name, payload):
    ino, mode, uid, gid, nlink, mtime, _size, devmaj, devmin, rdevmaj, rdevmin, _namesize, check = fields
    name_bytes = name.encode() + b"\0"
    header = b"070701" + b"".join(
        f"{v:08X}".encode()
        for v in [ino, mode, uid, gid, nlink, mtime, len(payload),
                  devmaj, devmin, rdevmaj, rdevmin, len(name_bytes), check]
    )
    out = header + name_bytes
    out += b"\0" * ((-len(out)) % 4)
    out += payload
    out += b"\0" * ((-len(payload)) % 4)
    return out


def main() -> int:
    src, init_path, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(src, "rb") as f:
        data = f.read()
    with open(init_path, "rb") as f:
        stock_init = f.read()
    if stock_init[:4] != b"\x7fELF":
        raise SystemExit("原厂 init 不是 ELF")

    out = bytearray()
    kept = replaced = dropped = 0
    for fields, name, payload in iter_entries(data):
        if name == ".backup" or name.startswith(".backup/"):
            dropped += 1
            continue
        if name == "overlay.d" or name.startswith("overlay.d/"):
            dropped += 1
            continue
        if name == "init":
            payload = stock_init
            fields[6] = len(payload)
            replaced += 1
        out += pack(fields, name, payload)
        kept += 1

    with open(dst, "wb") as f:
        f.write(out)
    print(f"kept={kept} init_replaced={replaced} dropped={dropped} size={len(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
