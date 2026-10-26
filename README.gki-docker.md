# GKI 5.10.272 Docker 支持（Xiaomi Pad 6 Max / yudi）

在 AOSP android12-5.10-lts 5.10.272 基础上，为小米平板 6 Max（yudi）启用宿主机原生
Docker 所需的内核特性，同时保持 vendor_boot 中 355 个厂商模块的 KMI/CRC 兼容。

- 分支：`gki-docker-phase2`（本地，未推送）
- 设备实测内核：`5.10.272-android12-9-geba364b9a173-dirty`（含 futex_waitv、epoll_pwait2；KernelSU LKM 正常）
- 最终镜像：`work/boot_272_epoll.img`（PC 侧 `C:\Users\OneFeiFan\boot_272_epoll.img`）
- 回退镜像：`C:\Users\OneFeiFan\boot_backup_pre_epoll.img`（含 futex_waitv，无 epoll_pwait2）

## 提交列表

| 提交 | 内容 |
|---|---|
| `cf9e01256` | cgroup devices/pids/net_cls，MAIN/EXT 拆分 |
| `39fd319eb` | CGROUP_PERF，perf_event cgrp 拆分 |
| `179863749` | nftables，`struct net` 空洞放置 |
| `ef0df4f22` | 桥接 netfilter + IPv6 NAT |
| `3655f7c25` | IPVS + SCTP，动态 netns |
| `0864bc626` | 隧道/VLAN/IPVLAN/tc，net_device 保留位 |
| `764e61cf9` | 块层限速、cgroup 分类器、checkpoint、Btrfs |
| `5e37c795c` | NTSync（Wine/Proton） |
| `d65fc915b` | le9uo 工作集保护 |
| `e7b167847` | dcache/overlayfs/nfnetlink_log/cpuset 安全补丁 |
| `8f015b6ca` | zram 内建 + LZ4K/LZ4KD + ARM64 NEON |
| `dbdc674ae` | vendor lz4 → lz4kd 映射 |
| `eb4f940a0` | BBRv1/KSM/tmpfs 配置 |
| `42ebf3a81` | BBRv3 + TCP PLB |
| `62cec6795` | BBRv3 默认拥塞控制 |
| `8a84344a2` | ADIOS I/O 调度器（可用，默认不变） |
| `ebf8ed4fc` | blk-mq 在 `limit_depth` 前设置 hctx（ADIOS 默认崩溃根因修复） |
| `720aeb68a` | ADIOS 设为内核默认调度器（依赖上一行修复） |
| `e970ecb92` | futex_waitv 系统调用回移（Wine/Proton） |
| `78b90ee4a` | epoll_pwait2 系统调用回移（纳秒超时） |

## 已启用功能

- NTSync：`/dev/ntsync`（KernelSU 模块 `ntsync` 开机创建，`/proc/misc` 127），Wine 10.15+/Proton
- futex_waitv：系统调用 449（Wine/Proton 多对象等待）；仅 64 位 ABI，32 位调用仍返回 ENOSYS
- epoll_pwait2：系统调用 441，纳秒级超时；64 位与 32 位 compat 都已接
- le9uo：`vm.workingset_protection=1`，`anon_min_ratio=15`、`clean_min_ratio=15`
- zram：内核内建（`ZRAM=y`/`ZSMALLOC=y`），默认 `lz4kd`；算法列表含 `lz4hc lz4k lz4k_oplus lz4kd`，带 `lz4armv8` NEON
- 安全：dcache、overlayfs、nfnetlink_log、cpuset 四个容器相关补丁
- BBRv1：`tcp_available_congestion_control` 含 bbr；默认仍 cubic，可 `sysctl -w net.ipv4.tcp_congestion_control=bbr`
- KSM：`/sys/kernel/mm/ksm` 存在，默认 `run=0`（需手动开）
- TMPFS_XATTR / TMPFS_POSIX_ACL：已启用
- BBRv3：`tcp_available_congestion_control` 含 `bbr3`，可 `sysctl -w net.ipv4.tcp_congestion_control=bbr3`；`tcp_plb_*` sysctl 存在（`tcp_plb_enabled` 默认 0）
- 默认拥塞控制：BBRv3（开机 `tcp_congestion_control` 即 `bbr3`；cubic 仍可选）
- ADIOS：内核默认调度器（`MQ_ADIOS_DEFAULT=y`）；`/sys/block/*/queue/scheduler` 列表含 `adios`。注意 vendor 的 `init.qti.kernel.rc` 会在开机后把 sda–sdh/mmcblk 改回 bfq（smartfocusio 开启时 sda 改 cpq），所以磁盘实际仍显示 cpq/bfq；未被 vendor 覆盖的队列（如 loop、mtdblock）显示 `[adios]`
- cgroup：devices、pids、perf_event、net_cls（cgroup v1/v2 均可）
- netfilter：nftables 全家、桥接 netfilter、IPv6 NAT
- 网络：IPVS 全家、SCTP、VXLAN、VLAN、IPVLAN、MACVLAN、L2TP、FOU、GRE、tc
- 块层：BLK_DEV_THROTTLING
- 其他：CHECKPOINT_RESTORE、BTRFS_FS(+ACL)、NET_CLS_CGROUP

