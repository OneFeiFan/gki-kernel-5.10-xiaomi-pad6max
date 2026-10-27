# 系统状态交接（yudi / Xiaomi Pad 6 Max）

日期：2026-10-27
用途：给后续驱动优化（先看 GPU）留一份可复现的现状记录。内核补丁本身见
`~/kernel-sources/vanilla-root/common/README.gki-docker.md` 和 `patches/`。

## 1. 设备与系统

| 项目 | 值 |
|---|---|
| 机型 | Xiaomi Pad 6 Max，代号 yudi，SoC SM8475 |
| GPU | Adreno 730 v3 |
| 系统 | Android 16，HyperOS `V816`，build `OS3.0.304.97.WMHCNXM` |
| 指纹 | `Xiaomi/yudi/yudi:16/BP2A.250605.031.A3/OS3.0.304.97.WMHCNXM:user/release-keys` |
| 安全补丁 | 2026-02-01 |
| 屏幕 | 1800×2880，最高 120Hz，360dpi，面板 `qcom,mdss_dsi_m80_42_02_0a_dsc_video` |
| 内存 | 15881904 kB（约 15.9GB），当前 MemFree 约 6.9GB，MemAvailable 约 10.9GB |
| CPU | 8 核，小核最高 2.016GHz，中核 2.7456GHz，大核 3.1872GHz，governor `walt` |
| 启动槽 | `_a`，bootloader 已解锁（verified boot orange），SELinux `Enforcing` |
| 当前内核 | `5.10.272-android12-9-geba364b9a173-dirty` |

两个容易踩的点：

1. **系统是 Android 16，不是 Android 12。** 内核源码来自 `android12-5.10-lts`，
   设备 vendor 模块却是按 `5.10.160-gki` 编译的。现在靠 GKI KMI 兼容跑通，不代表
   可以直接拿 Android 12 的 vendor 东西替换。
2. **boot 镜像的 cmdline 还带着旧指纹** `yudi:12/OS3.0.6.0.VMHCNXM:user`，
   而系统实际是 Android 16 / OS3.0.304.97。boot 镜像是早期从旧系统上取的底包重打包的。
   目前能开机，但做 vendor/驱动层改动前，建议先从当前 boot 分区重新取一份底包。

## 2. 内核项目状态

| 项目 | 位置 / 值 |
|---|---|
| 源码 | `~/kernel-sources/vanilla-root/common` |
| 分支 | `gki-docker-phase2` |
| 当前 HEAD | `c87cf87d8`（docs/patches；内核代码对应 `78b90ee4a`） |
| 构建输出 | `~/kernel-sources/out-zram` |
| 当前镜像 | `C:\Users\OneFeiFan\boot_272_epoll.img` |
| 回退镜像 | `C:\Users\OneFeiFan\boot_backup_pre_epoll.img` |
| 已知可开机备份 | `boot_272_bbr3d.img`、`boot_272_futex.img` 等 |
| GitHub | `https://github.com/OneFeiFan/gki-kernel-5.10-xiaomi-pad6max`，快照 `c314cfc64` |
| 补丁 | `common/patches/`，33 个，按 `patches/series` 顺序应用 |
| 补丁基线 | `a1eed2e9c`（5.10.272 merge） |

构建：

```sh
cd ~/kernel-sources/vanilla-root
SKIP_MRPROPER=1 SKIP_CP_KERNEL_HDR=1 \
BUILD_CONFIG=common/build.config.gki.aarch64 \
OUT_DIR=~/kernel-sources/out-zram \
bash build/build.sh -j12
```

门禁：

```sh
python3 tools/symvers_diff.py \
  out-final/dist/vmlinux.symvers out-zram/dist/vmlinux.symvers
python3 tools/crc_scan.py \
  out-zram/dist/vmlinux.symvers work/vendor_boot/root
```

期望：7298 个导出符号缺失 0、CRC 差异 0；355 个 vendor_boot 模块 0 失败。

刷机：

```sh
adb reboot bootloader
fastboot flash boot_a boot_272_epoll.img
fastboot reboot
```

只动 boot_a；vendor_boot、vendor_dlkm、dtbo 没有改。

## 3. 驱动分层

### 内核 GKI 层

