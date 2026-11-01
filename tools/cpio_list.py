#!/usr/bin/env python3
"""列出（或解出）newc cpio 的条目，用于检查 ramdisk 内容。"""
import os
import sys


def iter_entries(data):
    off = 0
    while off + 110 <= len(data):
        magic = data[off:off + 6]
        if magic not in (b"070701", b"070702"):
            raise SystemExit(f"bad cpio magic at {off}: {magic!r}")
        fields = [int(data[off + 6 + i * 8:off + 6 + (i + 1) * 8], 16) for i in range(13)]
        (ino, mode, uid, gid, nlink, mtime, filesize, devmajor, devminor,
         rdevmajor, rdevminor, namesize, check) = fields
        name_start = off + 110
        name = data[name_start:name_start + namesize - 1].decode("utf-8", "replace")
        data_start = (name_start + namesize + 3) & ~3
        yield name, mode, filesize, off, data_start
        if name == "TRAILER!!!":
            return
        off = (data_start + filesize + 3) & ~3


def main() -> int:
    cpio_path = sys.argv[1]
    extract_dir = sys.argv[2] if len(sys.argv) > 2 else None
    with open(cpio_path, "rb") as f:
        data = f.read()

    count = 0
    for name, mode, filesize, _, data_start in iter_entries(data):
        if name == "TRAILER!!!":
            break
        count += 1
        kind = "d" if (mode & 0o170000) == 0o040000 else ("l" if (mode & 0o170000) == 0o120000 else "-")
        perms = mode & 0o7777
        if extract_dir:
            dest = os.path.join(extract_dir, name.lstrip("/"))
            if kind == "d":
                os.makedirs(dest, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
                with open(dest, "wb") as out:
                    out.write(data[data_start:data_start + filesize])
                os.chmod(dest, perms)
        else:
            print(f"{kind} {perms:04o} {filesize:9d}  {name}")
    if not extract_dir:
        print(f"--- {count} entries ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
