# 内核构建与验证

## 构建

构建命令见仓库根目录 [README](../README.md)。发布镜像必须清空 `OUT_DIR` 做
全量构建：增量构建会复用 ThinLTO 缓存，`kernel/configs.c` 的 `.incbin` 不在
缓存键里，`/proc/config.gz` 可能还是上一次的配置数据，看起来像配置没生效。

当前基线是 ACK `android12-5.10-lts` 的 `8059ae2`（2026-10-24，Linux 5.10.272）；
通用 26 个 + 小米 3 个，共 29 个补丁应用后的源码树是 `2afd8cc8`（通用 26 个的树是
`862d9162`）。`8059ae2` 相对旧基线 `a1eed2e9c` 的净差异只有 `net/can/bcm.c` 的一处
回退；ACK 10 月的 ASB 修复旧基线里已经通过其他提交合入。

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

2026-10-31（r6，`out-xiaomi`，29 补丁）实测结果，与 r5 相同：

- 7298 个导出符号，缺失 0，CRC 差异 0
- vendor_boot 355 个模块、vendor_dlkm 315 个模块，失败 0
- 45 项 CONFIG 满足
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
NTSync/futex/epoll/CFS 的记录来自 2026-10-30 的 r4；2026-10-31 的 r6 做了开机、
门禁和 ExtM/mfz 节点检查，没有重跑这些 selftests。

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

## ExtM 与内存冻结（mfz）

0027 把 zram 换成小米 ExtM 写回实现，0028 加 mfz 策略，0029 修复 0027 从小米源码带入的 memcg 文件
注册位置。r6（29 补丁）实机结果：

- zram 内建，`comp_algorithm` 为 `[lz4kd]`，`backing_dev` 为 `/dev/block/dm-48`
- `/sys/block/zram0` 出现 `mfz_enable`、`mfz_disk_quota`、`mfz_compr_data_size`、
  `mfz_idle_stat`、`bd_stat`；`freeze-app/memory.anno_writeback_enable=2`（init.rc
  写 1，驱动按 5.10 接口存 2）
- 测试进程放进 `freeze-app` 内存组，`MADV_PAGEOUT` 换出 512MB 后
  `mfz_compr_data_size` 为 2,871,990 字节；进程退出后回到约 0
- `mfz_enable=0`、`mfz_disk_quota=524288`，默认由 ROM 的 PerfInit 决定是否启用

冻结器的现状（2026-10-31 实测，测试后已恢复）：本 ROM 的 cgroup2 只绑了 `pids`（因果待确认：cgroup v2 的冻结是内核核心功能、不需要绑定控制器，"只绑了 pids"本身是正常的；关键要看应用进程是否位于 `/sys/fs/cgroup` 的 `uid_*/pid_*` 组里），
而 `cgroups.json` 把 freezer 声明在 cgroup2（文件 `cgroup.freeze`），system_server
初始化失败后记录 `Freezer disabled`，每次开机把 `cached_apps_freezer` 改回
`disabled`，`am freeze` 触发 `CachedAppOptimizer` 空指针。cgroup v1 freezer 可以
手动挂载 `/sys/fs/cgroup/freezer` 并正常冻结（tick 测试冻结 10 秒无输出，解冻恢复）；
第三方 v1 冻结不会把进程搬进 `freeze-app`，所以 mfz 不会参与。Millet 的
`persist.sys.millet.cgroup=true` 会 tmpfs 覆盖 `/sys/fs/cgroup`，与 Android 16 的
pids 布局冲突，运行中开启会导致系统服务崩溃，不要直接开。

## cpuidle governor（TEO）

ACK 的 5.10 基线已经带 TEO（`CONFIG_CPU_IDLE_GOV_TEO=y`），设备上
`available_governors` 是 `menu teo qcom-cpu-lpm`，默认走厂商的 `qcom-cpu-lpm`。

yudi-tweaks 1.6 增加 `GOV` 开关（跟随系统 / teo / qcom-cpu-lpm）：WebUI 保存时
立即写 `current_governor`，重启后由 `service.sh` 再应用；选「跟随系统」时模块
不写 governor。

2026-10-31 熄屏 3 分钟的 A/B（8 核合计，单次采样，设备在充电）：

| governor | C4 时间 | WFI 时间 | 深睡占比 |
| --- | --- | --- | --- |
| qcom-cpu-lpm | 1372.5s | 31.7s | 97.74% |
| teo | 1409.0s | 18.3s | 98.72% |

TEO 的深睡占比略高，没有异常；功耗和唤醒延迟没有测，默认仍保持厂商 governor。

## 灰度与探针

- `CONFIG_WQ_POWER_EFFICIENT_DEFAULT=y`（0023）：默认启用 power-efficient
  unbound workqueues。已确认 `/sys/module/workqueue/parameters/power_efficient=Y`；
  真实功耗 A/B 还没做，去掉补丁即可回退。
- zram 写回（0017）、小米 ExtM（0027）和 mfz（0028/0029）已经落地，不再是探针；
  ExtM 的启用门槛在 PerfInit，见 [ExtM-research.md](ExtM-research.md)。

## 已知限制

- `tcp_plb_enabled=0`：PLB 面向数据中心 IPv6 多路径，手机网络没有收益。
- `net_cls` 已启用但未配置：没有默认 classid，需要按容器分流时再写 tc/nft 规则。
- 懒惰 RCU：5.10 没有这个特性；ztc 的回移也受 `rcu_expedited=1` 限制
  （该参数来自 vendor_boot，不在我们改的 boot.img 里），暂不做。
- `FHANDLE` 已启用：容器里可跑 systemd，但不要给容器 `CAP_DAC_READ_SEARCH`。
- 内核默认保持 stock：`cubic`、BFQ/cpq、zram `lz4`、KSM 关闭、ADIOS 不作为默认。
  这些由 `yudi-tweaks` 模块在开机后调整。
- 冻结器：本 ROM 的 API 冻结器不可用（`cgroups.json` 把 freezer 放在 cgroup2，
  内核 cgroup2 只有 pids）；手动/第三方 v1 freezer 可用，但不会把进程搬进
  `freeze-app`，mfz 只在小米自己的冻结链路下生效。
- 没有开启 `CONFIG_DEBUG_INFO_BTF`，CO-RE eBPF 程序不能用。
- 基线是 ACK `8059ae2`（Linux 5.10.272）；ACK 还没合入 Linux stable 5.10.273，
  安全缺口见 [ecosystem-survey.md](ecosystem-survey.md)。ACK 10 月的 ASB 修复
  旧基线里已经通过其他提交合入，升到 8059ae2 没有新增安全修复。
- UCLAMP 由 ACK 基线自带（`UCLAMP_TASK`、`UCLAMP_TASK_GROUP`，20 个 bucket），
  `sched_util_clamp_min/max` 默认 1024/1024、`min_rt_default=0`；没有改默认值。
