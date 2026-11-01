# 内核补丁

基线是 AOSP `android12-5.10-lts` 的 `8059ae219630`（2026-10-24）。按 `series` 顺序应用（通用系列，99 个）后得到的内核源码树（不含本目录）：

```
8f65209be3a29dd83647ffbe0169846f83b55bdf
```

按 `series.xiaomi` 应用（通用系列 99 个 + 小米组 4 个，共 103 个）后，也就是 yudi 实际构建和仓库 `source/` 的树：

```
7f30604ddca6842e726ff79311ab966e901d2d17
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
- 任意一个补丁都可以单独去掉，后面的补丁照样能打上，只有下面七处真实的代码依赖例外（最初 26 个补丁逐个做过"去掉一个、打其余 25 个"的验证；后续补丁按需要单独验证）：

| 补丁 | 依赖 | 原因 |
| --- | --- | --- |
| 0009 futex_waitv | 0008 epoll_pwait2 | 共享系统调用表 |
| 0020 BBRv3 | 0019 PLB | `include/net/tcp.h` |
| 0025 zstd | 0015 LZ4K/LZ4KD | `lib/Kconfig` |
| 0058 sync_file ABI | 0057 sync_file | 同一结构体和调试名的改动 |
| 0074 sync_file 池 | 0073 dma_buf 池 | 共用 `init/main.c` 的声明/调用 |
| 0078 treewide clear_page | 0077 f2fs copy_page | f2fs `segment.c` 上下文基于 0077 |
| 0088 zero-sized extent | 0087 map next extent | 0088 依赖 0087 的映射修正 |

- 除上面七对外，还有几组补丁改了同一文件的不同位置，彼此不冲突：0011/0012（`mm/vmscan.c`、`mm/page_alloc.c`）、0014/0025（f2fs、incfs 调用点）、0018 到 0020（TCP）。
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
| 0030 | `xiaomi/0030-zram-mfz-enable-default.patch` | `mfz_enable` 默认值改为 1，与小米 6.6 源码和官方 yudi zram.ko 一致；PerfInit 只在 `persist.sys.mfz.enable` 为 false 时写 0 |

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

### PerfInit 反汇编结论（2026-10-31）

- `writeback_quota`：PerfInit 并不读写这个文件。它检查的是 `mfz_disk_quota`，检查失败时打印的
  日志文字写成了 "writeback_quota not exist"，是小米的日志笔误。不需要实现。
- `zgroup_enable`：是另一套内存扩展架构的开关（按 memcg 分组管理 zram 对象，加上 memcg 级的后台
  换出线程 xswapd）。文件存在时，PerfInit 会改走这条路：写 `zgroup_enable=1`、重置 zram、打开
  `/dev/memcg/memory.xswapd.enable` 和 `memory.xswapd.umrenable`；判断"是否支持 ExtM"时也把它
  和 `backing_dev` 并列。miui-services、libmmperf、MiuiMmTrace 也会检查它。没有任何公开源码，
  内核侧需要整套分组与 xswapd 机制，**不实现、也不能放空文件**，否则 PerfInit 会切到一个内核
  并不具备的模式。
- `mfz_enable`：PerfInit 只在 `persist.sys.mfz.enable` 为 false 时写 0，依赖驱动默认值为 1，
  由 0030 修正；`mfz_disk_quota` 由 PerfInit 写入（`persist.sys.mfz.disk_quota`，默认 2048 MB，
  即 524288 页）。

## r8 正确性修复（2026-10-31）

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0031 | `07-block/0031-adios-flush-fua.patch` | ADIOS：去掉错误的 `ELEVATOR_F_MQ_AWARE`；完成请求时跳过 flush/FUA（`op_is_flush`）。空指针检查原本已有。来源 Melt `c8e6f8db45`、`62c201a18f` |
| 0032 | `05-storage/0032-zram-zcomp-vmalloc.patch` | zram 压缩流缓冲区改为 `vzalloc(2 * PAGE_SIZE)` / `vfree`，不再要求 2 页物理连续；来源 Barry Song `d4b079aee4` |
| 0033 | `03-memory/0033-le9uo-oom-escape.patch` | le9uo 硬水位把所有 LRU 扫描目标归零时的 OOM 兜底；仅在全部为 0 时重新填充，保留 SCAN_ANON/SCAN_FILE 引导。来源 Templar `17ea8a084b`；本树只取兜底，`prepare_workingset_protection()` 已经在 `shrink_node_memcgs()` 前 |

## r9a 空闲调度与低风险修正（2026-10-31）

TEO 按 ztc1997 `android12-5.10-2025-09` 分支的真实顺序回移；文档漏掉的 5 个前置提交
（`49157e81`、`1231824f`、`5869618c`、`b1111788`、`5e566cb4`）已补上。menu 15 个补丁因
`2067fff7`、`51eed4f466` 在 5.10.272 上冲突未纳入；`e8e5bf0511`、`b879914536` 同样跳过。

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0034 | `11-cpuidle/0034-teo-negative-sleep-length.patch` | TEO：处理负的 sleep length；Rafael `721b103b3d` |
| 0035 | `11-cpuidle/0035-teo-short-idle-times.patch` | TEO：调整极短 idle 时间的处理；`49157e81` |
| 0036 | `11-cpuidle/0036-teo-cosmetic-update.patch` | TEO：`teo_update()` 格式整理；`1231824f` |
| 0037 | `11-cpuidle/0037-teo-cosmetic-select.patch` | TEO：`teo_select()` 格式整理；`5869618c` |
| 0038 | `11-cpuidle/0038-teo-main-selection.patch` | TEO：主 idle 状态选择逻辑重写；`a4ec792917` |
| 0039 | `11-cpuidle/0039-teo-rework-recent-values.patch` | TEO：最近 idle 时长数据处理重做；`e567a18b74` |
| 0040 | `11-cpuidle/0040-teo-remove-semicolon.patch` | TEO：去掉多余分号；`b1111788` |
| 0041 | `11-cpuidle/0041-teo-fix-alternative-lookup.patch` | TEO：修正备用状态查找；`b4d6a28454` |
| 0042 | `11-cpuidle/0042-teo-rename-locals.patch` | TEO：重命名局部变量；`5e566cb4` |
| 0043 | `11-cpuidle/0043-teo-avoid-stop-tick.patch` | TEO：bail out 时避免不必要地停 tick；`a371bde465` |
| 0044 | `11-cpuidle/0044-teo-no-upfront-sleep-length.patch` | TEO：不提前调用 `tick_nohz_get_sleep_length()`；`7b03a8c807` |
| 0045 | `11-cpuidle/0045-teo-skip-sleep-length.patch` | TEO：部分情况跳过 sleep length 调用；`56d0909e92` |
| 0046 | `11-cpuidle/0046-teo-gather-tick-stats.patch` | TEO：统计是否值得停 tick；`43cd951e48` |
| 0047 | `11-cpuidle/0047-teo-avoid-assignments.patch` | TEO：去掉不必要的变量赋值；`4f228f5052` |
| 0048 | `11-cpuidle/0048-teo-remove-intercepts.patch` | TEO：移除 recent intercepts 指标；`7e56ccea53` |
| 0049 | `11-cpuidle/0049-teo-nonexistent-intercepts.patch` | TEO：不统计不存在的 intercepts；`fcd47e391f` |
| 0050 | `11-cpuidle/0050-idle-entry-return.patch` | 不在 `__CPU_PM_CPU_IDLE_ENTER()` 内部返回；`1ebbdf5c22` |
| 0051 | `11-cpuidle/0051-idle-entry-need-resched.patch` | `need_resched()` 时拒绝进入 idle；`1d2ce9dee1` |
| 0052 | `08-power/0052-suspend-cpuidle.patch` | 进入 suspend 时不再关闭 cpuidle；Tim Murray `571508da07` |
| 0053 | `06-network/0053-tcp-cubic-hystart-round.patch` | tcp_cubic：修正 HyStart 轮次起点判断；`cb630ba21a` |
| 0054 | `06-network/0054-tcp-cubic-bigtcp.patch` | tcp_cubic：`hystart_ack_delay()` 适配 BIG TCP；`151d4c4a07` |
| 0055 | `10-sched/0055-sched-idle-barrier.patch` | sched/idle：去掉多余的 memory barrier；`37bf036f4e` |
| 0056 | `08-power/0056-s2idle-wakeup.patch` | s2idle：避免过多唤醒尝试；`4b81b6afa1` |

## r10 第四批 4a（2026-10-31）

RCU `synchronize_rcu()` 延迟、长按电源键同步文件系统，以及 Sultan 的小优化。

RCU lazy 完整回移未纳入：文档只给了完整系列之后的 FIXUP `1673709568`，5.10.272
没有完整系列，单独打不上。selinux `167a6e942b` 在 `services.c:1532` 冲突，跳过。

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0057 | `12-misc/0057-sync-file-speed.patch` | dma-buf/sync_file：省略调试名，减少 ioctl 分配；Sultan `3404b28a50` |
| 0058 | `12-misc/0058-sync-file-abi.patch` | 修复 sync_file.h 的 ABI 破坏；Sultan `655e1a2589`，必须和 0057 一起 |
| 0059 | `12-misc/0059-kernfs-small-buffers.patch` | kernfs：小 write_iter 缓冲区避免动态分配；Sultan `c4ea3b34cb` |
| 0060 | `12-misc/0060-selinux-initcontextlen.patch` | selinux：INITCONTEXTLEN 小缓冲区避免动态分配；Sultan `4a40f8f05e` |
| 0061 | `12-misc/0061-bpf-small-buffers.patch` | bpf：map key/value 小缓冲区避免分配；Sultan `8f47a059db` |
| 0062 | `12-misc/0062-mbcache-fast-create.patch` | mbcache：加快 cache entry 创建；Sultan `6f0350a995` |
| 0063 | `12-misc/0063-binder-debug-prints.patch` | binder：默认去掉 debug 打印；Sultan `c038e12686` |
| 0064 | `12-misc/0064-uid-sys-stats-rtmutex.patch` | uid_sys_stats：uid_lock 从自旋锁改 rt_mutex；Sultan `320395e336` |
| 0065 | `12-misc/0065-kallsyms-lookup-speed.patch` | kallsyms：提升 kallsyms_lookup_name 性能；Sultan `d55ac0118e` |
| 0066 | `12-misc/0066-sched-calc-delta.patch` | sched：优化 __calc_delta()；Sultan `9e308a4815` |
| 0067 | `12-misc/0067-sched-fair-numa-disabled.patch` | sched/fair：关闭 NUMA 时编译掉 NUMA 代码；Sultan `ec63caab81` |
| 0068 | `12-misc/0068-pwrkey-sync-driver.patch` | 长按电源键触发文件系统同步的软件驱动；Juhyung Park `411bb710ce` |
| 0069 | `12-misc/0069-rcu-sync-latency.patch` | RCU：GP kthread 的 CPU 提前报告 QS，缩短 synchronize_rcu()；Joel Fernandes `43de808766` |
| 0070 | `12-misc/0070-enable-pwrkey-sync.patch` | GKI defconfig 启用 `CONFIG_INPUT_PWRKEY_SYNC=y`；本地配置 |

## r11 第四批 4b（2026-10-31）

9 个 kmem_cache 池/整页复制补丁，来源为 ESK 与 ztc 分支；两个适配版只改上下文，
不改逻辑。9 个补丁都不新增/删除导出符号、不改结构体布局。

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0071 | `13-kmem/0071-kernfs-kmem-pool.patch` | kernfs：`kernfs_open_node/file` 用 kmem_cache 池；ESK `f94ca8cb99`，适配 `kernfs_node` 上下文 |
| 0072 | `13-kmem/0072-cgroup-cset-link-pool.patch` | cgroup：`cgrp_cset_link` 用 kmem_cache 池；ESK `3f79c60d4c` |
| 0073 | `13-kmem/0073-dmabuf-attachment-pool.patch` | dma-buf：`dma_buf_attachment` 用 kmem_cache 池；ESK `aaa5047b59` |
| 0074 | `13-kmem/0074-sync-file-pool.patch` | dma-buf：`sync_file` 用 kmem_cache 池；ESK `01fc461c35`，适配 init/main.c |
| 0075 | `13-kmem/0075-zram-copy-page.patch` | zram：满页 `memcpy` 改 `copy_page`；ztc `2e68e9f9d8` |
| 0076 | `13-kmem/0076-zsmalloc-copy-page.patch` | zsmalloc：满页 `memcpy` 改 `copy_page`；ztc `30c861f9c1` |
| 0077 | `13-kmem/0077-f2fs-copy-page.patch` | f2fs：满页 `memcpy` 改 `copy_page`；ztc `a005e0a2eb` |
| 0078 | `13-kmem/0078-treewide-clear-page.patch` | treewide：整页 memset 改 clear_page；ztc `5078276692` |
| 0079 | `13-kmem/0079-arm64-clear-page-align.patch` | arm64：clear_page 16 字节对齐；ztc `95018d48f0` |

zram 只改 `__zram_bvec_read()` 的满页分支；mfz 回写走 `read_from_bdev()`，不经过该分支。
KMI/ABI 以标准构建的 symvers/CRC 门禁为准。

## r12 第四批 4d（2026-10-31）

10 个 f2fs 修正；`0087` 在本地补了 `is_hole` 变量（本树缺少上游的该前置重构），
`0089` 补了 `include/linux/f2fs_fs.h` 的 `F2FS_BLK_END_BYTES` 宏（5.10.272 缺少）。
原第 11 个 dnode 补丁未纳入：本树已有同类检查，直接打会产生重复块并引用缺失的
`f2fs_err_ratelimited`；原始补丁保留在 `refs-4d-2026-10-31/`。
不动导出符号和磁盘格式头。

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0080 | `14-f2fs/0080-f2fs-file-offset-overflow.patch` | 文件偏移整数溢出防护；`1b8085235fe9` |
| 0081 | `14-f2fs/0081-f2fs-node-info-flags.patch` | node info flags 总是初始化；`87c2b83fe0a0` |
| 0082 | `14-f2fs/0082-f2fs-gc-victim-segno.patch` | FG_GC ioctl 标记受害段；`0bdfa4232315` |
| 0083 | `14-f2fs/0083-f2fs-negative-nlink.patch` | 损坏镜像负 i_nlink 防 warning；`1f6332872374` |
| 0084 | `14-f2fs/0084-f2fs-sync-node-pages-error.patch` | `f2fs_sync_node_pages()` 返回正确错误号；`d94445903c9b` |
| 0085 | `14-f2fs/0085-f2fs-ino-xnid-sanity.patch` | ino/xnid sanity check；`ecff54aa20b5` |
| 0086 | `14-f2fs/0086-f2fs-extent-info-init.patch` | extent_info 初始化；`07523f7dd95d` |
| 0087 | `14-f2fs/0087-f2fs-map-next-extent.patch` | `map->m_next_extent` 修正；`4267734542b0` |
| 0088 | `14-f2fs/0088-f2fs-zero-sized-extent.patch` | zero-sized precache extent；`b133c8ad56cb`，依赖 0087 |
| 0089 | `14-f2fs/0089-f2fs-truncate-first-page.patch` | truncate 错误路径清首页；`28c17b42a27b` |

## r13 binder 位图描述符查找（2026-10-31）

Templar `ba009eabe6` = 上游 `15d9da3f818c` + `11512c197d38` + `3ebcd3460cad`
的 squash。`dmap` 放在 `binder_proc_ext`，不改冻结的 `binder_proc` 布局；
无导出符号变化。

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0090 | `15-binder/0090-binder-dbitmap.patch` | binder：用 dbitmap 做 O(1) 描述符查找；新增 `drivers/android/dbitmap.h`；Templar `ba009eabe6` |

## r14 RCU 惰性回调（2026-11-01）

采用 ACK `android14-5.15` 的 `rcu_async_hurry_nesting` 路线：开机和挂起期间通过独立
计数器强制赶时间，不再依赖 `rcu_expedited`（本机 cmdline 有
`rcupdate.rcu_expedited=1`，旧回移因此失效）。保留 5.10 的惰性核心，补上可写运行时
开关、收缩器修正和必须及时的调用点。内核默认关闭，运行时路径
`/sys/module/rcutree/parameters/enable_rcu_lazy`（0/1，0644）；要求
`rcu_nocbs` 已卸载回调，本机为 `rcu_nocbs=0-7`。

KMI：新增导出符号被 `CONFIG_TRIM_UNUSED_KSYMS` 裁掉，最终 `vmlinux.symvers`
仍为 7298 个、缺失 0、CRC 差异 0；670 个厂商模块 0 失败。

| 序号 | 补丁 | 内容 |
|---|---|---|
| 0091 | `16-rcu/0091-rcu-barrier-nocb-wake.patch` | `rcu_barrier()` 补 NOCB GP 唤醒；`a93e421c` |
| 0092 | `16-rcu/0092-rcu-bypass-flush-wakeup.patch` | flush bypass 时补迟到的唤醒；`20cefbbb` |
| 0093 | `16-rcu/0093-rcu-lazy-callbacks.patch` | `call_rcu()` 惰性回调核心；`3bab57d7` |
| 0094 | `16-rcu/0094-rcu-nocb-flush-refactor.patch` | `rcu_nocb_do_flush_bypass()` 重构；`c0abda7d` |
| 0095 | `16-rcu/0095-rcu-lazy-shrinker.patch` | 惰性回调收缩器；`9c54919b` |
| 0096 | `16-rcu/0096-percpu-refcount-call-rcu-hurry.patch` | percpu refcount 改用及时接口；`4fe455d1` |
| 0097 | `16-rcu/0097-rcu-sync-call-rcu-hurry.patch` | `rcu_sync` 改用及时接口；`b180dbb9` |
| 0098 | `16-rcu/0098-rcu-lazy-callbacks-fixup.patch` | 惰性核心修正；`eb4822a2` |
| 0099 | `16-rcu/0099-rcu-track-laziness-boot-suspend.patch` | 开机/挂起惰性计数器；ACK `85685937` |
| 0100 | `16-rcu/0100-rcu-runtime-lazy-param.patch` | `enable_rcu_lazy` 可写开关、默认关闭；ACK `37b02c19` + `706e751b` |
| 0101 | `16-rcu/0101-workqueue-dst-call-rcu-hurry.patch` | `queue_rcu_work()`、`dst_release()` 改用及时接口；ACK `a7e30c0e` |
| 0102 | `16-rcu/0102-rcu-lazy-shrinker-fixes.patch` | 收缩器 5 个竞态/卸载修正；ACK `2450b78e` 等 |
| 0103 | `16-rcu/0103-rcu-scsi-hurry.patch` | `scsi_eh_scmd_add()` 改用 `call_rcu_hurry()`；审计发现，避免 UFS/SCSI EH 被惰性拖慢 |

## 2026-10-31 第二次调整：zram 内建 + 小米组

同日曾把 zram 交还厂商模块（移植包里的 zram.ko 是第三方月亮内核的闭源构建），随后改为
自己维护：月亮内核已停更，闭源模块无法审查，且会把它自带的回收改动（异步 slab 回收）
一起带进来。最终方案：

- 0016、0017 回到通用系列（编号不变）；0015 负责启用压缩算法，0016 的配置块只含 zram、
  zsmalloc、LZO 和默认算法。
- 新增 `xiaomi/0027`（ExtM）、`xiaomi/0028`（内存冻结）、`xiaomi/0029`（memcg 文件注册修复）和 `xiaomi/0030`（`mfz_enable` 默认值）；0027/0028 来自小米官方源码；`series.xiaomi` = 通用系列 + 小米组。
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
