# 内核构建与验证

## 构建

```sh
cd ~/kernel-sources/vanilla-root
SKIP_MRPROPER=1 SKIP_CP_KERNEL_HDR=1 \
BUILD_CONFIG=common/build.config.gki.aarch64 \
OUT_DIR=~/kernel-sources/out \
bash build/build.sh -j12
```

发布镜像用全量构建（清空 `OUT_DIR`）。增量构建会复用 ThinLTO 缓存，
`kernel/configs.c` 的 `.incbin` 不在缓存键里，`/proc/config.gz` 可能还是上一次
的配置数据，看起来像配置没生效。

## 门禁

```sh
python3 tools/symvers_diff.py out-final/dist/vmlinux.symvers out/dist/vmlinux.symvers
python3 tools/crc_scan.py out/dist/vmlinux.symvers work/vendor_boot/root
python3 tools/crc_scan.py out/dist/vmlinux.symvers work/vendor_dlkm/modules
python3 tools/check_config.py out/common/.config
python3 tools/abi_layout_check.py out/dist/vmlinux
```

期望结果：

- 7298 个导出符号，缺失 0，CRC 差异 0
- vendor_boot 355 个模块、vendor_dlkm 315 个模块，失败 0
- 45 项 CONFIG 满足
- `cfs_rq` 大小 512，`android_vendor_data1` 偏移 344，`cfs_bandwidth` 指针偏移 472

## 镜像

两个镜像用同一份 `Image`：

- 无 root：把 `Image` 和 Google GKI 认证镜像
  （`gki-certified-boot-android12-5.10-*.zip` 里的 `boot-5.10.img`）的 ramdisk
  重新打包。
- 有 root：从 `ksud boot-patch`（v1）生成的 KernelSU 镜像里取出 ramdisk，再和
  本项目的 `Image` 重新打包。

```sh
# 无 root
python3 mkbootimg.py --header_version 4 \
  --kernel out/dist/Image \
  --ramdisk gki/unpack/ramdisk \
  --os_version 12.0.0 --os_patch_level 2025-09 \
  -o yudi-noroot.img

# 有 root（先取得 KernelSU ramdisk，再换成本项目的 Image）
ksud boot-patch -b gki/boot-5.10.img -o /data/local/tmp
python3 mkbootimg.py --header_version 4 \
  --kernel out/dist/Image \
  --ramdisk ksu/ramdisk \
  --os_version 12.0.0 --os_patch_level 2025-09 \
  -o yudi-ksu.img
```

`--os_version 12.0.0 --os_patch_level 2025-09` 与原厂 `boot.img` 的头部一致。
Google 的 GKI 认证镜像自带 `2099-12`，不要沿用它。设备上 KeyAttestation 显示的
boot patch level 由 TEE 维护（2026-02-01），与这个头字段无关；保持原厂值可以
避免不同引导程序或 Keymaster 实现上的未知行为。

`boot-5.10.img` 的内核镜像在 `image_size` 之后带 BTF/元数据，`ksud boot-patch-v2`
会拒绝这种输入；本项目的 `Image` 还带 CFI 别名，v2 会报符号不唯一。因此 root
镜像固定用 v1 生成 ramdisk，再用 `mkbootimg` 组合。

## 行为测试

设备上（root）：

```sh
sh /data/local/tmp/verify_yudi_kernel.sh
/data/local/tmp/vt_tests/ntsync_test
/data/local/tmp/vt_tests/ntsync_owner_test
/data/local/tmp/vt_tests/futex_waitv_test
/data/local/tmp/vt_tests/epoll_wakeup_test
```

期望：NTSync 11/11，owner 2/2，futex_waitv 7/7，epoll 63/63；zram 各算法
32MB 往返一致；CFS 20% 配额下 `nr_throttled` 增长。

`verify_yudi_kernel.sh` 里有两个已知误报：

- ipvlan：脚本在同一个 dummy 上先建 macvlan 再建 ipvlan。两者都要在 lower
  设备上注册 RX handler，只能有一个，`ip link add` 会报
  `Device or resource busy`。换一个独立的 dummy 就正常。
- bbr3 诊断：设备自带的 `ss` 是 iproute2-ss171113，不解析 bbr 信息。用 Termux
  的 iproute2 7.3.0 跑 `ss -tin`，能看到
  `bbr:(bw:...,mrtt:...,pacing_gain:...,cwnd_gain:...)`。

## 已知限制

- `tcp_plb_enabled=0`：PLB 面向数据中心 IPv6 多路径，手机网络没有收益。
- `net_cls` 已启用但未配置：没有默认 classid，需要按容器分流时再写 tc/nft 规则。
- `FHANDLE` 已启用：容器里可跑 systemd，但不要给容器 `CAP_DAC_READ_SEARCH`。
- 内核默认保持 stock：`cubic`、BFQ/cpq、zram `lz4`、KSM 关闭、ADIOS 不作为默认。
  这些由 `yudi-tweaks` 模块在开机后调整。
- 没有开启 `CONFIG_DEBUG_INFO_BTF`，CO-RE eBPF 程序不能用。
- 安全基线是 5.10.272，尚未合并更新的 `android12-5.10-lts`。
