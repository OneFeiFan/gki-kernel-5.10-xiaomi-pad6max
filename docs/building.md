# 构建

## 准备源码

`source/` 是在 ACK `android12-5.10-lts` 的 `8059ae2`（2026-10-24，Linux 5.10.272）上应用全部补丁后的内核树，对应 Android 构建环境里的 `common/` 目录。构建还需要 AOSP 的 `build/` 和 `prebuilts/`，它们不在本仓库里。

```sh
git clone --branch pad6max https://github.com/OneFeiFan/gki-kernel-5.10-xiaomi-pad6max.git gki-yudi
mkdir -p ~/kernel-sources/vanilla-root
cp -a gki-yudi/source ~/kernel-sources/vanilla-root/common
```

也可以从基线开始自己应用补丁，方法见 [patches/README.md](../patches/README.md)。

## 编译

```sh
cd ~/kernel-sources/vanilla-root
SKIP_MRPROPER=1 SKIP_CP_KERNEL_HDR=1 \
BUILD_CONFIG=common/build.config.gki.aarch64 \
OUT_DIR=~/kernel-sources/out \
bash build/build.sh -j12
```

产物是 `out/dist/Image`。

发布用的镜像要先清空 `OUT_DIR`，做一次全量构建。增量构建会复用 ThinLTO 缓存，而 `kernel/configs.c` 用 `.incbin` 嵌入的配置不在缓存键里，所以 `/proc/config.gz` 可能还是上一次的配置，看起来像是新配置没有生效。

## 打包 boot 镜像

两个镜像使用同一个 `Image`，区别只在 ramdisk。

ramdisk 取自 Google 的 GKI 认证镜像：

```sh
curl -LO https://dl.google.com/android/gki/gki-certified-boot-android12-5.10-2026-10_r1.zip
unzip -o gki-certified-boot-android12-5.10-2026-10_r1.zip boot-5.10.img
python3 unpack_bootimg.py --boot_img boot-5.10.img --out gki/unpack
```

`unpack_bootimg.py` 和 `mkbootimg.py` 来自 AOSP 的 `system/tools/mkbootimg`：

```sh
git clone https://android.googlesource.com/platform/system/tools/mkbootimg
```

不带 root 的镜像：

```sh
python3 mkbootimg.py --header_version 4 \
  --kernel out/dist/Image \
  --ramdisk gki/unpack/ramdisk \
  --os_version 12.0.0 --os_patch_level 2025-09 \
  -o yudi-noroot.img
```

带 KernelSU 的镜像：先在设备上用 `ksud` 生成带 KernelSU 的 ramdisk，从输出的镜像里解出 ramdisk，再和本项目的 `Image` 组合。`ksud` 取自 KernelSU 的发布页。

```sh
ksud boot-patch -b gki/boot-5.10.img -o /data/local/tmp
python3 mkbootimg.py --header_version 4 \
  --kernel out/dist/Image \
  --ramdisk ksu/ramdisk \
  --os_version 12.0.0 --os_patch_level 2025-09 \
  -o yudi-ksu.img
```

这里要用 `ksud boot-patch`，不能用 `boot-patch-v2`。GKI 认证镜像的内核在 `image_size` 之后带有 BTF 等元数据，v2 会拒绝这样的输入。本项目的 `Image` 还带有 CFI 别名，v2 会报符号不唯一。

## boot 头部的版本字段

`--os_version 12.0.0 --os_patch_level 2025-09` 与原厂 `boot.img` 的头部一致。GKI 认证镜像自带的补丁级别是 `2099-12`，不要沿用。

设备上 KeyAttestation 显示的 boot 补丁级别由 TEE 维护，与这个头部字段无关。保持原厂的值，是为了避免不同引导程序或 Keymaster 实现对异常值的未知处理。