- `CONFIG_DRM_MSM` **没有开**；GKI 里没有高通 display/KGSL 驱动。
- `CONFIG_MSM_KGSL` 不存在，GPU 驱动完全由 vendor 模块提供。
- GKI 提供的是通用块：DRM 核心、DMA-BUF、devfreq、thermal、cgroup、CPU freq 等。
- 所以改 GKI 内核配置只能间接影响 GPU（调度、内存、热、IRQ），不能直接改 KGSL。

### Vendor 内核模块层

- 模块目录：`/vendor_dlkm/lib/modules`（`/vendor/lib/modules` 是它的软链）。
- 设备上有 315 个 `.ko`；本地基线 `~/kernel-sources/work/vendor_boot/root` 里有 355 个。
- 当前加载模块数：421（`/proc/modules`；`lsmod` 会多一行表头）。
- GPU 相关：
  - `msm_kgsl.ko`：1,851,392 字节，vermagic `5.10.160-gki-gd28eeb36ae86`
  - `msm_drm.ko`：显示/DRM
  - `msm_performance.ko`、`qcom_dcvs`、`gpucc_waipio/diwali`、`llcc_qcom`
  - `mem_buf_dev`、`secure_buffer`、`qcom_iommu_util`、`arm_smmu`
- 本地基线里的 `msm_kgsl.ko` 和设备上的 sha256 完全一致：
  `71d90cc1df7da38f71c4f1277616cf1aa8cb4956761ca31b421c11eb828900be`
  这说明 CRC 门禁用的确实是当前系统模块，不是旧包。
- 目前没有 vendor kernel 源码，只有二进制 `.ko`。要改 KGSL 本身，需要 Xiaomi/Qualcomm
  的 yudi 5.10.160 源码，或者做 vendor_boot/vendor_dlkm 重打包，风险很高。

### GPU 用户态

- GLES：`Adreno (TM) 730, OpenGL ES 3.2 V@0762.10`
  （`GIT@1394a2c7a8, Id12349e41b, 1708672989`，带 `LHMOD-v1-GAME` 标记）
- GPU 驱动包：`com.qualcomm.qti.gpudrivers.taro.api32`
- `ro.hardware.egl=adreno`，`ro.hardware.vulkan=adreno`
- 关键库：`libgsl.so`、`libllvm-qcom.so`、`libllvm-qgl.so`、`libadreno_utils.so`
- 固件：`/vendor/firmware/a730_sqe.fw`、`a730_zap.*`

### 其他驱动

- 显示/触控：`msm_drm`、`nt36532_touch`
- 相机：`camera`、`msm_eva`、`msm_cvp`、`msm_video`
- Wi-Fi/连接：`cnss2`、`icnss2`、`qmi_helpers`、`pci_msm_drv`
- 音频：`wcd938x_dlkm`、`mbhc_dlkm`、`machine_dlkm` 等
- 存储：`ufs_qcom`、`sdhci_msm`
- 电源/热：`qcom_dcvs`、`msm_performance`、`perfmgr`、`thermal_pause`、`mi_thermal_interface`

## 4. GPU 当前状态

| 项目 | 值 |
|---|---|
| GPU 型号 | `Adreno730v3` |
| 可用频率 | 900 / 862 / 815 / 765 / 710 / 645 / 580 / 515 / 439 / 364 / 324 / 285 / 220 MHz |
| devfreq 当前 | 285MHz（空闲） |
| devfreq min / max | 220MHz / **765MHz** |
| governor | `msm-adreno-tz`（唯一可用） |
| busmon | `kgsl-busmon`，min 220 / max 900，governor `gpubw_mon` |
| 当前 GPU busy | 约 3% |
| GPU 温度 | gpuss-0 25.7°C，gpuss-1 26.1°C（空闲） |
| 频率驻留 | 765MHz 约 653.6s，285MHz 约 276.7s，220MHz 约 26.1s |
| 相关属性 | `persist.sys.computility.gpulevel=6`，`persist.sys.force_sw_gles=1` |

最值得先查的问题：**硬件可用到 900MHz，但 devfreq 的 max 被限在 765MHz。**
可能是 thermal、perfmgr、DT 或厂商策略，不一定是驱动 bug。先把原因查清楚，再决定要不要动。

常用节点：

