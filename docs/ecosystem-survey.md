# 生态调研：我们和 5.10 生态的差距

日期：2026-10-30。只读调研，本次没有改内核或补丁。

2026-10-31 更新：基线已从 `a1eed2e9c` 升到 ACK lts 最新 `8059ae2`；Linux stable
5.10.273 仍未合入 ACK，安全缺口和本报告的判断不变。

## 方法

项目重启后，为了确认"我们现在的优化和生态相比还差什么"，按方向拆成 10 个子代理并行收集：
安全/CVE、容器、高版本回移、内存/zram、网络、IO/调度/电源、文件系统、横向内核项目、
yudi 机型、中文社区。子代理只负责找事实和来源，不做取舍；主代理汇总后给一次判断。

调研时的树：`p0-series`，HEAD `a10996c3f`，26 个补丁，源码树 `4fa856c9`，基线 5.10.272。
2026-10-30 的决定：先把结论归档，内核保持现状。

## 总表

| 方向 | 生态对照 | 我们 | 判断 |
| --- | --- | --- | --- |
| 安全/上游 | 5.10.273（2026-10-30 发布，517 个提交）；ACK 10 月还有 7~10 个没进 stable 的安全提交 | 5.10.272 + 4 个手工 CVE | 唯一该补的缺口 |
| 容器 | Droidspaces 要求；同机型 Star-ZER0 5.10.252 被列为可用 | 设备/命名空间/veth/bridge/netfilter/IPVS/FHANDLE/CHECKPOINT_RESTORE/CFS_BANDWIDTH/CGROUP_PIDS 全开；ntsync/futex_waitv/epoll_pwait2 都有 | 已在上限，不动 |
| 内存 | MGLRU（android13-5.10、arter97 5.10.251）；le9uo；Kcompressd | le9uo + Kcompressd + zram lz4kd；无 MGLRU | MGLRU 不推荐 |
| zram | ExtM B + MIUI zram 统计（LowTension 5.10.237 公开树）；ZRAM_MULTI_COMP | LZ4K/LZ4KD + ExtM A 探针 | 维持不做 B |
| zstd | 1.5.7（ztc/Pzqqt） | 已升 1.5.7，f2fs/crypto/squashfs/incfs/pstore 调用方已适配 | 完成 |
| 网络 | BBRv3（WildKernels 3a75d65 同源）；Google 2026-09 新版独立 tcp_bbr3.c；PLB 上游只覆盖 IPv6 | BBRv3 + PLB | 可选跟进，不急 |
| IO/调度/电源 | BORE、TEO、UCLAMP、mq-deadline/Kyber 修复 | ADIOS + blk-mq depth | 不在原目标，不加 |
| 文件系统 | EROFS zstd 回移（7c442bbe，来源待核对）；f2fs 修复 | fs/erofs 没有 zstd 代码；f2fs 已用 1.5.7 | 低优先，f2fs 修复随 5.10.273 |
| 加固 | GrapheneOS 5.10 已归档；DivestedOS 硬化补丁 | 无额外硬化 | 不做 |
| 设备证据 | Star-ZER0、lkm4ctr 免刷内核跑 Docker、AOSPA 配置 | KMI 7298/0/0，670 个 vendor 模块 0 失败 | 路线可行 |

## 安全与上游同步

本地基线 5.10.272。stable 5.10.273 于 2026-10-30 发布，共 517 个提交。ACK
`android12-5.10-lts` 头是 `8059ae2`（2026-10-24），`android12-5.10` 头是
`15fd0b87`（2026-10-28），本地都不是祖先。

### 5.10.273 里和容器/日常使用相关的修复

| 提交 | 内容 |
| --- | --- |
| 25841e8d、2f53376b | nf_tables：set 元素计数在插入前无条件递增 |
| 29538fb3 | nf_tables：错误路径释放 flowtable 前等 RCU 宽限期 |
| 6c826a2e | nf_tables：nf_trace 启用时的崩溃（未初始化 info->pkt） |
| 348218a4 | nf_tables：NF_STOLEN 时不再访问可能已释放的 skb |
| 4e5a6d89 | nft_flow_offload：init 错误路径丢 flowtable 引用 |
| 0dd4e3d5 | ipset：内核侧 add 不更新 comment |
| 66472227 | fs：fspick() 拒绝内部 superblock |
| f9b48864 | namespace：automount 的挂载加锁 |
| 1e6ee93c | net/packet：TX_RING 字节计数溢出 |
| aa4a3bec | io_uring：写记账改到 ->ki_complete |
| f53d13a2 | openvswitch conntrack：扩展重分配导致 helper UAF |
| e5f830ae、9ebe824d、19c4de81、14fb6fad、77249d4b、872a38b6 | keys：读方法类型保护、keyring 索引、进程 keyring 搜索授权、named keyring owner、持久 keyring 超时等 |

### ACK 上还没进 stable、本地也没有的

