# 内核补丁

基线是 AOSP `android12-5.10-lts` 的 `8059ae219630`（2026-10-24）。按 `series` 顺序应用（通用系列，26 个）后得到的内核源码树（不含本目录）：

```
862d916248ae64f3b5c392aea6f5e5355e9eb8d0
```

按 `series.xiaomi` 应用（通用系列 26 个 + 小米组 3 个）后，也就是 yudi 实际构建和仓库 `source/` 的树：

```
2afd8cc80fffd02546bc3e5532fc5707db80be25
```

## 应用

```sh
cd common
git checkout 8059ae219630
PATCHES=/path/to/gki-yudi/patches
while read p; do git am "$PATCHES/$p"; done < "$PATCHES/series.xiaomi"   # 非小米设备用 series
```

只查看 diff、不建提交时，把 `git am` 换成 `git apply`。

## 组织原则

- 按子系统分目录，编号按目录顺序连续排列；`series` 就是目录顺序。
- 每个功能补丁自带它需要的 `gki_defconfig` 选项，放在**自己的原厂锚点行之后**，以 `# yudi:` 注释开头。各补丁的锚点互不相邻，所以配置不再把补丁串在一起；0001 关闭 `check_defconfig`，因为选项不再是 savedefconfig 的顺序。
- 任意一个补丁都可以单独去掉，后面的补丁照样能打上，只有下面三处真实的代码依赖例外（已逐个做过"去掉一个、打其余 25 个"的验证）：

| 补丁 | 依赖 | 原因 |
| --- | --- | --- |
| 0009 futex_waitv | 0008 epoll_pwait2 | 共享系统调用表 |
| 0020 BBRv3 | 0019 PLB | `include/net/tcp.h` |
| 0025 zstd | 0015 LZ4K/LZ4KD | `lib/Kconfig` |

- 除上面三对外，还有几组补丁改了同一文件的不同位置，彼此不冲突：0011/0012（`mm/vmscan.c`、`mm/page_alloc.c`）、0014/0025（f2fs、incfs 调用点）、0018 到 0020（TCP）。
- 补丁头部的 `Origin`、`Upstream-Status`、`KABI`、`Depends-On`、`Notes`、`Tested-On` 给出处、KABI 占用、与来源的差异和验证范围；找不到来源的明确写"本地实现"。
- **zram 内建**：0016 把 zram、zsmalloc、LZO 编进内核并接上 LZ4K/LZ4KD（0015 启用这些算法），
  厂商的 zram.ko / zsmalloc.ko 被内建屏蔽名单跳过；zram 驱动由本仓库维护。0017 打开上游的
  `ZRAM_WRITEBACK`。
- **小米组**：`xiaomi/` 下的补丁只用于小米设备，排在通用系列之后（见 `series.xiaomi`）。
  0027 把 zram 升级为小米 ExtM 实现，0028 加上内存冻结（mfz）写回策略；来源都是小米官方开源
  内核，不依赖任何第三方内核。
- 0005 的 `NET_CLS_CGROUP` 依赖 0004 的 `CGROUP_NET_CLASSID`；去掉 0004 时 Kconfig 会自动丢掉它。