```
/sys/class/kgsl/kgsl-3d0/gpu_model
/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage
/sys/class/kgsl/kgsl-3d0/gpu_available_frequencies
/sys/class/kgsl/kgsl-3d0/gpu_clock_stats
/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq
/sys/class/kgsl/kgsl-3d0/devfreq/min_freq
/sys/class/kgsl/kgsl-3d0/devfreq/max_freq
/sys/class/kgsl/kgsl-3d0/devfreq/governor
/sys/class/kgsl/kgsl-3d0/devfreq/trans_stat
/sys/class/devfreq/kgsl-busmon/
/sys/class/thermal/thermal_zone38   # gpuss-0
/sys/class/thermal/thermal_zone39   # gpuss-1
```

## 5. 状态采集

脚本：`~/kernel-sources/tools/collect_system_state.sh`
原始快照：`~/kernel-sources/work/state-2026-10-27.txt`

采集：

```sh
adb push tools/collect_system_state.sh /data/local/tmp/
adb shell su -c 'sh /data/local/tmp/collect_system_state.sh > /data/local/tmp/state.txt'
adb pull /data/local/tmp/state.txt
```

脚本覆盖 props、kernel cmdline、KGSL sysfs、devfreq、thermal、模块、存储、SELinux、sysctl。
输出约 75KB，适合直接归档，不要整段贴进聊天。

## 6. 做驱动优化前的约束

1. **KMI 不能破。** 每次内核改动跑 7298 符号和 355 模块门禁；vendor 模块按
   `5.10.160-gki` 编译，CRC 对不上就加载失败。
2. **GPU 驱动不在 GKI 里。** 改 KGSL 需要 vendor 源码或重打包 vendor 分区；
   改 GKI 只能影响调度、内存、热和 IRQ。
3. **boot 镜像底包偏旧。** cmdline 还是 Android 12/OS3.0.6.0 的指纹；深入 vendor
   层之前建议从当前系统重新提取 boot 底包。
4. **SELinux Enforcing。** 临时调试可以 `setenforce 0`，但不要做成常驻。
5. **热和功耗优先。** 直接把 GPU max 拉到 900MHz 可能换来降频、耗电和稳定性问题，
   先做负载测试和温度记录。

## 7. GPU 优化候选（按顺序）

1. **建立基线**：跑一个稳定的 GPU 负载，记录频率、busy、温度、帧时间、功耗。
   没有基线就不要改参数。
2. **查清 765MHz 上限**：看 thermal cooling device、perfmgr 配置、DT 里的
   `qcom,initial-pwrlevel` / `qcom,gpu-pwrlevels`，以及 `persist.sys.computility.gpulevel`
   的实际作用。
3. **调 devfreq/thermal**：确认 `min_freq`/`max_freq` 是否可写；可临时 pin 频率做对比，
   但不要长期写死。
4. **看 userspace 驱动**：确认 taro 是否有更新的 Adreno 驱动包（API32 之后），
   对比 GLES/Vulkan 版本和游戏表现；这是厂商签名包，不改内核。
5. **看 CPU/GPU 协同**：`walt`、`perfmgr`、`msm_performance`、`qcom_dcvs` 的频点策略，
   有时 GPU 不满是因为 CPU 先降频或 bus 带宽先限。
6. **最后才考虑 vendor 模块**：拿 Xiaomi/Qualcomm 的 yudi 5.10.160 源码重建
   `msm_kgsl.ko`，再做 vendor_boot/vendor_dlkm 重打包和 AVB；这是高风险路线。

## 8. 待确认

- 765MHz 上限来自哪里：thermal、perfmgr、DT 还是 `gpulevel`？
- `persist.sys.force_sw_gles=1` 是调试残留还是真的在强制软件 GLES？
  （SurfaceFlinger 当前显示 Adreno GLES，倾向于是无效/调试属性。）
- 是否要从当前 Android 16 系统重新提取 boot 底包，替换掉旧 cmdline/ramdisk？
- Xiaomi 是否公开 yudi 的 5.10.160 vendor 内核源码？

## 9. 相关文件

- 内核源码：`~/kernel-sources/vanilla-root/common`
- 构建输出：`~/kernel-sources/out-zram`
- vendor 模块基线：`~/kernel-sources/work/vendor_boot/root`
- 原始状态快照：`~/kernel-sources/work/state-2026-10-27.txt`
- 采集脚本：`~/kernel-sources/tools/collect_system_state.sh`
- KernelSU 模块项目：`~/yudi-ksu-modules`
- PC 镜像：`C:\Users\OneFeiFan\boot_272_epoll.img`、`C:\Users\OneFeiFan\boot_backup_pre_epoll.img`
