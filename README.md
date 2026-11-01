# GKI 5.10.272 for Xiaomi Pad 6 Max

基于 AOSP `android12-5.10-lts`（ACK `8059ae2`，Linux 5.10.272）的自编译内核，设备是小米平板 6 Max
（yudi，SM8475）。目标是保持原厂 KMI 不变，同时能跑容器、Droidspaces 和
Wine/Proton。

导出符号布局保持 stock，`vendor_boot` 的 355 个模块和 `vendor_dlkm` 的 315 个
`.ko` 直接加载。新增功能：

- 容器：cgroup v1 的 devices/pids/perf/net_cls、nftables、bridge netfilter、
  IPv6 NAT、IPVS、SCTP、VXLAN/VLAN/IPVLAN/MACVLAN、L2TP/FOU/GRE、tc、
  blkio 限速、Btrfs、checkpoint/restore、CRIU diag、FHANDLE
- Wine：NTSync、futex_waitv（64/32 位）、epoll_pwait2
- 存储与调度：内建 zram 与 LZ4K/LZ4KD、小米 ExtM 与内存冻结（`xiaomi/` 组）、BBRv3、ADIOS、le9uo、CFS 带宽（kABI 拆分）

内核只负责能力和 stock 默认值。BBRv3、zram 算法、KSM、ADIOS、DAMON 这些运行时
开关由 KernelSU 模块负责。

当前还带一个灰度项：`WQ_POWER_EFFICIENT_DEFAULT`。zram 内建并由本仓库维护，小米 ExtM 来自
小米官方开源源码（`patches/xiaomi/`），与第三方月亮内核完全切割，见 [docs/kernel.md](docs/kernel.md) 与
[docs/ExtM-research.md](docs/ExtM-research.md)。

cpuidle governor 默认跟随系统（`qcom-cpu-lpm`）；`yudi-tweaks` 2.2 提供 TEO、
RCU 惰性回调等运行时开关。RCU 惰性回调默认关闭，路径是
`/sys/module/rcutree/parameters/enable_rcu_lazy`；PELT multiplier 实测无显著
收益，保持默认 `1`；SSG 只保留可选补丁，默认仍是 cpq。

## 生态调研

2026-10-30 对 10 个方向做了只读盘点，结论和差距见
[docs/ecosystem-survey.md](docs/ecosystem-survey.md)。只归档，没有据此改内核。

2026-10-31 基线已升到 ACK lts 最新 `8059ae2`。此后 r6–r14 陆续加入正确性修复、
f2fs 修正、binder 位图查找和 RCU 惰性回调；当前共 103 个补丁（通用 99 + 小米 4），
r16 树是 `7f30604d...`。r16 在 r14 基础上加了 SCSI EH 的 `call_rcu_hurry()` 修正；
r15 是可选的 SSG 临时测试镜像，SSG 不设默认，默认仍是 cpq。

## 仓库结构

| 目录 | 内容 |
| --- | --- |
| `source/` | 内核源码，构建环境里的 `common/` |
| `patches/` | 相对 5.10.272 的 103 个功能补丁 |
| `tools/` | 验证脚本：符号、CRC、配置、结构布局 |
| `docs/` | 构建与验证、设备状态、模块说明、GPU/ExtM 研究、生态调研 |

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

每个内核有两个版本（KernelSU / 无 root），内核相同，ramdisk 不同。最后发布的是 r3（2026-10-30）；r4–r16 只在本地构建。
当前稳定镜像是 r16（r14 + SCSI fix），r14/r15 保留作回退和 SSG 试验（SSG 默认不启用，sda 仍是 cpq）。

| 镜像 | 内容 |
| --- | --- |
| `~/kernel-sources/work/r14-images/yudi-5.10.272-20261101-r14-rcu-ksu.img` | r14 稳定，KernelSU |
| `~/kernel-sources/work/r14-images/yudi-5.10.272-20261101-r14-rcu-noroot.img` | r14 稳定，无 root |
| `~/kernel-sources/work/r15-ssg-images/yudi-5.10.272-20261101-r15-ssg-ksu.img` | r15 SSG 可选试验，KernelSU |
| `~/kernel-sources/work/r15-ssg-images/yudi-5.10.272-20261101-r15-ssg-noroot.img` | r15 SSG 可选试验，无 root |
| `~/kernel-sources/work/r16-scsi-images/yudi-5.10.272-20261101-r16-scsi-ksu.img` | r16 SCSI fix，KernelSU |
| `~/kernel-sources/work/r16-scsi-images/yudi-5.10.272-20261101-r16-scsi-noroot.img` | r16 SCSI fix，无 root |

```sh
adb reboot bootloader
fastboot flash boot_a ~/kernel-sources/work/r16-scsi-images/yudi-5.10.272-20261101-r16-scsi-ksu.img
fastboot reboot
```

只动 `boot_a`。`vendor_boot`、`vendor_dlkm`、`dtbo` 都不需要改。

## 补丁

补丁在 `patches/`，基线是 `8059ae2`（ACK `android12-5.10-lts`，2026-10-24）。`series`
99 条、`series.xiaomi` 103 条（通用 99 + 小米 4），按功能分目录
（`00-platform/` … `16-rcu/`），`series` 决定应用顺序。按 `series` 顺序应用：

```sh
cd common
git checkout 8059ae2
while read p; do git am "$PATCHES/$p"; done < "$PATCHES/series"
```

## KernelSU 模块

源码和 zip：<https://github.com/OneFeiFan/yudi-ksu-modules>

| 模块 | 说明 |
| --- | --- |
| `yudi-tweaks` | 运行时开关和状态页（BBRv3、le9uo、zram、KSM、ADIOS、DAMON、cpuidle governor、RCU 惰性回调） |
| `ntsync` | 按 `/sys/class/misc/ntsync/dev` 创建 `/dev/ntsync` |

## 验证

以下为 2026-11-01 r16 的快速验证结果；NTSync/futex/epoll 和 CFS/zram 往返是
2026-10-30 r4 的结果，r16 没有重跑这些用例。详细步骤见 [docs/kernel.md](docs/kernel.md)。

- 7298 个导出符号，缺失 0，CRC 差异 0；670 个 vendor 模块 CRC 不匹配 0
- 47 项 CONFIG 满足；`cfs_rq` 布局与 stock 一致
- 设备开机 419 个模块、369 个服务；`dmesg` 无 RCU stall、panic/Oops
- RCU 开关写 1/0 正常；5000 文件 churn 未见异常；`enable_rcu_lazy` 默认 N
- 全量 345 个 `call_rcu` 审计完成；当前配置唯一必改的 SCSI EH 已改用 `call_rcu_hurry`
- NTSync v2 自测 11/11，futex_waitv 7/7，epoll 63/63（r4）
- CFS 带宽 20% 配额下 `nr_throttled` 正常增长，zram 各算法往返一致（r4）

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