## 补丁列表

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0001 | `00-platform/0001-build-thinlto-defconfig-check.patch` | ThinLTO；关闭 `check_defconfig` |
| 0002 | `00-platform/0002-platform-task-user-abi.patch` | task_struct/user_struct 的 KABI 占位；PID_NS、SYSVIPC、POSIX_MQUEUE、IPC_NS、USER_NS、DEVTMPFS |
| 0003 | `00-platform/0003-gki-defconfig-config-only-extras.patch` | 只改配置：KSM、tmpfs xattr/ACL、Btrfs |
| 0004 | `01-container/0004-cgroup-devices-pids-net-cls-perf.patch` | cgroup MAIN/EXT 拆分；devices、pids、perf、net_cls |
| 0005 | `01-container/0005-container-networking.patch` | 容器网络，含 netns_ipv4 的 l3mdev 布局和断言；nftables、bridge netfilter、IPv6 NAT、IPVS/SCTP、隧道、虚拟网卡、tc |
| 0006 | `01-container/0006-block-throttling-abireserve.patch` | blk-throttle 状态放进 KABI 预留位（本地实现，无外部出处）；BLK_DEV_THROTTLING |
| 0007 | `01-container/0007-checkpoint-restore-ipc-next-id.patch` | ipc next_id 放进 side table（本地实现，无外部出处）；CHECKPOINT_RESTORE、UNIX/PACKET/NETLINK_DIAG、FHANDLE |
| 0008 | `02-wine/0008-epoll-pwait2.patch` | epoll_pwait2 回移（上游提交 7cdf7c20e971 等） |
| 0009 | `02-wine/0009-futex-waitv.patch` | futex_waitv（64/32 位）回移；更新 syscall 表，`__NR_syscalls` 到 450 |
| 0010 | `02-wine/0010-ntsync.patch` | NTSync 驱动；NTSYNC |
| 0011 | `03-memory/0011-le9uo.patch` | le9uo 工作集保护 |
| 0012 | `03-memory/0012-kcompressd.patch` | Kcompressd：kswapd 把匿名 zram 页交给 per-node 线程异步压缩；状态放独立数组，`pglist_data` 不动 |
| 0013 | `04-security/0013-container-security-fixes.patch` | 四个上游修复回移（CVE-2026-98984 / 68448 / 98972 / 93288）；nfnetlink_log 修复含 5.10 各日志器的 pre_exit 部分 |
| 0014 | `05-storage/0014-lz4-armv8.patch` | lib/lz4 更新到带 ARM64 NEON 的版本；crypto、f2fs、incfs 调用点适配 |
| 0015 | `05-storage/0015-lz4k-lz4kd-codecs.patch` | LZ4K、LZ4K-oplus、LZ4KD 编解码器与 crypto 封装；连同 LZ4HC、842 作为内建压缩算法 |
| 0016 | `05-storage/0016-zram-builtin-lz4k-lz4kd.patch` | 内建 zram、zsmalloc、LZO；zram 接线（算法列表、`ZRAM_DEF_COMP`）；内建模块屏蔽名单（`module_blacklist=` 返回 `-EPERM`，内建影子跳过返回 0） |
| 0017 | `05-storage/0017-zram-writeback.patch` | `ZRAM_WRITEBACK`（上游写回；小米 PerfInit 用它挂 ExtM 写回设备） |
| 0018 | `06-network/0018-tcp-rate-bbrv3-infra.patch` | BBRv3 依赖的 TCP 基建：rate sample、32 位时间戳、TLP、CE 事件、`tcp_snd_cwnd` |
| 0019 | `06-network/0019-tcp-plb.patch` | PLB 核心、per-net sysctl、ECN_LOW |
| 0020 | `06-network/0020-tcp-bbr3.patch` | BBRv3 主体、inet_diag 统计、Kconfig |
| 0021 | `06-network/0021-tcp-enable-bbrv3.patch` | gki_defconfig 打开 TCP_CONG_ADVANCED、BBR、BBR3（默认仍是 cubic） |
| 0022 | `07-block/0022-blk-mq-limit-depth.patch` | blk-mq：在 `limit_depth` 前设置 ctx/hctx（上游 6259151c04d4，ADIOS 的前置） |
| 0023 | `07-block/0023-adios.patch` | ADIOS 3.2.0 调度器；MQ_IOSCHED_ADIOS（默认调度器不变） |
| 0024 | `08-power/0024-wq-power-efficient-default.patch` | 默认启用 power-efficient unbound workqueues（灰度实验） |
| 0025 | `09-lib/0025-zstd-1.5.7.patch` | zstd 升级到 1.5.7；lib/zstd 换成 common/compress/decompress 布局，crypto/f2fs/btrfs/squashfs/incfs/pstore/unzstd 切到新 API；新增 ZSTD_COMMON |
| 0026 | `10-sched/0026-cfs-bandwidth-kabi.patch` | CFS 带宽 kABI 拆分；CFS_BANDWIDTH |

