# GKI 5.10.272 for Xiaomi Pad 6 Max (yudi)

基于 AOSP `android12-5.10-lts` 的自编译内核，目标是在小米平板 6 Max 上直接运行 Docker/Droidspaces 容器和 Wine/Proton，同时不破坏原厂 `vendor_boot` 模块的 KMI。

- 设备：Xiaomi Pad 6 Max（yudi，SM8475）
- 内核：`5.10.272-android12-9-gd2cb81ef9dcf-dirty`（2026-10-28 构建，含 32 位 futex_waitv 与 CFS_BANDWIDTH）
- 当前镜像：`boot_272_cfsbw.img`（272 + KernelSU + CFS_BANDWIDTH）
- 回退镜像：`boot_272_simple.img`（上一版 272 + KernelSU）；stock 备份为 `boot_backup_pre_simple.img`
- GitHub：<https://github.com/OneFeiFan/gki-kernel-5.10-xiaomi-pad6max>（无历史快照分支 `pad6max`）

## 状态

| 项目 | 结果 |
| --- | --- |
| 开机、KernelSU | 正常 |
| 导出符号 CRC | 7298 个，与 5.10.272 基线差异 0 |
| vendor_boot 模块 | 355 个，加载失败 0 |
| vendor_dlkm 模块 | 315 个 .ko，CRC 不匹配 0 |
| zram | 默认 16GB `lz4`；`lz4kd` 由模块在运行时切换 |
| 默认拥塞控制 | `cubic`；BBRv3 由模块按需开启 |
| ADIOS | 可选，不作为默认；UFS 由 vendor 设为 BFQ/cpq |
| 32 位 futex_waitv | 已接线（syscall 449） |
| CPU 限制 | CFS_BANDWIDTH 已开启（kABI 拆分），Droidspaces `--cpus` 可用 |

## 功能

| 方向 | 内容 |
| --- | --- |
| 容器 | cgroup devices/pids/perf/net_cls、nftables、bridge netfilter、IPv6 NAT、IPVS、SCTP、VXLAN、VLAN、IPVLAN、MACVLAN、L2TP、FOU、GRE、tc、BLK_DEV_THROTTLING、Btrfs、checkpoint/restore |
| Wine/Proton | NTSync（`/dev/ntsync`）、`futex_waitv`（syscall 449，64/32 位）、`epoll_pwait2`（syscall 441） |
| 内存 | le9uo 工作集保护（补丁默认开启）；KSM 可用但默认不运行 |
| 存储 | zram/zsmalloc 内建，LZ4K/LZ4KD + ARM64 NEON，默认 `lz4` |
| 调度 | CFS_BANDWIDTH（CPU 限制 `--cpus`） |
| 网络 | BBRv1/BBRv3 可选，默认 `cubic`；TMPFS_XATTR/POSIX_ACL |
| 块层 | ADIOS 调度器可选，含 blk-mq hctx 顺序修复 |
| 安全 | dcache、overlayfs、nfnetlink_log、cpuset 四个容器相关补丁 |

## 实现要点

- cgroup 的 devices/pids/perf/net_cls 用 MAIN/EXT 拆分，新增控制器状态放在动态 ext 结构里，`struct cgroup`/`css_set` 大小不变。
- nftables、IPVS、SCTP 等新增状态放在 `struct net`、`struct netns_nf`、`struct net_device` 的 KABI reserve 或天然空洞里。
- 所有会影响 genksyms 的条件字段都用 `!defined(__GENKSYMS__)` 隐藏，保证 7298 个符号 CRC 不变。
- CFS_BANDWIDTH 用 kABI 拆分：每个 `cfs_rq` 的带宽状态放到单独分配的 `cfs_rq_bandwidth`，`task_group` 的状态单独分配，指针放 `ANDROID_KABI_RESERVE(2)`；`cfs_rq` 指针对 genksyms 隐藏。指针在 `cfs_rq` 内占 344 偏移，vendor 数据数组随之从 344 移到 352（static_assert 钉住；vendor 模块不使用这两个字段）。移植自 Goldzxcbug 的 5.15 `cgroup_limits` 补丁。
- ADIOS 的 `limit_depth()` 依赖 `data->hctx`；5.10 的顺序修复保留，ADIOS 仍是可选项。
- 内核不再改写 zram 算法：默认 `lz4`，需要 `lz4kd` 时由 `yudi-tweaks` 模块在开机后 swapoff/reset 切换。
- 内核只保证能力和 stock 默认；BBRv3、ADIOS、zram、KSM、DAMON 等运行时开关交给模块。le9uo 是例外：补丁自身默认开启（`mm/vmscan.c` 默认值 1），模块可以关。

## 构建

```sh
cd ~/kernel-sources/vanilla-root
SKIP_MRPROPER=1 SKIP_CP_KERNEL_HDR=1 \
BUILD_CONFIG=common/build.config.gki.aarch64 \
OUT_DIR=~/kernel-sources/out-zram \
bash build/build.sh -j12
```

本仓库的 `source/` 就是上面的 `common/` 内核树；构建工具 `build/`、`prebuilts/` 需要按 AOSP 的方式另外准备。

构建使用 ThinLTO。`out-zram` 是沿用下来的目录名，不代表构建内容只和 zram 有关。

构建后跑这些硬门禁：

