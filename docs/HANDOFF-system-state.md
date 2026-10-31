# 系统状态交接（yudi）

日期：2026-10-31。给后续驱动工作留的现状记录，内核构建和补丁见
[`kernel.md`](kernel.md) 与仓库 `patches/`。除特别说明外，表中的数值都是
2026-10-29 到 2026-10-31 的采样值。

## 设备与系统

| 项目 | 值 |
|---|---|
| 机型 | Xiaomi Pad 6 Max，yudi，SM8475 |
| GPU | Adreno 730 v3 |
| 系统 | Android 16，HyperOS `V816`，`OS3.0.304.97.WMHCNXM` |
| 安全补丁 | 系统 2026-08-01，vendor 2026-02-01 |
| 屏幕 | 1800×2880，最高 120Hz，360dpi，`qcom,mdss_dsi_m80_42_02_0a_dsc_video` |
| 内存 | 约 15.9GB |
| CPU | 8 核，小核 2.016GHz，中核 2.7456GHz，大核 3.1872GHz，`walt` |
| 启动槽 | `_a`，bootloader 已解锁，SELinux Enforcing |
| 当前内核 | `5.10.272-android12-9-g59cde2a4dfab`（r6，2026-10-31） |

两个容易踩的点：

- 系统是 Android 16，内核源码来自 `android12-5.10-lts`。设备 vendor 模块按
  `5.10.160-gki` 编译，现在靠 GKI KMI 兼容跑通，不代表可以拿 Android 12 的
  vendor 组件直接替换。
- boot 的 ramdisk 来自 Google GKI 认证镜像（`android12-5.10-2026-10`），内核是本
  项目编译的 5.10.272。做 vendor/驱动层改动前，先从当前系统取一份 boot 底包对照。

## 内核项目

| 项目 | 值 |
|---|---|
| 源码 | `~/kernel-sources/vanilla-root/common` |
| 分支 | `p0-series-xiaomi`（`p0-series-273` 保留通用 26 补丁） |
| HEAD | `59cde2a4d`（29 个功能补丁） |
| 构建输出 | `~/kernel-sources/out-xiaomi` |
| 补丁 | 29 个（通用 26 + 小米 3），基线 `8059ae2`，源码树 `2afd8cc8` |
| 镜像 | r6 只在本地（未发布）；最后发布的是 r3；SHA256 见下 |
| 灰度 | `WQ_POWER_EFFICIENT_DEFAULT=y`；ExtM/mfz 已落地（0027/0028/0029）；Kcompressd（默认启用）；cpuidle governor 默认跟随系统（yudi-tweaks 1.8 可切 TEO） |
| GitHub | `OneFeiFan/gki-kernel-5.10-xiaomi-pad6max`，`pad6max` 快照分支 |
| 模块 | yudi-tweaks 1.8；ntsync 1.1 |

## ExtM 与内存冻结（mfz）

- 0027 把 zram 换成小米 ExtM 写回实现；0028 加 mfz 策略；0030（r6 之后，待构建）把 `mfz_enable`
  默认值改为 1——r6 上的 `mfz_enable=0` 正是 0028 默认值错误所致；0029 修复 memcg 文件注册位置（小米 spinel 源码把注册写在 `return 0` 之后，0027 原样带入）
  （小米 spinel 源码把 `cgroup_add_legacy_cftypes()` 放在 `zram_init()` 的 `return 0` 之后，0027 原样带入）。
- 设备实测：zram 内建，`comp_algorithm` 为 `[lz4kd]`，`backing_dev` 为
  `/dev/block/dm-48`；`/sys/block/zram0` 出现 `mfz_enable`、`mfz_disk_quota`、
  `mfz_compr_data_size`、`mfz_idle_stat`、`bd_stat`。
- `freeze-app/memory.anno_writeback_enable=2`（init.rc 写 1，驱动按 5.10 接口存 2）；
  `mfz_enable=0`、`mfz_disk_quota=524288`，由 ROM 的 PerfInit 决定是否启用。
- mfz 计数实测：测试进程在 `freeze-app` 换出 512MB 后 `mfz_compr_data_size` 为
  2,871,990 字节；进程退出后回到约 0。按 memcg 打标和计数路径正常。
