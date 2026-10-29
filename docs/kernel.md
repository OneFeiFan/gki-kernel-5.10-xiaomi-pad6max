# 内核构建与验证

## 构建

构建命令见仓库根目录 [README](../README.md)。发布镜像必须清空 `OUT_DIR` 做
全量构建：增量构建会复用 ThinLTO 缓存，`kernel/configs.c` 的 `.incbin` 不在
缓存键里，`/proc/config.gz` 可能还是上一次的配置数据，看起来像配置没生效。

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

2026-10-29 实测结果：

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
2026-10-29 的记录：

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

## 灰度与探针

- `CONFIG_WQ_POWER_EFFICIENT_DEFAULT=y`（0023）：默认启用 power-efficient
  unbound workqueues。已确认 `/sys/module/workqueue/parameters/power_efficient=Y`；
  真实功耗 A/B 还没做，去掉补丁即可回退。
- `CONFIG_ZRAM_WRITEBACK=y`（0024）：小米 ExtM 的 A 探针。打开后 zram 会出现
  `backing_dev`、`writeback*`、`bd_stat` 等节点；ExtM 是否真正启动取决于
  PerfInit 的启动门槛，见 [ExtM-research.md](ExtM-research.md)。

## 已知限制

- `tcp_plb_enabled=0`：PLB 面向数据中心 IPv6 多路径，手机网络没有收益。
- `net_cls` 已启用但未配置：没有默认 classid，需要按容器分流时再写 tc/nft 规则。
- `FHANDLE` 已启用：容器里可跑 systemd，但不要给容器 `CAP_DAC_READ_SEARCH`。
- 内核默认保持 stock：`cubic`、BFQ/cpq、zram `lz4`、KSM 关闭、ADIOS 不作为默认。
  这些由 `yudi-tweaks` 模块在开机后调整。
- 没有开启 `CONFIG_DEBUG_INFO_BTF`，CO-RE eBPF 程序不能用。
- 安全基线是 5.10.272，尚未合并更新的 `android12-5.10-lts`。