## ABI 策略

硬门禁：全量 7298 个符号 CRC 与基线 diff=0；355 个厂商模块 0 失败。

要点：genksyms 会递归展开指针可达的结构定义，因此任何条件字段只要出现在
genksyms 可见的文本里，就可能带偏整片符号的 CRC。所有新增条件字段都用
`!defined(__GENKSYMS__)` 隐藏，必要时叠到 KABI reserve 或天然空洞：

- cgroup：控制器 MAIN/EXT 拆分，ext 指针放 `struct cgroup/css_set` 空洞
- `struct net`：nft@664、ipvs@680、sctp_ext@688
- `struct netns_nf`：hooks_bridge 指针放 KABI reserve
- `struct net_device`：l3mdev_ops / vlan_info 叠 reserve 1/2
- `struct netns_ipv4`：三个 l3mdev sysctl 放 tcp_death_row 前的 32 字节空洞
- `struct request_queue`：throtl_data 叠 reserve 1
- `struct perf_event`：cgrp 拆高低 32 位放空洞
- `struct ipc_ids`：next_id、sched cfs 字段对 genksyms 隐藏


## 阶段 10：NTSync / le9uo / 安全 / zram

- **NTSync**（`5e37c795c`）：上游 6.14 驱动，内置 `CONFIG_NTSYNC=y`；5.10 用驱动内 lockdep shim，不改内核 lockdep；去掉社区版的 `gpu_device` SELinux hack。`/dev/ntsync` 由 KernelSU 模块创建。
- **le9uo**（`d65fc915b`）：android12-5.10 回移，默认开启；内存压力时保护 15% 匿名页 + 15% 干净文件页。可 `sysctl -w vm.workingset_protection=0` 关闭。
- **安全**（`e7b167847`）：dcache `cant_mount`、overlayfs `copy_file_range` 源 creds、nfnetlink_log `.pre_exit`、cpuset v2 mode 缓存；overlayfs 额外包含 `../internal.h`（5.10 的 `rw_verify_area` 声明位置）。CVE-2026-43499/53163 已在 5.10.272 基线内。
- **zram**（`8f015b6ca` + `dbdc674ae`）：zram/zsmalloc 内建，LZ4K/LZ4KD 后端和 lz4armv8 NEON；vendor 脚本写死 `lz4`，驱动在 `comp_algorithm_store()` 里映射为 `lz4kd`。当前 zram0 16GB、`[lz4kd]`。
- **10.5 配置包**（`eb4f940a0`）：开启 BBRv1（默认 cubic，可 sysctl 切 bbr）、KSM（默认不运行）、TMPFS_XATTR/ACL；关闭 BIC/WESTWOOD/HTCP 模块以保持 GKI 模块清单一致。
- **注意**：本阶段配置了 `CONFIG_MODULE_SIG=n`（本地 zram 配方的取舍）；写 `lz4` 也会被映射为 `lz4kd`，要临时回 lz4 请刷 `boot_backup_pre_adios_safe.img`。
- 零宽字符内核补丁未采用（上游 CVE-2024-50089 已 revert，修在 Android 用户态 FuseFixer）；MGLRU 在 5.10 无现成回移；overlay2-on-f2fs 用 `--rootfs-img` 稀疏 ext4 容器，不改内核。

