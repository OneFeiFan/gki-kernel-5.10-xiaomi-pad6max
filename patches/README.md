# 内核补丁

基线是 AOSP `android12-5.10-lts` 的 5.10.272 合并提交 `a1eed2e9c`。
按 `series` 顺序应用后得到的内核源码树（不含本目录）：

```
b979f12d04548c963b53c6927219e42d7b53ad72
```

## 应用

```sh
cd common
git checkout a1eed2e9c
PATCHES=/path/to/gki-yudi/patches
while read p; do git am "$PATCHES/$p"; done < "$PATCHES/series"
```

只查看 diff、不建提交时，把 `git am` 换成 `git apply`。

## 组织原则

- 每个功能补丁自带它需要的 `gki_defconfig` 选项，选项和让它保持 KMI 安全的代码在同一个补丁里。
- `series` 的任意前缀都能单独构建，不会出现"选项已经打开、配套代码还没到"的中间状态。
- 除 `gki_defconfig` 外，补丁之间不改同一个文件。去掉某个功能补丁，它的选项也一起去掉。
- 0001 必须保留：它关闭 `check_defconfig`，后面的补丁按功能分块追加选项，不是 savedefconfig 的顺序。
- 0004 的 `NET_CLS_CGROUP` 依赖 0003 的 `CGROUP_NET_CLASSID`；去掉 0003 时 Kconfig 会自动丢掉它。
- 补丁头部的 `Origin`、`Upstream-Status`、`KABI`、`Tested-On` 给出处、KABI 占用和验证范围；找不到来源的明确写"来源未记录"。

## 补丁列表

| 序号 | 补丁 | 内容 |
|---|---|---|
| 1 | `00-platform/0001-build-thinlto-defconfig-check.patch` | ThinLTO；关闭 `check_defconfig` |
| 2 | `00-platform/0002-platform-task-user-abi.patch` | task_struct/user_struct 的 KABI 占位；PID_NS、SYSVIPC、POSIX_MQUEUE、IPC_NS、USER_NS、DEVTMPFS |
| 3 | `01-container/0003-cgroup-devices-pids-net-cls-perf.patch` | cgroup MAIN/EXT 拆分；devices、pids、perf、net_cls |
| 4 | `01-container/0004-container-networking.patch` | 容器网络，含 netns_ipv4 的 l3mdev 布局和断言；nftables、bridge netfilter、IPv6 NAT、IPVS/SCTP、隧道、虚拟网卡、tc |
| 5 | `01-container/0005-block-throttling-abireserve.patch` | blk-throttle 状态放进 KABI 预留位；BLK_DEV_THROTTLING |
| 6 | `01-container/0006-checkpoint-restore-ipc-next-id.patch` | ipc next_id 放进 side table；CHECKPOINT_RESTORE、UNIX/PACKET/NETLINK_DIAG、FHANDLE |
| 7 | `02-wine/0007-epoll-pwait2.patch` | epoll_pwait2 回移（上游提交 7cdf7c20e971 等） |
| 8 | `02-wine/0008-futex-waitv.patch` | futex_waitv（64/32 位）回移；更新 syscall 表，`__NR_syscalls` 到 450 |
| 9 | `02-wine/0009-ntsync.patch` | NTSync 驱动；NTSYNC |
| 10 | `03-memory/0010-le9uo.patch` | le9uo 工作集保护 |
| 11 | `04-security/0011-container-security-fixes.patch` | 容器相关安全修复回移 |
| 12 | `05-storage/0012-zram-lz4k-lz4kd.patch` | zram/zsmalloc 内建、LZ4K/LZ4KD/NEON、内建模块黑名单；压缩算法选项 |
| 13 | `06-network/0013-bbrv3-tcp-plb.patch` | BBRv3 和 PLB；TCP_CONG_ADVANCED、BBR、BBR3（默认仍是 cubic） |
| 14 | `07-block/0014-blk-mq-limit-depth.patch` | blk-mq：在 `limit_depth` 前设置 ctx/hctx（ADIOS 的前置修复） |
| 15 | `07-block/0015-adios.patch` | ADIOS 调度器；MQ_IOSCHED_ADIOS（默认调度器不变） |
| 16 | `10-sched/0016-cfs-bandwidth-kabi.patch` | CFS 带宽 kABI 拆分；CFS_BANDWIDTH |
| 17 | `00-platform/0017-gki-defconfig-config-only-extras.patch` | 只改配置：KSM、tmpfs xattr/ACL、Btrfs |
| 18 | `08-power/0018-wq-power-efficient-default.patch` | 默认启用 power-efficient unbound workqueues（灰度实验） |
| 19 | `05-storage/0019-zram-writeback-extm-probe.patch` | 打开 zram writeback，作为小米 ExtM 的 A 探针 |

## 与上一版 15 个补丁的关系

- `epoll_pwait2` 和 `futex_waitv` 从原来的合并补丁拆成 0007 和 0008；两者共享的 syscall 表按上游提交重新生成，epoll 不动 `__NR_syscalls`，futex 把它从 449 加到 450。
- `blk-mq` 的 ctx/hctx 修复从 ADIOS 补丁里拆出来，放在 0014；ADIOS 顺延为 0015。
- 拆分只改补丁边界，拆分后的源码树是 `1ba8c0e…`；再加上 0018 的 WQ 配置后是 `108c798…`，加上 0019 的 zram writeback 后是上面的 `b979f12…`。
- 0018 只改配置，默认启用 `WQ_POWER_EFFICIENT_DEFAULT`，不涉及导出布局，便于按配置回退。
- 0019 只改配置，打开 `CONFIG_ZRAM_WRITEBACK`，作为 ExtM 的 A 探针；详见 `docs/ExtM-research.md`。
- 0012 的模块黑名单修复：命令行 `module_blacklist=` 恢复返回 `-EPERM`，内建驱动影子跳过单独返回 0 并打 info 日志。
- 与 14 个补丁版本相比，源码树只差 `gki_defconfig` 里重复的
  `# CONFIG_FHANDLE is not set` 和上述黑名单修复。
