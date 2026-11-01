# 内核构建与验证

## 构建

构建命令见仓库根目录 [README](../README.md)。发布镜像必须清空 `OUT_DIR` 做
全量构建：增量构建会复用 ThinLTO 缓存，`kernel/configs.c` 的 `.incbin` 不在
缓存键里，`/proc/config.gz` 可能还是上一次的配置数据，看起来像配置没生效。

当前基线是 ACK `android12-5.10-lts` 的 `8059ae2`（2026-10-24，Linux 5.10.272）；
`series` 99 个通用补丁的树是 `8f65209b...`，`series.xiaomi` 103 个（通用 99 + 小米 4）
的树是 `7f30604d...`。`8059ae2` 相对旧基线 `a1eed2e9c` 的净差异
只有 `net/can/bcm.c` 的一处回退；ACK 10 月的 ASB 修复旧基线里已经通过其他提交合入。

## 门禁

脚本在 `tools/`，用法见 [tools/README.md](../tools/README.md)：

```sh
OUT=~/kernel-sources/out
BASE=~/kernel-sources/out-base
python3 tools/symvers_diff.py "$BASE/common/vmlinux.symvers" "$OUT/common/vmlinux.symvers"
python3 tools/crc_scan.py "$OUT/common/vmlinux.symvers" vendor_boot_modules vendor_dlkm_modules
python3 tools/check_config.py "$OUT/common/.config"
python3 tools/abi_layout_check.py "$OUT/dist/vmlinux"
```

基线 symvers 需要用同一套 `build/` 环境编译 5.10.272 基线得到；两个模块目录
从设备的 `vendor_boot` 和 `vendor_dlkm` 取，不随仓库发布；布局检查需要
`pahole`。

2026-11-01（r16，`out-xiaomi`）实测结果：

- 7298 个导出符号，缺失 0，CRC 差异 0；新增 RCU 导出被 `CONFIG_TRIM_UNUSED_KSYMS` 裁掉，extra 0
- vendor_boot 355 个模块、vendor_dlkm 315 个模块，失败 0（合计 670）
- 47 项 CONFIG 满足
- `cfs_rq` 大小 512，`android_vendor_data1` 偏移 344，`cfs_bandwidth` 指针偏移 472

## 镜像

两个镜像用同一份 `Image`。ramdisk 来自 Google GKI 认证镜像
（`android12-5.10-2026-10`），内核是本项目编译的。

```sh
curl -LO https://dl.google.com/android/gki/gki-certified-boot-android12-5.10-2026-10_r1.zip
unzip -o gki-certified-boot-android12-5.10-2026-10_r1.zip boot-5.10.img
python3 unpack_bootimg.py --boot_img boot-5.10.img --out gki/unpack
```

`unpack_bootimg.py` 和 `mkbootimg.py` 来自 AOSP `system/tools/mkbootimg`：

```sh
git clone https://android.googlesource.com/platform/system/tools/mkbootimg
```

```sh
# 无 root
python3 mkbootimg.py --header_version 4 \
  --kernel out/dist/Image \
  --ramdisk gki/unpack/ramdisk \
  --os_version 12.0.0 --os_patch_level 2025-09 \
  -o yudi-noroot.img

# 有 root：先在设备上生成 KernelSU ramdisk，再换成本项目的 Image
ksud boot-patch -b gki/boot-5.10.img -o /data/local/tmp
python3 mkbootimg.py --header_version 4 \
  --kernel out/dist/Image \
  --ramdisk ksu/ramdisk \
  --os_version 12.0.0 --os_patch_level 2025-09 \
  -o yudi-ksu.img
```

`ksud` 从 KernelSU 的 release 里取，在设备上运行；`ksu/ramdisk` 是从它输出的
镜像里解出来的 ramdisk。

`--os_version 12.0.0 --os_patch_level 2025-09` 与原厂 `boot.img` 的头部一致。
Google 的 GKI 认证镜像自带 `2099-12`，不要沿用它。设备上 KeyAttestation 显示的
boot patch level 由 TEE 维护（2026-02-01），与这个头字段无关；保持原厂值可以
避免不同引导程序或 Keymaster 实现上的未知行为。

`boot-5.10.img` 的内核镜像在 `image_size` 之后带 BTF/元数据，`ksud boot-patch-v2`
会拒绝这种输入；本项目的 `Image` 还带 CFI 别名，v2 会报符号不唯一。因此 root
镜像固定用 v1 生成 ramdisk，再用 `mkbootimg` 组合。