- **10.6 BBRv3**（`42ebf3a81`）：WildKernels android12-5.10 BBRv3 + TCP PLB；`tcp_sock` 复用 `unused:5` 位并用 `__GENKSYMS__` 隐藏，`struct bbr` 私有状态；手动适配 5.10.272 的 `sysctl_net_ipv4.c` 和 `tcp_ack` TLP 调用。默认仍 cubic，可切 bbr3；`tcp_plb_enabled` 默认 0。

- **10.7 BBRv3 默认**（`62cec6795`）：`DEFAULT_BBR3=y`，开机 `tcp_congestion_control` 直接是 `bbr3`；cubic 仍保留，可随时切回。

- **10.8 ADIOS**（`8a84344a2`）：ESK 5.10 `block/adios.c`，只注册 `MQ_IOSCHED_ADIOS`，不设默认。实测 `adios` 出现在列表，手动切 `sda` 成功，16MB dd 2.2GB/s；默认仍是 cpq/bfq。
- **10.9 ADIOS 默认崩溃根因修复**（`ebf8ed4fc`）：`adios_limit_depth()` 经 `to_word_depth()` 读 `data->hctx->sched_tags->bitmap_tags`，而原生 5.10 的 `__blk_mq_alloc_request()` 是先调 `limit_depth()`、后给 `data->ctx/data->hctx` 赋值，所以设成默认后开机首轮 I/O 就空指针，卡第一屏。ESK 的 `block/blk-mq.c` 把 `retry:` 与 hctx 赋值整体提前，并把 `if (!e)` 改成 `else`；本版照搬这 27 行改动。修复后实测：开机正常，`sda` 可切 `[adios]`，1GB 写入 782MB/s，无 Oops；随后在 10.10 设为默认并复测通过。
- **10.10 ADIOS 设为默认**（`720aeb68a`）：`MQ_ADIOS_DEFAULT=y`，`elevator_init_mq()` 优先取 `adios`，失败再回退原有默认。实测开机正常、1GB 写入 813MB/s、无 Oops。发现 vendor 的 `/vendor/etc/init/hw/init.qti.kernel.rc` 会在开机后把 sda–sdh/mmcblk 写成 bfq（`persist.sys.stability.smartfocusio=on` 时 sda 写 cpq），因此磁盘实际仍是 cpq/bfq，只有未被覆盖的 loop45、mtdblock0 等队列保持 `[adios]`。要让磁盘真正用上 ADIOS，需要额外的开机后脚本覆盖 vendor 设置。
- **10.11 futex_waitv**（`e970ecb92`）：照上游 5.16 接口回移，系统调用号 449；5.10 没有 `futex_init_timeout()`，绝对超时的换算直接写在 syscall 里。android12-5.10 已经把 futex 拆到 `kernel/futex/core.c`，所以代码直接接在 `get_robust_list` 之后。实测：`nr=0`→EINVAL、值不匹配→EAGAIN、值匹配但超时已过→ETIMEDOUT。仅接 64 位 ABI。
- **10.12 epoll_pwait2**（`78b90ee4a`）：5.11 接口，系统调用号 441；先把 epoll 内部超时改成 `timespec64`，再加 syscall。64 位 arm64 和 32 位 compat 都已接。实测：零超时返回 0、非法 `tv_nsec` 返回 EINVAL、1ms 超时正常到期、`maxevents=0` 返回 EINVAL；futex_waitv 回归测试仍通过。

## 构建与校验

```sh
cd ~/kernel-sources/vanilla-root
SKIP_MRPROPER=1 SKIP_CP_KERNEL_HDR=1 \
BUILD_CONFIG=common/build.config.gki.aarch64 \
OUT_DIR=~/kernel-sources/out-p2 bash build/build.sh -j12
```

构建后跑四项门禁：

1. 配置核对：`out-p2/common/.config`
2. 全量符号：`out-final/dist/vmlinux.symvers` 对比 `out-p2/dist/vmlinux.symvers`
   （7298 个基线符号缺失 0、CRC 差异 0）
3. 厂商模块：`python3 tools/crc_scan.py out-p2/dist/vmlinux.symvers work/vendor_boot/root`
   （355 模块 0 失败）
