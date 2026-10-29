# ExtM 研究报告（yudi）

日期：2026-10-29。只读研究，未修改设备。目标：判断小米内存扩展（ExtM）能不能在
我们的内建 zram 上恢复，以及需要移植什么。

## 结论

- ExtM 的写回后端仍然是块设备：`system_perf_init` 把 `/data/extm/extm_file`
  做成 dm-linear（失败则 loop），再把 `/dev/block/dm-*` 或 `/dev/block/loopN`
  写进 `/sys/block/zram0/backing_dev`。zram 内核侧只接受块设备，不是直接写
  `/data` 文件。
- system_server 每秒报 `Failed to read kernel info` 的根因已定位到字节码：
  `ExtendMImpl.isKernelSupported()` 读 `/sys/block/zram0/backing_dev`；我们没开
  `CONFIG_ZRAM_WRITEBACK`，文件不存在，读异常后打这条 warning。
- **启动门槛在 zram 之前**：PerfInit 先打印 `This device don't support extm.` 和
  `Skipping losetup for extendable memory.`，之后才检查 `mfz_enable` /
  `writeback_quota`。紧挨着的日志是 `open fail!` 和
  `Can not get Flash health_desc.`。所以只开 WRITEBACK 可能只消掉日志，ExtM
  仍然不会创建 extm_file/backing_dev。
- 公开源码没有厂商 `5.10.237-moon-source-gc30e8025c` 的完整实现。最接近的是
  `MiCode/Xiaomi_Kernel_OpenSource` 的 `spinel-v-oss` 5.10.233（ExtM 核心）；
  `bixi/onyx-v-oss` 6.6.56 有 mfz 特性。100% 还原做不到，只能做功能子集。

## 已验证事实

- 设备内核 `5.10.272-android12-9-g…`，`CONFIG_ZRAM=y`、
  `CONFIG_ZRAM_WRITEBACK` 未开、`CONFIG_MODVERSIONS=y`、
  `CONFIG_MODULE_SIG` 未开、`CONFIG_MODULE_FORCE_LOAD` 未开、`CONFIG_CRYPTO_LZ4KD=y`。
- zram0 16GiB、swap 已启用、算法 `[lz4kd]`。
- `/sys/block/zram0` 缺少 `backing_dev`、`writeback`、`writeback_limit`、
  `writeback_limit_enable`、`idle_stat`、`bd_stat`、`mfz_enable`、
  `mfz_disk_quota`、`mfz_compr_data_size`、`zgroup_enable`。
- 厂商 `/vendor_dlkm/lib/modules/zram.ko`：vermagic
  `5.10.237-moon-source-gc30e8025c`，依赖 zsmalloc，带 `backing_dev` 和
  `ExtM:` 字样；`init.rc` 已给这些 sysfs 做 chown/chmod。
- 设备属性：`persist.miui.extm.enable=1`、`bdsize=6144`、`dm_opt.enable=true`、
  `version=4.0`；`/data/extm` 为空，`/data/mqsas/extm/dailyrecord.txt` 全 0。
- PerfInit 日志顺序：`extm_on: 1` → `extm_file: /data/extm/extm_file` →
  `open fail!` → `Can not get Flash health_desc.` →
  `This device don't support extm.` → `Skipping losetup` →
  `mfz_enable/writeback_quota not exist` → `mkswap/swapon zram0`。
- 健康信息接口现在存在且 root 可读：
  `/sys/class/mi_memory/mi_memory_device/ufshcd0/dump_health_desc`（444）。

## 方案

| 方案 | 内容 | 工作量 | 风险 |
| --- | --- | --- | --- |
| A | 只开 `CONFIG_ZRAM_WRITEBACK`，观察 PerfInit 是否还跳过 ExtM | 0.5 天 | 低；新增 sysfs，不新增导出符号 |
| B | 移植 spinel 5.10.233 的 ExtM 核心 + 从 6.6 回移 mfz 子集 | 核心 3-7 天 | 高；zram 数据路径、`mem_cgroup` 内部字段、启动顺序、lz4kd 冲突 |
| C | 直接用厂商 zram.ko | — | 不可行：vermagic 和 MODVERSIONS 不匹配，`CONFIG_MODULE_FORCE_LOAD` 未开 |
| D | 维持现状（只压缩 swap） | 0 | 零；ExtM 不工作，每秒一条 logcat warning |

A 的判别逻辑：刷入后在下次启动的 PerfInit 日志里看是否还有
`This device don't support extm.`。没有 → 门槛主要是缺 `backing_dev`，可以继续
B；还有 → 门槛在 health_desc/时序/权限，先修启动侧，内核补丁救不了。

## 本次发布带上的探针

0019 已加 `CONFIG_ZRAM_WRITEBACK=y`，作为 A 探针随本次内核一起发布。启动后看：

```sh
ls /sys/block/zram0 | grep -E 'backing_dev|writeback|bd_stat'
cat /sys/block/zram0/backing_dev        # 设置前应为 none
logcat -s ExtM                          # 不应再每秒 Failed to read kernel info
grep PerfInit /data/adb/ksu/log/logcat.log | grep -i extm
ls -l /data/extm
cat /proc/swaps
cat /sys/block/zram0/comp_algorithm     # 仍应为 [lz4kd]
```

## 移植时要处理的关键点（若走 B）

- 本地 lz4kd（commit `d5e0e6837` 那套）必须保留，不能为了 ExtM 丢掉自定义压缩。
- `anno_writeback` 需要给 `struct mem_cgroup` 加 `android_oem_data1` 字段，属于
  内部结构改动，要全量跑 vendor 模块 CRC 门禁。
- `mfz_enable` / `mfz_disk_quota` / `mfz_compr_data_size` 受
  `CONFIG_MI_MEMORY_FREEZE` 保护，我们没这个配置，需要解耦或补 stub。
- `zgroup_enable` 在公开源码里没找到实现；可能可选。
- 厂商模块里的 `kshrink_slabd`、`schedule_bio_write`、`moon_reclaim` 没有公开
  源码，无法 1:1 还原。
- `backing_dev` 必须在 zram initstate 置 1 / swapon 之前设置。

## 参考

- `MiCode/Xiaomi_Kernel_OpenSource`：`spinel-v-oss` 5.10.233
  （`49ff345d71aba889f15a06202b3c31ba24c68bbf`），`bixi-v-oss` / `onyx-v-oss`
  6.6.56（mfz）
- 本地：`/vendor_dlkm/lib/modules/zram.ko`、`/system_ext/xbin/system_perf_init`、
  `/system_ext/framework/miui-services.jar`
- 启动日志：`/data/adb/ksu/log/logcat.log`