## 行为测试

设备上（root）的测试二进制和整机检查脚本是维护者的本机工具，不随仓库发布。
NTSync/futex/epoll/CFS 的记录来自 2026-10-30 的 r4；2026-11-01 的 r16 做了开机、
KMI 门禁、RCU 开关/churn 和 zram/BBR 节点检查，没有重跑这些 selftests。

```sh
sh /data/local/tmp/verify_yudi_kernel.sh
/data/local/tmp/vt_tests/ntsync_test
/data/local/tmp/vt_tests/ntsync_owner_test
/data/local/tmp/vt_tests/futex_waitv_test
/data/local/tmp/vt_tests/epoll_wakeup_test
```

NTSync 测试来自上游 selftests（v6.18 的 `stress_counter` 已改成 `volatile`），
futex/epoll 来自内核 selftests，交叉编译成 arm64 后推到设备上。

期望：NTSync 11/11，owner 2/2，futex_waitv 7/7，epoll 63/63；zram 各算法
32MB 往返一致；CFS 20% 配额下 `nr_throttled` 增长。

`verify_yudi_kernel.sh` 里有两个已知误报：

- ipvlan：脚本在同一个 dummy 上先建 macvlan 再建 ipvlan。两者都要在 lower
  设备上注册 RX handler，只能有一个，`ip link add` 会报
  `Device or resource busy`。换一个独立的 dummy 就正常。
- bbr3 诊断：设备自带的 `ss` 是 iproute2-ss171113，不解析 bbr 信息。Termux 里
  `pkg install iproute2` 后跑 `ss -tin`，能看到
  `bbr:(bw:...,mrtt:...,pacing_gain:...,cwnd_gain:...)`。

## zstd 1.5.7

`lib/zstd` 升级到 1.5.7（来源 ztc1997 的 android12-5.10 树），目录改为
`common/`、`compress/`、`decompress/`，调用者（crypto、f2fs、btrfs、
squashfs、incfs、pstore、unzstd）切到小写 `zstd_*` API。

- 设备实测：zram 切到 `zstd` 后 32MB 随机数据写入/读回 md5 一致
- `vmlinux.symvers` 仍是 7298 个符号、CRC 差异 0；zstd 符号不在 KMI 白名单，未导出
- 5.10 的 EROFS 不支持 zstd，收益只体现在 zram、f2fs、btrfs 和 initramfs 解压

## Kcompressd

加入 Kcompressd（来源 ztc1997/Pzqqt）：kswapd 把要写到 zram 的匿名页交给
per-node 的 kcompressd 线程，压缩和写回不再占用回收线程。

- 状态放在 `include/linux/kcompressd.h` 的 `kcompress_data[]`，`pglist_data`
  和 `mmzone.h` 都不动，KMI 不变
- 只对 `SWP_SYNCHRONOUS_IO`（zram）且由 kswapd 发起的匿名页写回生效
- 2026-10-30 实机（r4）：ksu 421 个模块、noroot 419 个；10GB 匿名内存压力下
  `pswpout` 增加约 238 万页，kcompressd CPU 90→449 ticks、kswapd 149→580，
  无 OOM/panic

## cpuidle governor（TEO）

ACK 的 5.10 基线已经带 TEO（`CONFIG_CPU_IDLE_GOV_TEO=y`），设备上
`available_governors` 是 `menu teo qcom-cpu-lpm`，默认走厂商的 `qcom-cpu-lpm`。

yudi-tweaks 2.2 增加 `GOV` 开关（跟随系统 / teo / qcom-cpu-lpm）：WebUI 保存时
立即写 `current_governor`，重启后由 `service.sh` 再应用；选「跟随系统」时模块
不写 governor。

2026-10-31 熄屏 3 分钟的 A/B（8 核合计，单次采样，设备在充电）：

| governor | C4 时间 | WFI 时间 | 深睡占比 |
| --- | --- | --- | --- |
| qcom-cpu-lpm | 1372.5s | 31.7s | 97.74% |
| teo | 1409.0s | 18.3s | 98.72% |

TEO 的深睡占比略高，没有异常；功耗和唤醒延迟没有测，默认仍保持厂商 governor。

