# GKI 5.10.272 patches（与当前源码对应）

这些补丁只包含本项目的改动，不包含 AOSP/android12-5.10 的 1535 条历史。

## 基线

- AOSP `android12-5.10-lts`，5.10.272 合并提交：`a1eed2e9c`
  （`Merge 5.10.272 into android12-5.10-lts`）
- 应用本目录的 `series` 后，应得到当前仓库的内核源码树；
  实测 tree 哈希为 `65226488ec40d50478e95a449d8f586ac8cebec4`
  （不含 `patches/` 目录本身）。

## 应用方法

```sh
cd common
git checkout a1eed2e9c
while read p; do git am "patches/$p"; done < patches/series
```

如果只想看 diff、不建提交：

```sh
cd common
git checkout a1eed2e9c
while read p; do git apply "patches/$p"; done < patches/series
```

补丁按 `series` 的顺序应用，不要只按目录名猜顺序。

## 分类

| 目录 | 内容 |
|---|---|
| `00-platform/` | yudi/Droidspaces 基础配置、构建脚本跳过严格 defconfig 检查 |
| `01-container/` | cgroup、nftables、桥接/IPv6 NAT、IPVS/SCTP、隧道/VLAN/tc、块层限速/Btrfs |
| `02-wine/` | NTSync、futex_waitv |
| `03-memory/` | le9uo 工作集保护 |
| `04-security/` | dcache、overlayfs、nfnetlink_log、cpuset |
| `05-storage/` | zram 内建、LZ4K/LZ4KD/NEON、lz4→lz4kd 映射 |
| `06-network/` | BBRv1 配置包、BBRv3 + TCP PLB、BBRv3 默认 |
| `07-block/` | ADIOS 调度器、blk-mq hctx 顺序修复、ADIOS 默认 |
| `08-syscalls/` | epoll_pwait2 |
| `09-docs/` | README 文档更新（只改 `README.gki-docker.md`） |

## 补丁索引

| 补丁 | 原提交 | 说明 |
|---|---|---|
| `00-platform/0001-gki-droidspaces-container-baseline.patch` | `3351311eb` | GKI: enable Droidspaces container features for yudi |
| `00-platform/0002-build-skip-strict-defconfig-check.patch` | `765e02f8a` | build: skip strict defconfig check for customized gki_defconfig |
| `01-container/0003-cgroup-devices-pids-net-cls.patch` | `cf9e01256` | GKI: enable cgroup device/pids/net_cls with ABI-safe ext split |
| `01-container/0004-cgroup-perf.patch` | `39fd319eb` | GKI: enable CGROUP_PERF with an ABI-safe cgrp split |
| `01-container/0005-netfilter-nftables.patch` | `179863749` | GKI: enable nftables with an ABI-safe struct net placement |
| `01-container/0006-bridge-netfilter-ipv6-nat.patch` | `ef0df4f22` | GKI: enable bridge netfilter and IPv6 NAT with ABI-safe netns |
| `01-container/0007-ipvs-sctp.patch` | `3655f7c25` | GKI: enable IPVS and SCTP with ABI-safe net namespace storage |
| `01-container/0008-tunnels-vlan-ipvlan-tc.patch` | `0864bc626` | phase6: enable tunnels, virtual NICs and tc; ABI-safe VLAN and IPVLAN |
| `01-container/0009-block-throttle-net-classifier-checkpoint-btrfs.patch` | `764e61cf9` | phase7: block throttle, net classifier, checkpoint/restore, Btrfs |
| `02-wine/0010-ntsync.patch` | `5e37c795c` | phase10.1: add NTSync driver for Wine/Proton |
| `03-memory/0011-le9uo-workingset-protection.patch` | `d65fc915b` | phase10.2: add le9uo working-set protection |
| `04-security/0012-container-security-fixes.patch` | `e7b167847` | phase10.3: backport container-relevant security fixes |
| `05-storage/0013-zram-lz4k-lz4kd-neon.patch` | `8f015b6ca` | phase10.4: build zram in with LZ4K/LZ4KD and ARM64 NEON |
| `05-storage/0014-zram-map-lz4-to-lz4kd.patch` | `dbdc674ae` | phase10.4a: map vendor lz4 writes to lz4kd |
| `06-network/0015-bbrv1-ksm-tmpfs-xattr.patch` | `eb4f940a0` | phase10.5: enable BBRv1, KSM and tmpfs xattrs |
| `06-network/0016-bbrv3-tcp-plb.patch` | `42ebf3a81` | phase10.6: backport BBRv3 and TCP PLB |
| `06-network/0017-bbrv3-default.patch` | `62cec6795` | phase10.7: make BBRv3 the default congestion control |
| `07-block/0018-adios-io-scheduler.patch` | `8a84344a2` | phase10.8: add ADIOS I/O scheduler as an available option |
| `07-block/0019-blk-mq-hctx-before-limit-depth.patch` | `ebf8ed4fc` | block: blk-mq: set hctx before elevator limit_depth |
| `07-block/0020-adios-default.patch` | `720aeb68a` | phase10.10: make ADIOS the default I/O scheduler |
| `02-wine/0021-futex-waitv.patch` | `e970ecb92` | phase10.11: backport futex_waitv syscall |
| `08-syscalls/0022-epoll-pwait2.patch` | `78b90ee4a` | phase10.12: backport epoll_pwait2 syscall |
| `09-docs/0023-docs-add-gki-docker-readme.patch` | `e982cb44f` | docs: add GKI Docker support README |
| `09-docs/0024-docs-ntsync-le9uo-security-zram.patch` | `10f124ee5` | docs: document NTSync, le9uo, security and zram |
| `09-docs/0025-docs-phase10.5.patch` | `867e6173f` | docs: update for phase 10.5 |
| `09-docs/0026-docs-phase10.6.patch` | `8dd834996` | docs: update for phase 10.6 |
| `09-docs/0027-docs-phase10.7.patch` | `90c474b1c` | docs: update for phase 10.7 |
| `09-docs/0028-docs-phase10.8.patch` | `58a10f05e` | docs: update for phase 10.8 |
| `09-docs/0029-docs-phase10.9-blk-mq.patch` | `5d213e854` | docs: update for phase 10.9 blk-mq hctx fix |
| `09-docs/0030-docs-phase10.10-adios-default.patch` | `c24fa6176` | docs: update for phase 10.10 ADIOS default |
| `09-docs/0031-docs-phase10.11-futex-waitv.patch` | `eba364b9a` | docs: update for phase 10.11 futex_waitv |
| `09-docs/0032-docs-phase10.12-epoll-pwait2.patch` | `cffd11567` | docs: update for phase 10.12 epoll_pwait2 |

## 验证

- 每个补丁保留原提交的作者和提交信息，`git am` 会重建对应提交。
- 应用完 `series` 后，内核源码树应与本仓库提交 `patches/` 之前的 `HEAD` 一致，
  即 tree `65226488ec40d50478e95a449d8f586ac8cebec4`
  （`09-docs` 只改 README；`patches/` 目录本身不在补丁里）。
- 本项目的硬门禁：7298 个基线导出符号 CRC 差异为 0；355 个 vendor_boot
  模块 0 失败。详见 `README.gki-docker.md`。