- 冻结器现状（2026-10-31 实测）：内核的 v1 freezer 和 v2 冻结都可用。进程都在 cgroup v2
  的分组里（system_server 在 `/system/uid_1000/pid_*`，应用在 `/apps/uid_*/pid_*`）；v2 只
  列出 pids 控制器是正常的（cpu、cpuset、memory、blkio 挂在 v1，其余是 v1 专用控制器），
  v2 冻结是内核核心功能，不需要控制器。新建组写 `cgroup.freeze` 实测 `cgroup.events` 显示
  `frozen 1`，解冻后 `frozen 0`。系统 API 冻结器的 `Freezer disabled` 来自 ROM 默认设置：
  `cached_apps_freezer` 为 `disabled`（`dumpsys settings`：`pkg:android value:disabled
  default:disabled defaultSystemSet:true`），`use_freezer` 设备配置为空，日志里没有
  `Checking cgroup freezer`，系统没有走到检测内核能力那一步；澎湃 OS 用自己的 Millet
  冻结链路。v1 freezer ROM 不挂载，第三方墓碑在自己的挂载命名空间里挂（如
  `/sys/fs/cgroup/freezer/perf/frozen`）。第三方冻结（v1 或 v2）不会把进程搬进
  `/dev/memcg/freeze-app`，所以 mfz 只在小米自己的冻结链路下生效。Millet 的
  `persist.sys.millet.cgroup=true` 会 tmpfs 覆盖 `/sys/fs/cgroup`，与 Android 16 的分组
  布局冲突，运行中开启会导致系统服务崩溃，不要直接开。
- 未保留任何测试改动：模块 `post-fs-data.sh` 已还原，freezer 挂载和
  `/data/local/tmp` 测试程序已删除。

## r6 镜像（本地）

```
a05392feeedf29c6f5e1b543310d55c2792dc897bb3685e5d8d004ee77c7a79e  Image
3c07c7b79efbcfe6d71d0ac174df40ce0f3e44b46ea19e01780ff48fc2cdc0c8  yudi-5.10.272-20261031-r6-ksu.img
c241d5fe6056e401dcdd28a6f34beb9cc2a8150c1928ac1121005b549a2ed2aa  yudi-5.10.272-20261031-r6-noroot.img
```

## 驱动分层

GKI 内核里没有 `CONFIG_DRM_MSM` 和 `CONFIG_MSM_KGSL`，显示和 GPU 驱动全部由
vendor 模块提供：

- 模块目录 `/vendor_dlkm/lib/modules`，设备上 315 个 `.ko`
- 加载模块 417 个（r6）
- GPU 相关：`msm_kgsl.ko`、`msm_drm.ko`、`msm_performance.ko`、`qcom_dcvs`、
  `gpucc_waipio/diwali`、`llcc_qcom`、`mem_buf_dev`、`secure_buffer`、
  `qcom_iommu_util`、`arm_smmu`
- 本地基线里的 `msm_kgsl.ko` 与设备上的 sha256 一致，CRC 门禁用到的就是当前
  系统模块
- 没有 vendor kernel 源码，只有二进制 `.ko`

所以改 GKI 只能影响调度、内存、热和 IRQ；要改 KGSL 本身需要 Xiaomi/Qualcomm
的 yudi 5.10.160 源码，或者重打包 `vendor_boot`/`vendor_dlkm`。

## GPU 现状

空闲时采样（2026-10-29），温度随负载变化：

| 项目 | 值 |
|---|---|
| 型号 | Adreno730v3 |
| 可用频率 | 900 / 862 / 815 / 765 / 710 / 645 / 580 / 515 / 439 / 364 / 324 / 285 / 220 MHz |
| devfreq | 空闲 285MHz，min 220MHz，max 765MHz |
| governor | `msm-adreno-tz` |
| busmon | `kgsl-busmon`，220–900MHz，`gpubw_mon` |
| 温度 | gpuss-0 约 26°C，gpuss-1 约 26°C（空闲） |
| 属性 | `persist.sys.computility.gpulevel=6`，`persist.sys.force_sw_gles=1` |

硬件能到 900MHz，但 devfreq 的 max 停在 765MHz。可能是 thermal、perfmgr、DT
或厂商策略，先查清来源再决定是否调整。

常用节点：

```
/sys/class/kgsl/kgsl-3d0/gpu_model
/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage
/sys/class/kgsl/kgsl-3d0/devfreq/{cur_freq,min_freq,max_freq,governor,trans_stat}
/sys/class/devfreq/kgsl-busmon/
/sys/class/thermal/thermal_zone38   # gpuss-0
/sys/class/thermal/thermal_zone39   # gpuss-1
```

## 约束

1. 不能破 KMI。每次改动都要跑 7298 个符号、355 个 vendor_boot 和 315 个
   vendor_dlkm 模块的门禁。
2. GPU 驱动不在 GKI 里，改 KGSL 的路线成本很高。
3. boot 的 ramdisk 用的是 Google GKI 认证镜像，深入 vendor 层前建议取一份当前
   系统的 boot 底包对照。
4. SELinux Enforcing，临时调试可以 `setenforce 0`，不要常驻。
5. 热和功耗优先，直接拉高 GPU 上限可能换来降频和耗电。

## 待确认

- 765MHz 上限来自 thermal、perfmgr、DT 还是 `gpulevel`？
- `persist.sys.force_sw_gles=1` 是调试残留还是实际生效？SurfaceFlinger 当前
  显示 Adreno GLES，倾向于是无效属性。
- 是否需要从当前 Android 16 系统提取 boot 底包，与 Google GKI ramdisk 做对照？
- Xiaomi 是否公开 yudi 的 5.10.160 vendor 内核源码？