## 小米组

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0027 | `xiaomi/0027-zram-xiaomi-extm.patch` | zram 升级为小米 ExtM 实现：分批写回（`idle <wb_max> <wb_idle_min>`）、按时间老化（`time_list`、`idle_stat`）、低压缩率优先写回（`low_compress_ratio`）、页面寿命与大小统计（`pages_life`、`avg_size`、`new`、`new_stat`、`origin_pages_max`、`wb_pages_max`）、SIGUSR1 中止写回；`MIUI_ZRAM_MEMORY_TRACKING` |
| 0028 | `xiaomi/0028-zram-xiaomi-memory-freeze.patch` | 内存冻结（mfz）写回策略：页面进入 zram 时按所属 memcg 打标（`freeze-app` 组 → 不限额写回）；`mfz_enable`、`mfz_disk_quota`（为冻结应用预留写回空间）、`mfz_compr_data_size`、`mfz_idle_stat`；`bd_stat` 多三列；memcg 文件 `anno_writeback_enable`（5.10 名）与 `anno_writeback_control`（6.6 名）；`MI_MEMORY_FREEZE` |
| 0029 | `xiaomi/0029-zram-memcg-anno-register.patch` | 修复 0027 带入的小米源码问题——memcg 文件注册：`cgroup_add_legacy_cftypes()` 原本在 `zram_init()` 的 `return 0` 之后，`memory.anno_writeback_*` 不会出现；把注册移到 return 之前。本地修复，依赖 0028 |

0027 的来源是 `MiCode/Xiaomi_Kernel_OpenSource` 的 `spinel-v-oss`（5.10.233，`49ff345d71ab`）。
它基于 ACK，已包含本仓库 5.10.272 zram 的全部 ACK 改动，因此直接取其 `zram_drv.c`/`zram_drv.h`，
再加回 0016 的默认算法配置；Kconfig 为三方合并。yudi 自己的开源分支 `yudi-t-oss`（5.10.160）
里的 zram 是原版，没有 ExtM。

0028 的来源是小米 6.6 源码 `bixi-v-oss`（`56295df675b9`）里 `CONFIG_MI_MEMORY_FREEZE` 那部分，移植到
0027 的 5.10 驱动上。memcg 标记用 ACK 5.10 已有的 `struct mem_cgroup::android_oem_data1`，不改结构体。
接口名和取值对照官方 yudi zram.ko：`anno_writeback_enable` 写非零即把该组标为内存冻结（取值 2），
`anno_writeback_protected` 标为受保护（取值 1）；另提供 6.6 的 `anno_writeback_control`，因为移植包的
`init.rc` 两套都会写。加上 0028 后，本仓库 zram 的 sysfs 接口与官方 yudi zram.ko 完全一致（30 个）。
0029 修复这组 memcg 文件的注册位置（问题出在小米 spinel 源码本身：`zram_init()` 把注册写在 `return 0` 之后，是永远执行不到的代码，0027 原样带入）：注册必须在 `zram_init()` 返回之前完成，否则
`/dev/memcg/freeze-app/memory.anno_writeback_enable` 等文件不会出现；zram sysfs 仍是 30 个。

仍然没有的：`writeback_quota`、`zgroup_enable`。名字来自移植包里的 PerfInit，任何公开源码和
现有 zram.ko 都没有实现；PerfInit 遇到缺少的接口只打日志、继续运行。

## 2026-10-31 第二次调整：zram 内建 + 小米组

同日曾把 zram 交还厂商模块（移植包里的 zram.ko 是第三方月亮内核的闭源构建），随后改为
自己维护：月亮内核已停更，闭源模块无法审查，且会把它自带的回收改动（异步 slab 回收）
一起带进来。最终方案：

