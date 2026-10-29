# 内核补丁

基线是 AOSP `android12-5.10-lts` 的 5.10.272 合并提交 `a1eed2e9c`。
按 `series` 顺序应用后得到的内核源码树（不含本目录）：

```
24bbf84fe781ee37f10f012a01c5db4e2c94ec71
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

## 补丁列表

| 序号 | 补丁 | 内容 |
|---|---|---|
| 1 | `00-platform/0001-build-thinlto-defconfig-check.patch` | ThinLTO；关闭 `check_defconfig` |
| 2 | `00-platform/0002-platform-task-user-abi.patch` | task_struct/user_struct 的 KABI 占位；PID_NS、SYSVIPC、POSIX_MQUEUE、IPC_NS、USER_NS、DEVTMPFS |
| 3 | `01-container/0003-cgroup-devices-pids-net-cls-perf.patch` | cgroup MAIN/EXT 拆分；devices、pids、perf、net_cls |
| 4 | `01-container/0004-container-networking.patch` | 容器网络，含 netns_ipv4 的 l3mdev 布局和断言；nftables、bridge netfilter、IPv6 NAT、IPVS/SCTP、隧道、虚拟网卡、tc |
| 5 | `01-container/0005-block-throttling-abireserve.patch` | blk-throttle 状态放进 KABI 预留位；BLK_DEV_THROTTLING |
| 6 | `01-container/0006-checkpoint-restore-ipc-next-id.patch` | ipc next_id 放进 side table；CHECKPOINT_RESTORE、UNIX/PACKET/NETLINK_DIAG、FHANDLE |
| 7 | `02-wine/0007-futex-waitv-epoll-pwait2.patch` | futex_waitv、epoll_pwait2 |
| 8 | `02-wine/0008-ntsync.patch` | NTSync 驱动；NTSYNC |
| 9 | `03-memory/0009-le9uo.patch` | le9uo 工作集保护 |
| 10 | `04-security/0010-container-security-fixes.patch` | 容器相关安全修复回移 |
| 11 | `05-storage/0011-zram-lz4k-lz4kd.patch` | zram/zsmalloc 内建、LZ4K/LZ4KD/NEON、内建模块黑名单；压缩算法选项 |
| 12 | `06-network/0012-bbrv3-tcp-plb.patch` | BBRv3 和 PLB；TCP_CONG_ADVANCED、BBR、BBR3（默认仍是 cubic） |
| 13 | `07-block/0013-adios.patch` | ADIOS 调度器；MQ_IOSCHED_ADIOS（默认调度器不变） |
| 14 | `10-sched/0014-cfs-bandwidth-kabi.patch` | CFS 带宽 kABI 拆分；CFS_BANDWIDTH |
| 15 | `00-platform/0015-gki-defconfig-config-only-extras.patch` | 只改配置：KSM、tmpfs xattr/ACL、Btrfs |

## 与上一版 14 个补丁的关系

- 代码不变：143 个涉及文件里，除 `gki_defconfig` 外全部逐字节一致。
- 原 0002（集中的 defconfig）拆进了各功能补丁；原 0014（KMI 杂项）拆回各自归属：
  netns_ipv4 布局进 0004，IPC side table 进 0006，内建模块黑名单进 0011。
- 新增 0001（构建设置）、0006（CHECKPOINT_RESTORE 和 IPC）、0015（只改配置的附加项）。
- 唯一的内容变化：删掉 stock 的 `# CONFIG_FHANDLE is not set`。它和后面追加的
  `CONFIG_FHANDLE=y` 重复，Kconfig 会报 override 警告；生成的 `.config` 完全相同。
  仓库 `source/` 里同步删掉这一行后，tree 哈希从 `6c6605b…` 变成上面的 `24bbf84…`。