| 提交 | 内容 |
| --- | --- |
| 8b1cb427 | usb: gadget: u_audio: Fix use-after-free on sound card disconnect |
| 89a3b6a3 | ipv4: validate checksum_start before completing checksum |
| 091c49a9 | net: lock the socket in sock_gettstamp() |
| 133d8e99 | nfc: llcp: Fix race condition in accept_queue lifecycle |
| a3431a2d | HID: logitech-hidpp: fix race condition when accessing stale stack pointer |
| ba7e98f3 | Bluetooth: RFCOMM: serialize security confirmation handling（ASB 2026-10 标签） |
| 15fd0b87 | f_midi UAF（android12-5.10 尖端） |
| bda27102 | RFCOMM NULL deref（尖端，对象本地缺失） |
| 9bc43309 | HID synchronize input（尖端，对象本地缺失） |

### Android Security Bulletin 2026

- 2026-09：CVE-2026-31629（NFC，Critical，提交 4642ec2b3fdc、3bcdd9244037）、
  CVE-2026-43049（logitech-hidpp，High，提交 20130e92480a、0e9b1ff4）；另有 3 个
  pKVM 的 Critical 项（CVE-2026-58846/58848/58941），本机不用 pKVM，不适用。
- 2026-10：内核段没有表，但 ACK 标签对应的提交 `ba7e98f3605e`（RFCOMM 串行化）本地未含。
- 2026-06：CVE-2025-40214（af_unix scc_index），5.10 没有这段代码路径，不适用。
- 2026-08：页面抓取 3 次都没有 CVE 表，内核项未核对到。
- 上述 ACK 提交在本地对象库中都没有，未做代码等价核对。

### 我们手工回移的 4 个 CVE

| CVE | 修复 | 本地状态 | 5.10.y |
| --- | --- | --- | --- |
| CVE-2026-98984 | dcache：75f4197f1e11，dentry 正在移除时不加挂载点 | 在 0011 里 | **5.10.273 已含**（stable 回移 25e3ce3e2ebd），升级时去掉重复段 |
| CVE-2026-68448 | overlayfs：a1e0eb8f55cf，copy_file_range 源用 mounter creds 校验 | 在 0011 里 | 没有，继续保留 |
| CVE-2026-98972 | cpuset：e06b678e3b4e，is_in_v2_mode() 不再读可重建的 root | 在 0011 里 | 没有，继续保留 |
| CVE-2026-93288 | nfnetlink_log：33d1469b0124，pernet 释放前等 RCU | 在 0011 里 | 没有，继续保留 |

rtmutex 的两个 CVE（CVE-2026-43499/53163）基线里已有修复代码，不需要再补。

### 第三方安全线

GrapheneOS 的 5.10 仓库已归档（最后推送 2025-03-04），2026 年的 release 只维护
6.1/6.6/6.12/6.18；LineageOS 24 的更新日志称 18.1–24.0 已合入 2025-08 到 2026-10
的安全补丁，但有 xiaomi_sm8450 内核、没有 yudi（sm8475）内核；DivestedOS 的
kernel_patches 有 4.4–5.15 的硬化补丁。结论：没有现成可跟的第三方 5.10 安全线，
直接跟 stable + ACK 最省事。

## 容器

- Droidspaces 的 GKI 补丁（001/002）主要补 SYSVIPC、POSIX_MQUEUE 这些；CFS_BANDWIDTH、
  CGROUP_PIDS 被文档标为可能破 kABI，我们已经有，7298 个符号和 670 个模块的门禁全过。
- 我们现在开的东西：cgroup v1 devices/pids/perf/net_cls、veth/bridge/netfilter/IPVS/
  SCTP/VXLAN/VLAN/IPVLAN/MACVLAN/L2TP/FOU/GRE、tc、blkio 限速、Btrfs、
  CHECKPOINT_RESTORE、FHANDLE、CRIU diag；Wine 方向的 ntsync、futex_waitv、
  epoll_pwait2 也有。
- 同机型证据：Star-ZER0 的 yudi 5.10.252 fork 被 Droidspaces 社区表列为可用，带 NTsync、
  Turnip/Virgl；lkm4ctr 有免刷内核跑 Docker 的模块（另一条路线）。
- 判断：容器面已到生态上限，不需要再为容器加东西。

## 内存与 zram

- MGLRU：只在 `android13-5.10` 有，arter97 的 5.10.251 也有；`android12-5.10` 没有。
- le9uo、Kcompressd：我们都有，Kcompressd 来自 ztc1997/Pzqqt。
- ExtM B：公开的 LowTension 5.10.237 树里有小米 zram 统计和 ExtM 代码，可以做参考；
  用户已决定不做。
