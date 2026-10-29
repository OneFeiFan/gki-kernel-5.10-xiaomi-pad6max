# 验证脚本

四个脚本都用 Python 3，输入全部从命令行传：

| 脚本 | 检查内容 | 输入 |
| --- | --- | --- |
| `symvers_diff.py` | 导出符号缺失和 CRC 差异 | 基线和新内核的 `vmlinux.symvers` |
| `crc_scan.py` | 每个 `.ko` 的 `__versions` CRC | 新内核的 `vmlinux.symvers`、模块目录（可以给多个） |
| `check_config.py` | 45 项必需 `CONFIG`，以及禁止项 | 构建出的 `.config` |
| `abi_layout_check.py` | `cfs_rq`、`ipc_ids`、`netns_ipv4`、`task_group` 的布局 | 带调试信息的 `vmlinux`，需要 `pahole` |

示例（`OUT` 换成自己的构建目录）：

```sh
OUT=~/kernel-sources/out
python3 symvers_diff.py "$BASE/common/vmlinux.symvers" "$OUT/common/vmlinux.symvers"
python3 crc_scan.py "$OUT/common/vmlinux.symvers" vendor_boot_modules vendor_dlkm_modules
python3 check_config.py "$OUT/common/.config"
python3 abi_layout_check.py "$OUT/dist/vmlinux"
```

前置条件：

- 基线 `vmlinux.symvers` 要用同一套 `build/` 环境单独编译 5.10.272 基线得到。
- `vendor_boot` 和 `vendor_dlkm` 的模块目录不随仓库发布，需要从设备上的对应
  分区或镜像里取。
- `abi_layout_check.py` 依赖 `pahole`（dwarves 包），并且 `vmlinux` 要带调试信息。
