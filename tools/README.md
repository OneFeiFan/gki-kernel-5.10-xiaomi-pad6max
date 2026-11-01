# 验证与镜像工具

门禁的步骤和通过标准见 [docs/verification.md](../docs/verification.md)。

## KMI 与配置门禁

| 脚本 | 作用 |
| --- | --- |
| `symvers_diff.py` | 对比基线与新构建的 `vmlinux.symvers`：缺失、新增、CRC 变化 |
| `crc_scan.py` | 批量扫描目录下所有 `.ko` 的 `__versions` CRC 是否与内核 `vmlinux.symvers` 匹配 |
| `crc_check.py` | 单个模块的 `__versions` CRC 与 `vmlinux.symvers` 对比 |
| `check_config.py` | 构建出的 `.config` 是否丢了必需的选项 |
| `abi_layout_check.py` | 关键结构体的偏移和大小是否与原厂 5.10.272 GKI 一致（需要 `pahole`） |
| `gencrc.sh` | 用构建目录里记录的编译命令，对单个编译单元跑 cpp + genksyms，定位 CRC 变化的来源 |
| `bisect_configs.sh` | 按配置分组逐个编译，检查厂商模块 CRC 是否被某组配置破坏 |

## 镜像

| 脚本 | 作用 |
| --- | --- |
| `bootimg_extract.py` | 按 boot header v3/v4 解析 `boot.img`，导出 kernel 和 ramdisk |
| `bootimg_repack.py` | 按 boot v4 布局重新打包 |
| `vendor_boot_extract.py` | 解析 `vendor_boot` v4，导出各 vendor ramdisk 片段 |
| `cpio_list.py` | 列出或解出 newc cpio 的条目，检查 ramdisk 内容 |
| `cpio_repack.py` | 还原被 Magisk 改过的 ramdisk cpio |

## 设备与容器

| 脚本 | 作用 |
| --- | --- |
| `collect_system_state.sh` | 在设备上收集内核、模块和系统状态 |
| `docker-check-config.sh` | Docker 官方的 check-config（改编自 lxc-checkconfig），检查容器所需的内核选项 |
| `gen_config_map.py` | 生成 Docker 所需配置的映射表：5.10 适用性、当前值、check-config 状态 |