```sh
# 全量导出符号：缺失 0，CRC 差异 0
python3 tools/symvers_diff.py \
  out-final/dist/vmlinux.symvers out-zram/dist/vmlinux.symvers

# 355 个 vendor_boot 模块：0 失败
python3 tools/crc_scan.py \
  out-zram/dist/vmlinux.symvers work/vendor_boot/root

# vendor_dlkm 的 315 个 .ko：0 失败
python3 tools/crc_scan.py \
  out-zram/dist/vmlinux.symvers work/vendor_dlkm/modules

# 关键 CONFIG（构建脚本的 check_defconfig 被跳过，单独校验）
python3 tools/check_config.py out-zram/common/.config

# 关键结构体布局（以 AOSP 5.10.272 基线为准）
python3 tools/abi_layout_check.py out-zram/dist/vmlinux
```

需要看布局时用 `pahole` 核对 `struct net`、`struct net_device`、`struct request_queue` 等关键结构。

## 刷机

```sh
adb reboot bootloader
fastboot flash boot_a boot_272_cfsbw.img
fastboot reboot
```

刷前确认 `boot_272_simple.img`（上一版已验证）和 `boot_backup_pre_simple.img`（stock）存在。回退：

```sh
fastboot flash boot_a boot_272_simple.img
# 或者彻底回到 stock：
fastboot flash boot_a boot_backup_pre_simple.img
```

`uname` 里的时间来自 HEAD 提交时间，同一提交下多次构建看起来一样，不能用来区分构建。

## 运行时设置

两个 KernelSU 模块：

| 模块 | 作用 |
| --- | --- |
| `ntsync` | 开机创建 `/dev/ntsync`（字符设备 10:127） |
| `yudi-tweaks` | WebUI 配置内核运行时开关；默认只开安全项（sysctl、BBRv3、le9uo、zram） |

`yudi-tweaks` 默认设置的值：

| 参数 | 值 |
| --- | --- |
| `vm.max_map_count` | 1048576 |
| `fs.inotify.max_user_watches` | 524288 |
| `fs.inotify.max_user_instances` | 1024 |

自查：

```sh
cat /proc/sys/vm/max_map_count
cat /proc/sys/fs/inotify/max_user_watches
cat /proc/sys/fs/inotify/max_user_instances
grep ntsync /proc/misc
grep __arm64_sys_futex_waitv /proc/kallsyms
grep __arm64_compat_sys_futex_waitv /proc/kallsyms
grep __arm64_sys_epoll_pwait2 /proc/kallsyms
/data/local/tmp/futex_test32; echo $?   # 32 位：0 = 通过
cat /proc/sys/vm/workingset_protection
cat /sys/block/zram0/comp_algorithm
cat /sys/block/zram0/disksize
cat /proc/sys/net/ipv4/tcp_congestion_control
grep -H . /sys/block/sda/queue/scheduler
/data/local/Droidspaces/bin/droidspaces check   # 需要 root；CPU limit support 应为 ✓
```

## 补丁

补丁放在仓库顶层的 `patches/`（不在本源码目录内），只包含本项目相对 5.10.272 的改动。

- 基线：`a1eed2e9c`（`Merge 5.10.272 into android12-5.10-lts`）
- 顺序：`patches/series`
- 分类：`00-platform`、`01-container`、`02-wine`、`03-memory`、`04-security`、`05-storage`、`06-network`、`07-block`、`08-syscalls`、`09-docs`、`10-sched`
- 索引：`patches/README.md`

在 AOSP 基线树上应用（把 `PATCHES` 指向本仓库的 `patches/`）：

```sh
cd common
git checkout a1eed2e9c
PATCHES=/path/to/gki-yudi/patches
while read p; do git am "$PATCHES/$p"; done < "$PATCHES/series"
```

`patches/` 目录本身不在补丁里；应用完 series 后的源码树应与本仓库的 `source/` 一致。

## 已知限制

- **ADIOS 不是默认调度器**：vendor 的 `init.qti.kernel.rc` 会把 sda–sdh/mmcblk 写成 BFQ（smartfocusio 开启时 sda 写 cpq）。需要 ADIOS 时由 `yudi-tweaks` 在开机后切换。
- **KSM 默认关闭**：`/sys/kernel/mm/ksm/run=0`；按进程 KSM 尚未实现。
- **`tcp_plb_enabled=0`**：PLB 是数据中心 IPv6 多路径优化，手机网络没有收益。
- **`CONFIG_MODULE_SIG` 未开启**：GKI 基线默认就没有开启，本仓库不再显式写 `=n`（写不写结果一样）。
- **zram 切换有前提**：模块会先 swapoff + reset；已用 swap 超过阈值时跳过，等下次重启再切。
- **未全局开启 overlayfs metacopy/index**：这两个开关会改默认行为，metacopy 还会连带 redirect_dir。
- **未启用**：HUGETLB/CGROUP_HUGETLB、AppArmor、MGLRU。
- **CFS_BANDWIDTH 已开启**：用 kABI 拆分保留 vendor 模块，`--cpus` 可用；之前 inline 开启会开不了机，现在把带宽状态移到 ext 对象解决。唯一布局差异是 `cfs_rq.android_vendor_data1` 从 344 移到 352；`ipc_ids.key_ht`（104）和 `netns_ipv4.tcp_death_row`（640）已用 static_assert 钉回 stock。
- **安全基线是 5.10.272**：尚未合并更新的 `android12-5.10-lts`。

## 参考

- AOSP `android12-5.10-lts`
- KernelSU
- SukiSU Ultra zram（LZ4K/LZ4KD）
- WildKernels android12-5.10 BBRv3
- ESK GKI `block/adios.c`
- le9uo
- linux-tkg futex_waitv 回移
- `kernel-workshop-docker` 的 fulldocker 配置参考
- Goldzxcbug/Droidspaces_Kernel_patch（`cgroup_limits` 的 CFS_BANDWIDTH kABI 拆分）

## License

内核代码遵循 GPL-2.0，与上游一致。