- ZRAM_MULTI_COMP：有 5.10 回移，但只有配合 ExtM B（二级压缩）才有意义。
- mfz 是 6.6 的东西，X-Ring zgroup、DAMON 也不在 5.10 主线，不适用。
- 判断：MGLRU 不推荐。16GB 收益有限；它重写回收路径，和 Kcompressd（挂在 kswapd）、
  le9uo、zram 全冲突。android13-5.10/arter97 能跑，不代表我们这堆 mm 补丁上能跑。

## 网络

- BBRv3：我们的实现和 WildKernels 的 `3a75d65` 同源；Google 2026-09 的 BBRv3 是独立的
  `tcp_bbr3.c`，另一套实现，收益没有证据。
- PLB：上游就只覆盖 IPv6，不是我们改残了；手机网络收益有限。
- 其他：`force_tcp_nodelay`、OpenWrt 的 threaded NAPI/netfilter 优化，多针对路由/隧道场景。
- 判断：保持现状；要跟进 Google 新版再单独评估。

## IO/调度/电源

- ADIOS：源码宏是 3.2.0，说明里写 3.3.0r2，我们实际用的是旧版；需要时再从上游对一次。
- 生态里还有 mq-deadline/Kyber/BFQ/blk-mq 的修复，以及 BORE、TEO、schedutil、UCLAMP 的调整。
- 判断：不在最初的目标里，对这台机器收益不明确，不主动加。

## 文件系统

- EROFS zstd：社区报告说有 5.10 回移 `7c442bbe`（基于 5.10.223）；本地 `fs/erofs` 里没有
  zstd 代码，来源需要核对。只有系统分区真的用 zstd 压缩才有意义。
- f2fs：lookup/checkpoint 的修复大多会随 stable 进来。
- overlayfs/fscrypt/iomap 的发现没有形成可执行的补丁清单。
- 判断：随 5.10.273 走；EROFS zstd 先核对再说。

## 横向项目与第三方补丁集

- WildKernels：BBRv3 与我们同源，可作为对照。
- Pzqqt Melt / ztc1997：lazy RCU、zstd 1.5.7、Kcompressd 的来源。
- arter97：5.10 上有 MGLRU 和一批 mm 回移，是 MGLRU 的参考实现。
- LineageOS：有 xiaomi_sm8450 内核，没有 yudi/sm8475 内核。
- ACK：android12-5.10 是最直接的上游。
- GrapheneOS 5.10 已归档；DivestedOS 有硬化补丁。
- 懒惰 RCU：5.10 没有这个特性；ztc 的回移带 3c8875a（call_rcu 走到 expedited
  时关闭 lazy），而且 vendor_boot 的 cmdline 有 `rcu_expedited=1`，实际上不会启用。

## yudi 与中文社区

- Star-ZER0 的 yudi 5.10.252 fork：Droidspaces 社区验证可用。
- 报告称小米公开了 yudi-t-oss 5.10.160 源码（未核实，见 HANDOFF 的待确认项）。
- AOSPA 有 yudi 的预编译配置；Uotan 有 yudi 移植包；Amktiao 有模块。
- lkm4ctr 的 Docker 模块可以免刷内核跑 Docker，说明容器需求不一定非要自定义内核。
- 这些多为二手信息，没有逐条验证。

## 没查实/失败的点

- source.android.com 2026-08-01 页面抓 3 次都没有 CVE 表，8 月内核项未核对到。
- kernel.org 的 commit/patch 页和 CVE 仓库克隆 TLS 失败；5.10.273 部分修复的 CVE 号
  只能记"未说明"。
- EROFS zstd 回移来源（7c442bbe）和 ADIOS 版本是两处矛盾，待核对。
- 社区二手信息未验证。

## 判断（2026-10-30）

1. 唯一明确该补的是安全同步：基线升到 5.10.273，挑 ACK 上还没进 stable 的安全提交，
   0011 里的 dcache 段去掉（已进 5.10.273），其余 3 个 CVE 保留；重放 26 个补丁，
   跑 KMI/模块/开机/容器/zram 门禁。
2. MGLRU 不做（理由见上）。
3. ExtM B 维持不做；ZRAM_MULTI_COMP、EROFS zstd、BORE/TEO/UCLAMP、Google 新版
   BBRv3 都不主动做。
4. 用户 2026-10-30 决定：先归档，不改内核。以后启动时按第 1 条开始。

## 来源（主要）

- ChangeLog-5.10.273：<https://cdn.kernel.org/pub/linux/kernel/v5.x/ChangeLog-5.10.273>
- ACK 标签：<https://android.googlesource.com/kernel/common/+/refs/tags/ASB-2026-10-05_12-5.10>
- ASB：<https://source.android.com/docs/security/bulletin/2026/2026-09-01>
- GrapheneOS releases：<https://grapheneos.org/releases>
- LineageOS 更新日志：<https://lineageos.org/Changelog-32/>
- DivestedOS kernel_patches：<https://codeberg.org/divested-mobile/kernel_patches>
- WildKernels、Pzqqt、ztc1997、arter97、Droidspaces、Star-ZER0 的 GitHub 仓库
