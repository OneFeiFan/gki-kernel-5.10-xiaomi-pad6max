# 补丁

基线是 ACK `android12-5.10-lts` 的 `8059ae219630`（2026-10-24，Linux 5.10.272）。

| 系列 | 补丁数 | 应用后的源码树 |
| --- | --- | --- |
| `series` | 46 | `f2545102b9ea16eb087e81a0b0f50770173d0063` |
| `series.xiaomi` | 48 | `2eaa32fda05643fb9672a89502f46d6b48567141`，即仓库里的 `source/` |

`series` 是通用补丁，`series.xiaomi` 在其后加上只适用于小米设备的两个补丁。yudi 用的是 `series.xiaomi`。

## 应用

```sh
cd common
git checkout 8059ae219630
PATCHES=/path/to/gki-yudi/patches
while read p; do git am "$PATCHES/$p"; done < "$PATCHES/series.xiaomi"
```

只想看改动、不建提交时，把 `git am` 换成 `git apply`。

## 组织方式

一个功能一个补丁。属于同一功能的多个上游提交合并在同一个补丁里，补丁说明列出它包含的原始提交，并在末尾附上这些提交的原始说明。f2fs 的上游修正例外，每个修正单独一个补丁，以后基线自带了某个修正时可以直接删掉。

补丁编号就是应用顺序，也和目录顺序一致：`00-platform` 到 `16-rcu`，最后是 `xiaomi/`。

每个补丁自带它需要的 `gki_defconfig` 选项，写在原厂对应选项的后面，用 `# yudi:` 注释标出。因为选项不再按 savedefconfig 的顺序排列，0001 关闭了 `check_defconfig`。

补丁说明头的字段（`Origin`、`Upstream-Status`、`KABI`、`Depends-On`、`Notes`、`Tested-On`）写明出处、与来源的差异、KABI 预留字段的占用、依赖和验证范围。格式见 [docs/writing-guide.md](../docs/writing-guide.md)。

## 依赖

除下表外，任何一个补丁都可以单独去掉，其余补丁照样能打上。这是逐个去掉 48 个补丁实测得出的。

| 补丁 | 依赖 | 原因 |
| --- | --- | --- |
| 0009 futex_waitv | 0008 epoll_pwait2 | 共用系统调用表 |
| 0025 zstd | 0015 LZ4K/LZ4KD | 修改了同一处 `lib/Kconfig` |
| 0042 f2fs 零长度区段 | 0041 f2fs 区段映射 | 基于 0041 的改动 |
| 0048 内存冻结 | 0047 ExtM | 同一个驱动 |
| 0047 ExtM | 0016、0017 | 需要内建 zram 和 `ZRAM_WRITEBACK`，补丁本身可以单独打上 |

另外，0005 的 `NET_CLS_CGROUP` 依赖 0004 的 `CGROUP_NET_CLASSID`；去掉 0004 时，Kconfig 会自动去掉它。

## 列表