- 0016、0017 回到通用系列（编号不变）；0015 负责启用压缩算法，0016 的配置块只含 zram、
  zsmalloc、LZO 和默认算法。
- 新增 `xiaomi/0027`（ExtM）、`xiaomi/0028`（内存冻结）和 `xiaomi/0029`（memcg 文件注册修复，本地）；0027/0028 来自小米官方源码；`series.xiaomi` = 通用系列 + 小米组。
- 本地验证：两个 series 都能完整打上，树哈希如上；单独打补丁和"去掉一个"测试只剩 0009→0008、
  0020→0019、0025→0015 三处依赖（0027 依赖 0016/0017 的配置，补丁本身可独立打上）；用
  clang 18.1.3 按 `gki_defconfig` 交叉编译 `drivers/block/zram`、`kernel/module.c`、
  `nf_log_ipv4`、`nf_log_ipv6` 通过（0027 为此把几个空参数列表补成 `(void)`）。

## 2026-10-31 整理记录

对照来源逐个核对后做了以下整理（审查报告见仓库外的文档）：

- **配置布局**：各补丁的 `gki_defconfig` 选项从"依次追加到文件末尾"改为"放在各自的原厂锚点行之后"。最终 `gki_defconfig` 的 866 个符号及取值与整理前逐一相同，只是行的位置和注释变了。
- **重新编号**：按目录顺序连续编号（旧编号 → 新编号见下表）。
- **来源更正**：0002（Droidspaces GKI 5.10 sysvipc/posix 补丁，KABI 为 USE(6)+REPLACE(7)(8)）、0009（上游 `bf69bad38cf6`）、0022（上游 `6259151c04d4`）、0023（ADIOS 3.2.0）、0026（移植自 Droidspaces cgroup_limits）；0014、0025 补全来源链。
- **补写差异说明**：0007 写明已含 CVE-2026-52923 修复；0010、0016、0020 写明与来源相比的有意改动。
- **补全依赖声明**：0009 → 0008，0025 → 0015。
- **代码归位**：BBRv3 的 `GSO_LEGACY_MAX_SIZE` 从 0005 移到 0020；最终 `netdevice.h` 不变。
- **补全安全修复**：0013 的 nfnetlink_log 修复补上上游 `nf_log_syslog.c` 那一半：5.10 的 `nf_log_ipv4`、`nf_log_ipv6`、`nf_log_netdev`、`nf_log_arp`、`nf_log_bridge` 的命名空间退出改为 `pre_exit`。这是本次唯一的代码行为变化，尚未实机验证。
- **格式**：每个补丁里同一文件只保留一段 diff（原 BBRv3 补丁是多个提交拼接的）。

| 旧编号 | 新编号 | 目录 |
| --- | --- | --- |
| 0022 | 0003 | `00-platform` |
| 0003 | 0004 | `01-container` |
| 0004 | 0005 | `01-container` |
| 0005 | 0006 | `01-container` |
| 0006 | 0007 | `01-container` |
| 0007 | 0008 | `02-wine` |
| 0008 | 0009 | `02-wine` |
| 0009 | 0010 | `02-wine` |
| 0010 | 0011 | `03-memory` |
| 0026 | 0012 | `03-memory` |
| 0011 | 0013 | `04-security` |
| 0012 | 0014 | `05-storage` |
| 0013 | 0015 | `05-storage` |
| 0014 | 0016 | `05-storage` |
| 0024 | 0017 | `05-storage` |
| 0015 | 0018 | `06-network` |
| 0016 | 0019 | `06-network` |
| 0017 | 0020 | `06-network` |
| 0018 | 0021 | `06-network` |
| 0019 | 0022 | `07-block` |
| 0020 | 0023 | `07-block` |
| 0023 | 0024 | `08-power` |
| 0021 | 0026 | `10-sched` |