2026-11-01 又做了 PELT multiplier 的 16 分钟亮屏 ABBA（1 vs 2）：冷启动差异
-1.2%/-1.4%/0.0%，p=0.40/0.55/1.00，UI 帧和 CPU 频率驻留一致；结论保持默认 `1`，
不把 `2` 写进 yudi-tweaks。8 小时待机那一轮因为 USB/adb 的 `ssusb` wakelock
没有进入 suspend，数据作废，需要拔掉 USB/充电线重跑。

## RCU 惰性回调（r14）

r14 加入 ACK android14-5.15 路线的 RCU 惰性回调（`16-rcu/0091-0102`，12 个补丁）：
旧 5.10 惰性核心 + 开机/挂起 `rcu_async_hurry_nesting` + 可写运行时开关
`/sys/module/rcutree/parameters/enable_rcu_lazy`（默认 `N`，0644）+ 收缩器修正 +
`call_rcu_hurry` 调用点。配置 `CONFIG_RCU_LAZY=y`、`CONFIG_RCU_LAZY_DEFAULT_OFF=y`；
本机 `rcu_nocbs=0-7`。KMI 数字见上；开关写 1/0 正常，5000 文件 churn 无 RCU stall。
全量审计后又补了 `drivers/scsi/scsi_error.c` 的 `call_rcu_hurry()`（r16），
避免 SCSI/UFS 错误恢复被惰性拖慢；IPOIB/AF_RXRPC 的条件风险当前配置未构建。

## SSG（可选，不默认）

SSG 来自三星 SM-S908B 源码（ztc1997 移植），独立分支 `ssg-r14`、提交
`ba45f1858`，补丁在 `refs-ssg-2026-11-01/0103-ssg-iosched.patch`。`elevator.c`
改默认的 hunk 已丢弃，sda 默认仍是 cpq；构建/KMI 门禁全过。短测没有一致收益，
顺序写反而低约 18%，所以不设默认、不并入默认 series。

## 灰度与探针

- `CONFIG_WQ_POWER_EFFICIENT_DEFAULT=y`（0024）：默认启用 power-efficient
  unbound workqueues。已确认 `/sys/module/workqueue/parameters/power_efficient=Y`；
  真实功耗 A/B 还没做，去掉补丁即可回退。
- `CONFIG_ZRAM_WRITEBACK=y`（0017）：上游写回；小米 PerfInit 用它挂 ExtM 写回设备，ExtM 写回逻辑由 `xiaomi/0027` 提供。
  `backing_dev`、`writeback*`、`bd_stat` 等节点；ExtM 是否真正启动取决于
  PerfInit 的启动门槛，见 [ExtM-research.md](ExtM-research.md)。

## 已知限制

- `tcp_plb_enabled=0`：PLB 面向数据中心 IPv6 多路径，手机网络没有收益。
- `net_cls` 已启用但未配置：没有默认 classid，需要按容器分流时再写 tc/nft 规则。
- RCU 惰性回调：已加入 r14，但默认关闭；需要时写 `enable_rcu_lazy=1`。旧 ztc 回移
  受 `rcu_expedited=1` 限制，未采用。
- `FHANDLE` 已启用：容器里可跑 systemd，但不要给容器 `CAP_DAC_READ_SEARCH`。
- 内核默认保持 stock：`cubic`、BFQ/cpq、zram 内建（Kconfig 默认 `lz4`，实际算法由系统或 yudi-tweaks 设置）、KSM 关闭、ADIOS 不作为默认。
  这些由 `yudi-tweaks` 模块在开机后调整。
- 没有开启 `CONFIG_DEBUG_INFO_BTF`，CO-RE eBPF 程序不能用。
- 启动时有一条 vendor `nanosic_driver` 的 RCU 警告：它在 atomic power-supply
  notifier 里调用会休眠的 `mutex_lock()`；`atomic_notifier_call_chain()` 持有 RCU
  read lock，触发 `tree_plugin.h:297` 的 `WARN_ON_ONCE`。这是 vendor 模块的问题，
  不是 r16 引入，功能正常。
- 基线是 ACK `8059ae2`（Linux 5.10.272）；ACK 还没合入 Linux stable 5.10.273，
  安全缺口见 [ecosystem-survey.md](ecosystem-survey.md)。ACK 10 月的 ASB 修复
  旧基线里已经通过其他提交合入，升到 8059ae2 没有新增安全修复。
- UCLAMP 由 ACK 基线自带（`UCLAMP_TASK`、`UCLAMP_TASK_GROUP`，20 个 bucket），
  `sched_util_clamp_min/max` 默认 1024/1024、`min_rt_default=0`；没有改默认值。
