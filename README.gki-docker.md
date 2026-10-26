# GKI 5.10.272 for Xiaomi Pad 6 Max (yudi)

基于 AOSP `android12-5.10-lts` 的自编译内核，目标是在小米平板 6 Max 上直接运行 Docker/Droidspaces 容器和 Wine/Proton，同时不破坏原厂 `vendor_boot` 模块的 KMI。

- 设备：Xiaomi Pad 6 Max（yudi，SM8475）
- 内核：`5.10.272-android12-9-geba364b9a173-dirty`
- 当前镜像：`boot_272_epoll.img`
- 回退镜像：`boot_backup_pre_epoll.img`
- GitHub：<https://github.com/OneFeiFan/gki-kernel-5.10-xiaomi-pad6max>（无历史快照分支 `pad6max`）

## 状态

| 项目 | 结果 |
| --- | --- |
| 开机、KernelSU | 正常 |
| 导出符号 CRC | 7298 个，与 5.10.272 基线差异 0 |
| vendor_boot 模块 | 355 个，加载失败 0 |
| zram | 16GB，`lz4kd` |
| 默认拥塞控制 | BBRv3 |
| ADIOS | 内核默认；UFS 实际仍被 vendor 设为 BFQ/cpq |

## 功能

| 方向 | 内容 |
| --- | --- |
| 容器 | cgroup devices/pids/perf/net_cls、nftables、bridge netfilter、IPv6 NAT、IPVS、SCTP、VXLAN、VLAN、IPVLAN、MACVLAN、L2TP、FOU、GRE、tc、BLK_DEV_THROTTLING、Btrfs、checkpoint/restore |
| Wine/Proton | NTSync（`/dev/ntsync`）、`futex_waitv`（syscall 449）、`epoll_pwait2`（syscall 441） |
| 内存 | le9uo 工作集保护；KSM 可用但默认不运行 |
| 存储 | zram/zsmalloc 内建，LZ4K/LZ4KD + ARM64 NEON，默认 `lz4kd` |
| 网络 | BBRv1 可选，BBRv3 默认；TMPFS_XATTR/POSIX_ACL |
| 块层 | ADIOS 调度器，含 blk-mq hctx 顺序修复 |
| 安全 | dcache、overlayfs、nfnetlink_log、cpuset 四个容器相关补丁 |

## 实现要点

- cgroup 的 devices/pids/perf/net_cls 用 MAIN/EXT 拆分，新增控制器状态放在动态 ext 结构里，`struct cgroup`/`css_set` 大小不变。
- nftables、IPVS、SCTP 等新增状态放在 `struct net`、`struct netns_nf`、`struct net_device` 的 KABI reserve 或天然空洞里。
- 所有会影响 genksyms 的条件字段都用 `!defined(__GENKSYMS__)` 隐藏，保证 7298 个符号 CRC 不变。
- ADIOS 的 `limit_depth()` 依赖 `data->hctx`，而 5.10 原来在调用 `limit_depth()` 之后才设置 hctx；blk-mq 这处顺序修好之后 ADIOS 才能作为默认调度器。
- zram 驱动在 `comp_algorithm_store()` 里把 vendor 写的 `lz4` 映射为 `lz4kd`，所以不需要改 vendor init。

## 构建

```sh
cd ~/kernel-sources/vanilla-root
SKIP_MRPROPER=1 SKIP_CP_KERNEL_HDR=1 \
BUILD_CONFIG=common/build.config.gki.aarch64 \
OUT_DIR=~/kernel-sources/out-zram \
bash build/build.sh -j12
```

构建使用 ThinLTO。`out-zram` 是沿用下来的目录名，不代表构建内容只和 zram 有关。

构建后跑两项硬门禁：

```sh
# 全量导出符号：缺失 0，CRC 差异 0
python3 tools/symvers_diff.py \
  out-final/dist/vmlinux.symvers out-zram/dist/vmlinux.symvers

# 355 个 vendor_boot 模块：0 失败
python3 tools/crc_scan.py \
  out-zram/dist/vmlinux.symvers work/vendor_boot/root
```

需要看布局时用 `pahole` 核对 `struct net`、`struct net_device`、`struct request_queue` 等关键结构。

## 刷机

```sh
adb reboot bootloader
fastboot flash boot_a boot_272_epoll.img
fastboot reboot
```

刷前确认 `boot_backup_pre_epoll.img` 存在（192MB）。回退：

```sh
fastboot flash boot_a boot_backup_pre_epoll.img
```

`uname` 里的时间来自 HEAD 提交时间，同一提交下多次构建看起来一样，不能用来区分构建。

## 运行时设置

两个 KernelSU 模块：

| 模块 | 作用 |
| --- | --- |
| `ntsync` | 开机创建 `/dev/ntsync`（字符设备 10:127） |
| `sysctl-tune` | 提高 Wine/容器相关限制 |

`sysctl-tune` 设置的值：

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
grep __arm64_sys_epoll_pwait2 /proc/kallsyms
cat /sys/block/zram0/comp_algorithm
cat /sys/block/zram0/disksize
cat /proc/sys/net/ipv4/tcp_congestion_control
grep -H . /sys/block/sda/queue/scheduler
```

## 补丁

`patches/` 放的是本项目相对 5.10.272 的全部改动，不包含 AOSP 历史。

- 基线：`a1eed2e9c`（`Merge 5.10.272 into android12-5.10-lts`）
- 顺序：`patches/series`
- 分类：`00-platform`、`01-container`、`02-wine`、`03-memory`、`04-security`、`05-storage`、`06-network`、`07-block`、`08-syscalls`、`09-docs`
- 索引：`patches/README.md`

应用方式：

```sh
git checkout a1eed2e9c
while read p; do git am "patches/$p"; done < patches/series
```

`patches/` 目录本身不在补丁里；应用完 series 后的代码树应与当前提交前的源码树一致。

## 已知限制

- **ADIOS 不是实际磁盘调度器**：vendor 的 `init.qti.kernel.rc` 会在开机后把 sda–sdh/mmcblk 写成 BFQ（smartfocusio 开启时 sda 写 cpq）。只有未被覆盖的队列保持 `[adios]`。要强制切换需要额外的开机脚本。
- **futex_waitv 只有 64 位**：arm64 compat 表没有接线，32 位进程仍返回 ENOSYS。
- **KSM 默认关闭**：`/sys/kernel/mm/ksm/run=0`；按进程 KSM 尚未实现。
- **`tcp_plb_enabled=0`**：PLB 是数据中心 IPv6 多路径优化，手机网络没有收益。
- **`CONFIG_MODULE_SIG=n`**：本地 zram 配方的取舍。
- **`lz4` 会写成 `lz4kd`**：驱动做了映射；要临时回 lz4 请刷回退镜像。
- **未全局开启 overlayfs metacopy/index**：这两个开关会改默认行为，metacopy 还会连带 redirect_dir。
- **未启用**：CFS_BANDWIDTH（实测无法开机）、HUGETLB/CGROUP_HUGETLB、AppArmor、MGLRU。
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

## License

内核代码遵循 GPL-2.0，与上游一致。