4. 布局：pahole 核对 `struct net` 4672、`net_device` 2496、`request_queue` 2096 等

镜像重打包：`python3 tools/bootimg_repack.py work/boot_272_ksu.img work/ksu_x/ramdisk <out.img> out-p2/dist/Image`

## 刷机与回退

```sh
adb reboot bootloader
fastboot flash boot_a boot_272_epoll.img
fastboot reboot
```

刷前确认 `boot_backup_pre_epoll.img` 存在（192MB）。回退：

```sh
fastboot flash boot_a boot_backup_pre_epoll.img
```

注意：`uname` 里的时间是 HEAD 提交时间（KBUILD_BUILD_TIMESTAMP），同一提交下
多次构建看起来相同，不能用来区分构建。

## 设备自查（Termux）

Termux 已安装，检查脚本与配置已放在：

- Termux 家目录：`~/docker-check-plain.sh`、`~/config-final`
- `/sdcard/Download/`：官方脚本、plain 副本、压缩/未压缩配置

```sh
NO_COLOR=1 sh ~/docker-check-plain.sh ~/config-final
```

官方原版脚本用 `~/docker-check-config.sh ~/config-final.gz`（需要 gzip）。


阶段 10 后的补充自查：

```sh
cat /proc/misc | grep ntsync
head -c 0 /dev/ntsync && echo ntsync_ok
grep __arm64_sys_futex_waitv /proc/kallsyms     # futex_waitv 已接入
grep __arm64_sys_epoll_pwait2 /proc/kallsyms    # epoll_pwait2 已接入
cat /sys/block/zram0/comp_algorithm      # 期望行尾 [lz4kd]
cat /sys/block/zram0/disksize            # 17179869184
cat /proc/sys/vm/workingset_protection /proc/sys/vm/anon_min_ratio /proc/sys/vm/clean_min_ratio
cat /proc/sys/net/ipv4/tcp_available_congestion_control  # 期望含 bbr bbr3
cat /proc/sys/net/ipv4/tcp_congestion_control   # 默认 bbr3
grep -H . /sys/block/sda/queue/scheduler          # 列表应含 adios（实际选中项会被 vendor init 改成 cpq/bfq）
# 手动切换（需 root，必要时临时 permissive）：
# setenforce 0; echo adios > /sys/block/sda/queue/scheduler; setenforce 1
cat /sys/kernel/mm/ksm/run                     # 默认 0
```

## check-config 结果与已知缺口

仍需注意的项（与参考项目 fulldocker 对比）：

| 项 | 说明 | 参考项目 |
|---|---|---|
| cpu/cpuset/io/memory 显示 missing | 脚本只查 cgroup v2 的 `cgroup.controllers`；Android 把 cpu/cpuset/memory/blkio 挂在 `/dev/*`（v1），内核控制器本身都已启用 | 同样不处理，属误报 |
| CGROUP_HUGETLB | 需要 HUGETLB_PAGE；只影响 `--hugetlb-*` 限额 | 未启用（defconfig 0 命中） |
| CFS_BANDWIDTH | 只影响 `--cpus` 硬配额。实测单独启用即无法开机（禁 cpu 控制器、单核均无效）；已暂缓 | 未启用（0 命中） |
| SECURITY_APPARMOR | Android 使用 SELinux | 未启用（0 命中） |
| 3 个 forwarding sysctl | 运行时设置，不是编译项 | 不涉及 |

结论：参考项目对上述 10 项同样没有处理；其中只有 CGROUP_HUGETLB、CFS_BANDWIDTH、
AppArmor 是真正的内核配置项，参考项目全部未开启。按用户决定"例子没开的不再开"，
本仓库维持现状。阶段 9 部署 dockerd 时再打开 IPv4/IPv6 forwarding。

## 参考

- 参考项目：`~/kernel-sources/refs/kernel-workshop-docker`（fulldocker/superkernel.diff）
- 规划与流水账：`~/kernel-dev/.claude/plans/gki-docker/{task_plan,findings,progress}.md`
- 校验工具：`~/kernel-sources/tools/{crc_scan.py,bootimg_repack.py,gencrc.sh}`
