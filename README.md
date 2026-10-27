# GKI 5.10.272 for Xiaomi Pad 6 Max (yudi)

基于 AOSP `android12-5.10-lts`（5.10.272）的自编译内核，目标是在小米平板 6 Max 上运行 KernelSU、Docker/Droidspaces 容器和 Wine/Proton，同时保持原厂 `vendor_boot` 模块的 KMI。

- 设备：Xiaomi Pad 6 Max（yudi，SM8475）
- 基线：`a1eed2e9c`（`Merge 5.10.272 into android12-5.10-lts`）
- 当前镜像的内核：`5.10.272-android12-9-gc87cf87d870c-dirty`
- KernelSU 模块：<https://github.com/OneFeiFan/yudi-ksu-modules>

## 仓库结构

| 目录 | 内容 |
| --- | --- |
| `source/` | 完整内核源码树（即构建系统里的 `common/`），与刷机镜像同一代码状态 |
| `patches/` | 相对 AOSP 5.10.272 的补丁系列（`series` 可在基线上重放） |
| `docs/` | 系统状态交接、KernelSU 模块说明 |
| `README.md` | 本文件 |

`source/` 是应用完补丁的最终源码树，不是 AOSP 基线。要复现它：把 AOSP `common` 检出到 `a1eed2e9c`，再按 `patches/series` 应用补丁；`patches/README.md` 有完整命令和 tree 校验值。

镜像的 `uname` 带 `-dirty`，因为构建时源码还没提交；之后的文档、补丁目录提交不改变内核二进制。从当前源码重新构建会得到新的 `g` 哈希，这是正常的。

## 构建

`source/` 对应 Android 构建环境里的 `common/`；还需要 AOSP 的 `build/` 与 `prebuilts/`：

```sh
git clone --branch pad6max https://github.com/OneFeiFan/gki-kernel-5.10-xiaomi-pad6max.git gki-yudi
mkdir -p ~/kernel-sources/vanilla-root
cp -a gki-yudi/source ~/kernel-sources/vanilla-root/common

cd ~/kernel-sources/vanilla-root
SKIP_MRPROPER=1 SKIP_CP_KERNEL_HDR=1 \
BUILD_CONFIG=common/build.config.gki.aarch64 \
OUT_DIR=~/kernel-sources/out-zram \
bash build/build.sh -j12
```

细节、硬门禁（7298 个导出符号 CRC、355 个 vendor 模块）见 [`source/README.gki-docker.md`](source/README.gki-docker.md)。

## 状态（2026-10-28）

| 项目 | 结果 |
| --- | --- |
| 开机 / KernelSU | 正常（`boot_272_simple.img`） |
| 导出符号 CRC | 7298 个，与 5.10.272 基线差异 0 |
| vendor_boot 模块 | 355 个，加载失败 0 |
| 32 位 futex_waitv | 已接线（syscall 449） |
| 内核默认值 | 保持 stock：cubic、vendor 调度器、zram `lz4` |
| 运行时开关 | 由 `yudi-tweaks` 模块开启（BBRv3、le9uo、zram `lz4kd`、KSM、ADIOS、DAMON） |

## 刷机

```sh
adb reboot bootloader
fastboot flash boot_a boot_272_simple.img
fastboot reboot
```

`boot_272_simple.img` 是 5.10.272 + KernelSU 的启动镜像。回退镜像为 `boot_backup_pre_simple.img`（stock 5.10.237 + Magisk）。刷机前请自行备份当前 `boot_a`。

## KernelSU 模块

源码和 zip：<https://github.com/OneFeiFan/yudi-ksu-modules>。默认只开安全项（sysctl、BBRv3、le9uo、zram），KSM、ADIOS、DAMON 在 WebUI 的“高级选项”里手动开启；配置在重启后生效。

## License

GPL-2.0，与上游一致。