| 序号 | 补丁 | 内容 | r16 编号 |
| --- | --- | --- | --- |
| 0001 | `00-platform/0001-build-thinlto-defconfig-check.patch` | ThinLTO；关闭 `check_defconfig` | 0001 |
| 0002 | `00-platform/0002-platform-task-user-abi.patch` | task_struct/user_struct 的 KABI 占位；PID_NS、SYSVIPC、POSIX_MQUEUE、IPC_NS、USER_NS、DEVTMPFS | 0002 |
| 0003 | `00-platform/0003-gki-defconfig-config-only-extras.patch` | 只改配置：KSM、tmpfs xattr/ACL、Btrfs | 0003 |
| 0004 | `01-container/0004-cgroup-devices-pids-net-cls-perf.patch` | cgroup MAIN/EXT 拆分；devices、pids、perf、net_cls | 0004 |
| 0005 | `01-container/0005-container-networking.patch` | 容器网络，含 netns_ipv4 的 l3mdev 布局和断言；nftables、bridge netfilter、IPv6 NAT、IPVS/SCTP、隧道、虚拟网卡、tc | 0005 |
| 0006 | `01-container/0006-block-throttling-abireserve.patch` | blk-throttle 状态放进 KABI 预留位，本地实现；BLK_DEV_THROTTLING | 0006 |
| 0007 | `01-container/0007-checkpoint-restore-ipc-next-id.patch` | ipc next_id 放进独立的表，本地实现；CHECKPOINT_RESTORE、UNIX/PACKET/NETLINK_DIAG、FHANDLE | 0007 |
| 0008 | `02-wine/0008-epoll-pwait2.patch` | epoll_pwait2 回移（上游提交 7cdf7c20e971 等） | 0008 |
| 0009 | `02-wine/0009-futex-waitv.patch` | futex_waitv（64/32 位）回移；更新 syscall 表，`__NR_syscalls` 到 450 | 0009 |
| 0010 | `02-wine/0010-ntsync.patch` | NTSync 驱动；NTSYNC | 0010 |
| 0011 | `03-memory/0011-le9uo.patch` | le9uo 工作集保护；硬水位把扫描目标全部归零时的 OOM 兜底（不能换出时只填充文件页链表） | 0011、0033 |
| 0012 | `03-memory/0012-kcompressd.patch` | Kcompressd：kswapd 把匿名 zram 页交给 per-node 线程异步压缩；状态放独立数组，`pglist_data` 不动 | 0012 |
| 0013 | `04-security/0013-container-security-fixes.patch` | 四个上游修复回移（CVE-2026-98984 / 68448 / 98972 / 93288）；nfnetlink_log 修复含 5.10 各日志器的 pre_exit 部分 | 0013 |
| 0014 | `05-storage/0014-lz4-armv8.patch` | lib/lz4 更新到带 ARM64 NEON 的版本；crypto、f2fs、incfs 调用点适配 | 0014 |
| 0015 | `05-storage/0015-lz4k-lz4kd-codecs.patch` | LZ4K、LZ4K-oplus、LZ4KD 编解码器与 crypto 封装；连同 LZ4HC、842 作为内建压缩算法 | 0015 |
| 0016 | `05-storage/0016-zram-builtin-lz4k-lz4kd.patch` | 内建 zram、zsmalloc、LZO；zram 接线（算法列表、`ZRAM_DEF_COMP`）；内建模块屏蔽名单（`module_blacklist=` 返回 `-EPERM`，内建影子跳过返回 0） | 0016 |
| 0017 | `05-storage/0017-zram-writeback.patch` | `ZRAM_WRITEBACK`（上游写回；小米 PerfInit 用它挂 ExtM 写回设备） | 0017 |
| 0018 | `05-storage/0018-zram-zcomp-vmalloc.patch` | zram 压缩流缓冲区改为 `vzalloc(2 * PAGE_SIZE)` / `vfree`，不再要求 2 页物理连续 | 0032 |
| 0019 | `06-network/0019-tcp-bbrv3.patch` | BBRv3：TCP 基建（rate sample、32 位时间戳、TLP、CE 事件、`tcp_snd_cwnd`）、PLB、BBRv3 本体与 inet_diag 统计、`gki_defconfig`（默认仍是 cubic） | 0018、0019、0020、0021 |
| 0020 | `06-network/0020-tcp-cubic-fixes.patch` | tcp_cubic：HyStart 轮次起点修正；`hystart_ack_delay()` 适配 BIG TCP | 0053、0054 |
| 0021 | `07-block/0021-adios.patch` | ADIOS 3.2.0：blk-mq `limit_depth` 前置（上游 `6259151c04d4`）、调度器本体、修正（去掉错误的 `ELEVATOR_F_MQ_AWARE`，完成请求时跳过 flush/FUA）；默认调度器不变 | 0022、0023、0031 |
| 0022 | `08-power/0022-wq-power-efficient-default.patch` | 默认启用节能的工作队列（`WQ_POWER_EFFICIENT_DEFAULT`） | 0024 |
| 0023 | `08-power/0023-suspend-keep-cpuidle.patch` | 进入 suspend 时不再关闭 cpuidle；Tim Murray `571508da07` | 0052 |
| 0024 | `08-power/0024-s2idle-wakeup.patch` | s2idle：避免过多唤醒尝试；`4b81b6afa1` | 0056 |
| 0025 | `09-lib/0025-zstd-1.5.7.patch` | zstd 升级到 1.5.7；lib/zstd 换成 common/compress/decompress 布局，crypto/f2fs/btrfs/squashfs/incfs/pstore/unzstd 切到新 API；新增 ZSTD_COMMON | 0025 |
| 0026 | `09-lib/0026-page-copy-clear.patch` | 整页复制与清零：zram、zsmalloc、f2fs 的满页 `memcpy` 改 `copy_page`；整页 `memset` 改 `clear_page`（7 个调用点均页对齐）；arm64 `clear_page` 16 字节对齐 | 0075、0076、0077、0078、0079 |
| 0027 | `10-sched/0027-cfs-bandwidth-kabi.patch` | CFS 带宽 kABI 拆分；CFS_BANDWIDTH | 0026 |
| 0028 | `10-sched/0028-sched-micro-opts.patch` | 调度小优化：去掉 idle 循环多余的 barrier；优化 `__calc_delta()`；关闭 NUMA 时编译掉 NUMA 代码 | 0055、0066、0067 |
| 0029 | `11-cpuidle/0029-teo-backport.patch` | TEO 空闲调度器回移（2021–2024 的 16 个上游提交）；默认 governor 仍是厂商 `qcom-cpu-lpm`，由 yudi-tweaks 切换 | 0034、0035、0036、0037、0038、0039、0040、0041、0042、0043、0044、0045、0046、0047、0048、0049 |
| 0030 | `11-cpuidle/0030-idle-entry-fixes.patch` | 空闲入口修正：不在 `__CPU_PM_CPU_IDLE_ENTER()` 内部返回；`need_resched()` 时不进入 idle | 0050、0051 |
| 0031 | `12-misc/0031-small-alloc-micro-opts.patch` | Sultan 的小块分配与零碎优化：sync_file（含 ABI 修正）、kernfs、selinux、bpf、mbcache、binder 调试打印、uid_sys_stats、kallsyms | 0057、0058、0059、0060、0061、0062、0063、0064、0065 |
| 0032 | `12-misc/0032-pwrkey-sync.patch` | 长按电源键 2 秒同步文件系统（`INPUT_PWRKEY_SYNC`，配置随补丁）；死机选项未开启 | 0068、0070 |
| 0033 | `13-kmem/0033-kmem-cache-pools.patch` | kmem_cache 池：kernfs open node/file、cgroup cset link、dma_buf attachment、sync_file | 0071、0072、0073、0074 |
| 0034 | `14-f2fs/0034-f2fs-file-offset-overflow.patch` | 文件偏移整数溢出防护；`1b8085235fe9` | 0080 |
| 0035 | `14-f2fs/0035-f2fs-node-info-flags.patch` | node info flags 总是初始化；`87c2b83fe0a0` | 0081 |
| 0036 | `14-f2fs/0036-f2fs-gc-victim-segno.patch` | FG_GC ioctl 标记受害段；`0bdfa4232315` | 0082 |
| 0037 | `14-f2fs/0037-f2fs-negative-nlink.patch` | 损坏镜像负 i_nlink 防 warning；`1f6332872374` | 0083 |
| 0038 | `14-f2fs/0038-f2fs-sync-node-pages-error.patch` | `f2fs_sync_node_pages()` 返回正确错误号；`d94445903c9b` | 0084 |
| 0039 | `14-f2fs/0039-f2fs-ino-xnid-sanity.patch` | ino/xnid sanity check；`ecff54aa20b5` | 0085 |
| 0040 | `14-f2fs/0040-f2fs-extent-info-init.patch` | extent_info 初始化；`07523f7dd95d` | 0086 |
| 0041 | `14-f2fs/0041-f2fs-map-next-extent.patch` | `map->m_next_extent` 修正；`4267734542b0` | 0087 |
| 0042 | `14-f2fs/0042-f2fs-zero-sized-extent.patch` | zero-sized precache extent；`b133c8ad56cb`，依赖 0041 | 0088 |
| 0043 | `14-f2fs/0043-f2fs-truncate-first-page.patch` | truncate 错误路径清首页；`28c17b42a27b` | 0089 |
| 0044 | `15-binder/0044-binder-dbitmap.patch` | binder：用 dbitmap 做 O(1) 描述符查找；新增 `drivers/android/dbitmap.h`；Templar `ba009eabe6` | 0090 |
| 0045 | `16-rcu/0045-rcu-sync-latency.patch` | RCU：GP kthread 的 CPU 提前报告 QS，缩短 synchronize_rcu()；Joel Fernandes `43de808766` | 0069 |
| 0046 | `16-rcu/0046-rcu-lazy.patch` | RCU 惰性回调：惰性核心、开机与挂起计数器、收缩器及其修正、`rcu_barrier()` 与唤醒修正、必须及时执行的调用点（percpu refcount、rcu_sync、`queue_rcu_work()`、`dst_release()`、SCSI EH）、运行时开关 `enable_rcu_lazy`（默认关闭） | 0091、0092、0093、0094、0095、0096、0097、0098、0099、0100、0101、0102、0103 |
| 0047 | `xiaomi/0047-zram-xiaomi-extm.patch` | 小米 ExtM zram：分批写回、按时间老化、低压缩率优先写回、页面寿命与大小统计、SIGUSR1 中止写回；含 memcg 文件注册位置修复 | 0027、0029 |
| 0048 | `xiaomi/0048-zram-xiaomi-memory-freeze.patch` | 小米内存冻结（mfz）写回策略：按 memcg 打标、`mfz_enable`（默认 1）、`mfz_disk_quota`、`mfz_compr_data_size`、`mfz_idle_stat`、`bd_stat` 多三列；memcg 文件 5.10 与 6.6 两套名字 | 0028、0030 |

各功能的说明见 [docs/features.md](../docs/features.md)。r16 的旧编号和新编号的完整对照见 [RENUMBER-r17.md](RENUMBER-r17.md)。
