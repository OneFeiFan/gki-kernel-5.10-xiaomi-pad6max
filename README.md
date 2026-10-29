# GKI 5.10.272 for Xiaomi Pad 6 Max

基于 AOSP `android12-5.10-lts`（5.10.272）的自编译内核，设备是小米平板 6 Max
（yudi，SM8475）。目标是保持原厂 KMI 不变，同时能跑容器、Droidspaces 和
Wine/Proton。

导出符号布局保持 stock，`vendor_boot` 的 355 个模块和 `vendor_dlkm` 的 315 个
`.ko` 直接加载。新增功能：

- 容器：cgroup v1 的 devices/pids/perf/net_cls、nftables、bridge netfilter、
  IPv6 NAT、IPVS、SCTP、VXLAN/VLAN/IPVLAN/MACVLAN、L2TP/FOU/GRE、tc、
  blkio 限速、Btrfs、checkpoint/restore、CRIU diag、FHANDLE
- Wine：NTSync、futex_waitv（64/32 位）、epoll_pwait2
- 存储与调度：zram 的 LZ4K/LZ4KD、BBRv3、ADIOS、le9uo、CFS 带宽（kABI 拆分）

内核只负责能力和 stock 默认值。BBRv3、zram 算法、KSM、ADIOS、DAMON 这些运行时
开关由 KernelSU 模块负责。

当前还带两个灰度项：`WQ_POWER_EFFICIENT_DEFAULT` 和 zram writeback（小米 ExtM
的 A 探针），见 [docs/kernel.md](docs/kernel.md) 与
[docs/ExtM-research.md](docs/ExtM-research.md)。

## 仓库结构

| 目录 | 内容 |
| --- | --- |
| `source/` | 内核源码，构建环境里的 `common/` |
| `patches/` | 相对 5.10.272 的 19 个功能补丁 |
| `tools/` | 验证脚本：符号、CRC、配置、结构布局 |
| `docs/` | 构建与验证、设备状态、模块说明、GPU/ExtM 研究 |

`source/` 是应用完补丁后的树，不是基线。复现方法见 `patches/README.md`。

## 构建

`source/` 需要配 AOSP 的 `build/` 和 `prebuilts/`：

```sh
git clone --branch pad6max https://github.com/OneFeiFan/gki-kernel-5.10-xiaomi-pad6max.git gki-yudi
mkdir -p ~/kernel-sources/vanilla-root
cp -a gki-yudi/source ~/kernel-sources/vanilla-root/common

cd ~/kernel-sources/vanilla-root
SKIP_MRPROPER=1 SKIP_CP_KERNEL_HDR=1 \
BUILD_CONFIG=common/build.config.gki.aarch64 \
OUT_DIR=~/kernel-sources/out \
bash build/build.sh -j12
```

构建前建议清空 `OUT_DIR`。增量构建会复用 ThinLTO 缓存，`/proc/config.gz`
可能留在上一次的配置数据上。

硬门禁和测试方法见 [docs/kernel.md](docs/kernel.md)。

## 刷机

镜像有两个版本，内核相同，ramdisk 不同：

| 镜像 | 内容 |
| --- | --- |
| `yudi-5.10.272-20261029-ksu.img` | KernelSU |
| `yudi-5.10.272-20261029-noroot.img` | 无 root |

```sh
adb reboot bootloader
fastboot flash boot_a yudi-5.10.272-20261029-ksu.img
fastboot reboot
```

只动 `boot_a`。`vendor_boot`、`vendor_dlkm`、`dtbo` 都不需要改。

## 补丁

补丁在 `patches/`，基线是 `a1eed2e9c`（5.10.272 合并提交）。补丁按功能分目录
（`00-platform/`、`01-container/` … `10-sched/`），`series` 决定应用顺序，任意
前缀都能单独构建。按 `series` 顺序应用：

```sh
cd common
git checkout a1eed2e9c
while read p; do git am "$PATCHES/$p"; done < "$PATCHES/series"
```

## KernelSU 模块

源码和 zip：<https://github.com/OneFeiFan/yudi-ksu-modules>

| 模块 | 说明 |
| --- | --- |
| `yudi-tweaks` | 运行时开关和状态页（BBRv3、le9uo、zram、KSM、ADIOS、DAMON） |
| `ntsync` | 按 `/sys/class/misc/ntsync/dev` 创建 `/dev/ntsync` |

## 验证

以下为 2026-10-29 实测结果，详细步骤见 [docs/kernel.md](docs/kernel.md)。

- 7298 个导出符号，与 5.10.272 基线 CRC 差异 0
- 355 个 `vendor_boot` 模块、315 个 `vendor_dlkm` 模块，CRC 不匹配 0
- 设备开机 420 个模块，`dmesg` 无 CRC 或 WARNING
- NTSync v2 自测 11/11，futex_waitv 7/7，epoll 63/63
- CFS 带宽 20% 配额下 `nr_throttled` 正常增长，zram 各算法往返一致

verify 脚本还有两个已知误报：ipvlan 用例在同一个 dummy 上先建 macvlan 再建
ipvlan（两者争用 RX handler，必然 EBUSY）；设备自带的 `ss` 是
iproute2-ss171113，看不到 bbr3 诊断，用 Termux 的 iproute2 7.3.0 可复测。

## 参考

- AOSP `android12-5.10-lts`
- KernelSU
- SukiSU Ultra zram（LZ4K/LZ4KD）
- WildKernels android12-5.10 BBRv3
- ESK GKI `block/adios.c`
- le9uo
- linux-tkg futex_waitv 回移
- Goldzxcbug/Droidspaces_Kernel_patch（CFS 带宽 kABI 拆分）

## License

GPL-2.0，与上游一致。
