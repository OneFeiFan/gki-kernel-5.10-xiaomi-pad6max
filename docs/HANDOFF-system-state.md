# 系统状态交接（yudi）

日期：2026-10-29。给后续驱动工作留的现状记录，内核构建和补丁见
[`kernel.md`](kernel.md) 与仓库 `patches/`。除特别说明外，表中的数值都是
2026-10-29 的采样值。

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
| 当前内核 | 5.10.272，见 `uname -r` |

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
| 分支 | `restructured-20261029`（旧 `cfs-bandwidth` 保留） |
| HEAD | `2cdee214e`（15 个功能补丁） |
| 构建输出 | `~/kernel-sources/out-zram` |
| 补丁 | 15 个，基线 `a1eed2e9c`，源码树 `24bbf84f` |
| GitHub | `OneFeiFan/gki-kernel-5.10-xiaomi-pad6max`，`pad6max` 快照分支 |

## 驱动分层

GKI 内核里没有 `CONFIG_DRM_MSM` 和 `CONFIG_MSM_KGSL`，显示和 GPU 驱动全部由
vendor 模块提供：

- 模块目录 `/vendor_dlkm/lib/modules`，设备上 315 个 `.ko`
- 加载模块 420 个
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
