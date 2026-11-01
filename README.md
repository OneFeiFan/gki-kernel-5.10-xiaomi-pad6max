# yudi GKI 5.10

小米平板 6 Max（yudi，骁龙 8+ Gen 1）的 GKI 内核，基于 Android 通用内核 android12-5.10（Linux 5.10.272）。

它和原厂内核的模块接口（KMI）完全兼容：vendor 分区里的驱动模块原样加载，只需刷入 boot 分区。在此之上，它加入了容器、Wine 和内存管理方面的功能。

## 功能

- **容器**：Docker、LXC 和 Droidspaces 需要的 cgroup、网络和存储功能，包括按容器限制 CPU 用量（CFS 带宽）、checkpoint/restore 和 nftables。
- **Wine 和 Proton**：NTSync、futex_waitv 和 epoll_pwait2。
- **内存**：le9uo 工作集保护、Kcompressd 异步压缩、内建 zram 与 LZ4K/LZ4KD 压缩算法，以及移植自小米开源代码的内存扩展（ExtM）和内存冻结（MFZ）。
- **网络**：BBRv3 拥塞控制。
- **存储**：ADIOS 调度器（可选）、zstd 1.5.7、f2fs 的上游修正。
- **省电**：TEO 空闲调度器的上游改进，RCU 惰性回调（实验性，默认关闭）。

内核保持原厂的默认行为。BBRv3、zram 压缩算法、KSM、ADIOS 等运行时开关由配套的 [yudi-tweaks](https://github.com/OneFeiFan/yudi-ksu-modules) 模块管理。每项功能的作用、默认值和开关方法见 [docs/features.md](docs/features.md)。

## 兼容性

- 设备：小米平板 6 Max 14（yudi）。
- 系统：在 HyperOS 3（Android 16）上使用。设备 vendor 分区来自原厂 OS3.0.6.0。
- Root：每个版本提供两个镜像，一个集成 KernelSU，一个不带 root。两者内核相同，只有 ramdisk 不同。

## 安装

1. 从 [Releases](https://github.com/OneFeiFan/gki-kernel-5.10-xiaomi-pad6max/releases) 下载镜像：`*-ksu.img` 带 KernelSU，`*-noroot.img` 不带 root。
2. 先备份当前的 boot 分区，回退时要用。
3. 刷入当前启动槽位的 boot 分区：

   ```sh
   adb reboot bootloader
   fastboot getvar current-slot          # 输出 a 或 b
   fastboot flash boot_a yudi-5.10.272-<日期>-ksu.img   # 槽位是 b 时改为 boot_b
   fastboot reboot
   ```

不需要改动 `vendor_boot`、`vendor_dlkm` 或 `dtbo`。

**回退**：用同样的命令刷回备份的 boot 镜像。

## 构建

源码在 `source/`，是在基线上应用全部补丁后的完整内核树。补丁本身在 `patches/`。构建和打包镜像的方法见 [docs/building.md](docs/building.md)，发布前的检查见 [docs/verification.md](docs/verification.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [CHANGELOG.md](CHANGELOG.md) | 各版本的改动 |
| [docs/features.md](docs/features.md) | 功能说明、默认值和开关 |
| [docs/known-issues.md](docs/known-issues.md) | 已知问题和尚未充分验证的改动 |
| [docs/building.md](docs/building.md) | 构建内核、打包 boot 镜像 |
| [docs/verification.md](docs/verification.md) | KMI 门禁和设备上的测试 |
| [patches/README.md](patches/README.md) | 补丁的组织方式、依赖和列表 |
| [docs/writing-guide.md](docs/writing-guide.md) | 维护文档时的写作规范 |
| [docs/notes/](docs/notes/) | 开发过程中的调研和记录 |

## 致谢

本内核汇集了以下项目的工作，具体到每个补丁的出处写在补丁说明里。

- [Android 通用内核](https://android.googlesource.com/kernel/common/)：android12-5.10 基线；android14-5.15 的 RCU 惰性回调回移。
- [Linux 内核](https://www.kernel.org/)：大量上游修正与功能回移。
- [小米开源内核](https://github.com/MiCode/Xiaomi_Kernel_OpenSource)：ExtM 与内存冻结。
- [KernelSU](https://github.com/tiann/KernelSU)。
- [SukiSU 补丁集](https://github.com/ShirkNeko/SukiSU_patch)：LZ4K/LZ4KD 与 zram 集成。
- [kernel-workshop-docker](https://github.com/superturtlee/kernel-workshop-docker)：容器相关补丁、LZ4 1.10 与 ARM64 汇编。
- [WildKernels](https://github.com/WildKernels/kernel_patches)：BBRv3 与 NTSync 的 5.10 回移。
- [Droidspaces](https://github.com/Goldzxcbug/Droidspaces_Kernel_patch)：SysV IPC 与 CFS 带宽的 KMI 兼容实现。
- [le9uo](https://github.com/Star-ZER0/le9uo_android12-5.10)（Star-ZER0）：工作集保护。
- [ADIOS](https://github.com/firelzrd/adios)（firelzrd）：IO 调度器。
- [linux-tkg](https://github.com/Frogging-Family/linux-tkg)：futex_waitv 回移。
- ztc1997 的 [android12-5.10 内核](https://github.com/ztc1997/android_gki_kernel_5.10_common)：zstd 1.5.7、Kcompressd，以及 TEO、f2fs 等大量回移的整理。
- Pzqqt 的 [Melt 内核](https://github.com/Pzqqt/android_kernel_xiaomi_marble)：Kcompressd 的 KMI 修正、ADIOS 修正、kmem_cache 池、长按电源键同步的移植。
- Sultan Alsawaf：减少小块分配等一系列小优化。
- [ESK](https://github.com/ESK-Project/android12-5.10-gki)：kmem_cache 池、zram 缓冲区、挂起时的 cpuidle 改动。
- [Templar](https://github.com/Steambot12/Templar-Kernel-GKI-5.10)（Steambot12）：binder 位图查找的回移、le9uo 的 OOM 兜底。
- Panchajanya1999 的 [Pixel 5.10 内核](https://github.com/Panchajanya1999/kernel-5.10)：RCU 惰性回调的 5.10 回移。
- Juhyung Park（arter97）：长按电源键同步文件系统。

## 许可

GPL-2.0，与 Linux 内核相同。
