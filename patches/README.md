# 内核补丁

基线是 AOSP `android12-5.10-lts` 的 5.10.272 合并提交 `a1eed2e9c`。
按 `series` 顺序应用后得到与仓库 `source/` 相同的内核源码树（不含本目录）：

```
6c6605b152b7b04be3100c3df4d328acfef19e9d
```

## 应用

```sh
cd common
git checkout a1eed2e9c
PATCHES=/path/to/gki-yudi/patches
while read p; do git am "$PATCHES/$p"; done < "$PATCHES/series"
```

只查看 diff、不建提交时，把 `git am` 换成 `git apply`。

## 补丁列表

共 14 个补丁，按功能拆分。

| 序号 | 补丁 | 内容 |
|---|---|---|
| 1 | `00-platform/0001-platform-task-user-abi.patch` | platform: keep task_struct and user_struct ABI stock |
| 2 | `00-platform/0002-gki-defconfig-feature-set.patch` | gki_defconfig: enable the container, Wine and storage feature set |
| 3 | `01-container/0003-cgroup-devices-pids-net-cls-perf.patch` | cgroup: enable devices, pids, net_cls and perf with ABI-safe state |
| 4 | `01-container/0004-container-networking.patch` | net: enable ABI-safe container networking |
| 5 | `01-container/0005-block-throttling-abireserve.patch` | block: overlay block throttling state on the KABI reserve |
| 6 | `02-wine/0006-futex-waitv-epoll-pwait2.patch` | futex, epoll: backport futex_waitv and epoll_pwait2 |
| 7 | `02-wine/0007-ntsync.patch` | ntsync: add the NTSync driver for Wine/Proton |
| 8 | `03-memory/0008-le9uo.patch` | mm: add le9uo working-set protection |
| 9 | `04-security/0009-container-security-fixes.patch` | fs, net: backport container-relevant security fixes |
| 10 | `05-storage/0010-zram-lz4k-lz4kd.patch` | zram: build in LZ4K/LZ4KD with ARM64 NEON |
| 11 | `06-network/0011-bbrv3-tcp-plb.patch` | tcp: backport BBRv3 and TCP PLB |
| 12 | `07-block/0012-adios.patch` | block: add the ADIOS I/O scheduler |
| 13 | `10-sched/0013-cfs-bandwidth-kabi.patch` | sched: add kABI-safe CFS bandwidth support |
| 14 | `00-platform/0014-kmi-module-crc-ipc-netns.patch` | kmi: restore module CRC rejection and pin the IPC/netns layouts |
