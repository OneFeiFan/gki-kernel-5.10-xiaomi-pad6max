# GPU 驱动交接（yudi）

日期：2026-10-29。给接手的会话看的 GPU/显示现状，跟内核构建、补丁、模块分开。
总交接见 [`HANDOFF-system-state.md`](HANDOFF-system-state.md)，构建与验证见
[`kernel.md`](kernel.md)。

## 一句话现状

GKI 内核里没有 GPU/显示驱动，Adreno 730 全部由小米的 vendor 模块提供，我们只有
二进制 `.ko`，没有 vendor 内核源码。当前设备跑我们编译的 5.10.272 GKI，
`msm_kgsl.ko` 正常工作；已知疑问是 devfreq 的 max 停在 765MHz，硬件最高 900MHz。

## 设备与系统（2026-10-29 采样）

| 项目 | 值 |
| --- | --- |
| 机型 | Xiaomi Pad 6 Max（yudi，SM8475） |
| GPU | Adreno 730 v3（`gpu_model` 读出 `Adreno730v3`） |
| 系统 | Android 16，HyperOS（V816，`OS3.0.304.97.WMHCNXM`） |
| 内核 | 自编译 GKI 5.10.272，`5.10.272-android12-9-gf249115d139a` |
| 启动槽 | `_a`，bootloader 已解锁（orange），SELinux Enforcing |
| 安全补丁 | 系统 2026-08-01，vendor 2026-02-01 |

注意：平板目前没连 adb（2026-10-29 晚）。下面带“采样”的数值要在设备连上后复核。

## 驱动分层（关键约束）

- 内核 `.config` 里 `# CONFIG_DRM_MSM is not set`，也没有 `CONFIG_MSM_KGSL`
- 显示和 GPU 全部由 vendor 模块提供：
  - `/vendor_dlkm/lib/modules`：设备上 315 个 `.ko`
  - `vendor_boot` ramdisk 里还有 355 个
- 本地副本：`work/vendor_dlkm/modules/`、`work/vendor_boot/root/lib/modules/`
- `msm_kgsl.ko` 的 vermagic 是 `5.10.160-gki-gd28eeb36ae86`，靠 GKI KMI 跑在我们的
  5.10.272 上；依赖 `qcom_iommu_util,qcom-scm,msm_performance,cmd-db,llcc-qcom,
  clk-qcom,qcom-dcvs,minidump,mdt_loader,secure_buffer,mem_buf_dev`
- 没有 yudi 的 vendor 内核源码，只有二进制。改 GKI 只能影响调度、内存、热和
  IRQ；改 KGSL 本身只能找小米/高通源码，或重打包 `vendor_boot`/`vendor_dlkm`

本地 `.ko` 和当初设备上的一致（做过 sha256 对比），CRC 门禁用的就是这套模块。
设备连上后可以重新核对。

## 当前 GPU 状态（空闲采样 2026-10-29）

| 项目 | 值 |
| --- | --- |
| 型号 | `Adreno730v3` |
| 可用频率 | 900 / 862 / 815 / 765 / 710 / 645 / 580 / 515 / 439 / 364 / 324 / 285 / 220 MHz |
| devfreq | cur 285MHz（空闲），min 220MHz，max 765MHz |
| governor | `msm-adreno-tz` |
| busmon | `kgsl-busmon`，220–900MHz，`gpubw_mon` |
| 温度 | gpuss-0 ≈26°C，gpuss-1 ≈26°C（空闲） |
| 属性 | `persist.sys.computility.gpulevel=6`，`persist.sys.force_sw_gles=1` |

核心疑问：硬件能到 900MHz，devfreq 的 `max_freq` 却停在 765MHz。可能的来源：
thermal 限制、perfmgr/powerhint、DT 里的 OPP/冷却映射、`gpulevel` 属性、厂商
策略。目前没有定论，这是接手后优先查的第一件事。

## 常用检查命令（设备连上后）

```sh
adb shell cat /sys/class/kgsl/kgsl-3d0/gpu_model
adb shell cat /sys/class/kgsl/kgsl-3d0/gpu_busy_percentage
adb shell cat /sys/class/kgsl/kgsl-3d0/devfreq/available_frequencies
adb shell cat /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq
adb shell cat /sys/class/kgsl/kgsl-3d0/devfreq/min_freq
adb shell cat /sys/class/kgsl/kgsl-3d0/devfreq/max_freq
adb shell cat /sys/class/kgsl/kgsl-3d0/devfreq/governor
adb shell cat /sys/class/kgsl/kgsl-3d0/devfreq/trans_stat
adb shell cat /sys/class/thermal/thermal_zone38/temp    # gpuss-0
adb shell cat /sys/class/thermal/thermal_zone39/temp    # gpuss-1
adb shell getprop persist.sys.computility.gpulevel
adb shell getprop persist.sys.force_sw_gles
adb shell su -c 'lsmod | grep -E "kgsl|msm|gpucc|llcc|dcvs"'
```

本地模块信息：

```sh
modinfo work/vendor_dlkm/modules/msm_kgsl.ko
strings -a work/vendor_dlkm/modules/msm_kgsl.ko | grep -m1 vermagic
```

原始采集在 `work/state-2026-10-29.txt` 的 `===== gpu props =====` 和
`===== kgsl sysfs =====` 两段。

## 进一步排查方向（建议顺序）

1. 先确认 765MHz 是谁限制的：
   - 看 thermal zone 38/39 的温度和 cooling device 绑定
   - 看 kgsl devfreq 的 `available_governors` 和 `trans_stat`
   - 读 DT：从 `vendor_boot`/`dtb.img` 或设备 `/proc/device-tree` 找 GPU OPP 表、
     cooling-maps、`qcom,gpu-*` 属性
   - 看 `/vendor/etc` 下的 perfmgr/powerhint 配置（可能是二进制/加密）
   - 看 `persist.sys.computility.gpulevel` 是谁在读（小米 framework/游戏助手？）
2. 不要先硬拉 `max_freq` 到 900MHz：可能触发 thermal 降频、功耗和稳定性问题，
   先确认限制来源。
3. 如果只是属性/策略限制，优先在 userspace 解决（KernelSU 模块/属性），不要动
   内核。
4. 如果必须改 KGSL：需要 vendor 源码或重打包 `vendor_dlkm`/`vendor_boot`，
   成本高，先评估。

## 约束与红线

1. 不能破 KMI：7298 个导出符号、355 个 `vendor_boot` 和 315 个 `vendor_dlkm`
   模块必须继续加载，CRC 不匹配 0。
2. 不要随意改 `vendor_boot`、`vendor_dlkm`、`dtbo`。
3. SELinux Enforcing，临时 `setenforce 0` 只用于调试，不要常驻。
4. 热和功耗优先，直接拉高 GPU 上限可能换来降频和耗电。
5. 设备是解锁 + orange；刷 boot 失败要有回退镜像。

## 已验证 / 未验证

已验证：

- `msm_kgsl.ko` 等 vendor 模块能在我们的 GKI 上加载（420 个模块，CRC 不匹配 0）
- 本地 `msm_kgsl.ko` 与设备上的 sha256 一致（之前核对）
- 频率、温度、属性是 2026-10-29 的采样

未验证 / 待确认：

- 765MHz 上限的真实来源（thermal、perfmgr、DT 还是 `gpulevel`）
- `persist.sys.force_sw_gles=1` 是否真的生效（之前判断倾向无效）
- 设备当前状态（adb 掉线，需重连复核）
- 是否有公开的 yudi 5.10.160 vendor 内核源码
