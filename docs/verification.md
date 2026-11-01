# 验证

每次修改补丁后，发布前要通过两类检查：KMI 门禁保证原厂驱动模块还能加载，设备测试保证功能正常。最近一次的结果写在 [CHANGELOG.md](../CHANGELOG.md) 对应版本下。

## KMI 门禁

设备上的驱动模块是按原厂内核编译的二进制文件，它们依赖的导出符号和 CRC 必须保持不变。脚本在 `tools/`，说明见 [tools/README.md](../tools/README.md)。

```sh
OUT=~/kernel-sources/out
BASE=~/kernel-sources/out-base
python3 tools/symvers_diff.py "$BASE/common/vmlinux.symvers" "$OUT/common/vmlinux.symvers"
python3 tools/crc_scan.py "$OUT/common/vmlinux.symvers" vendor_boot_modules vendor_dlkm_modules
python3 tools/check_config.py "$OUT/common/.config"
python3 tools/abi_layout_check.py "$OUT/dist/vmlinux"
```

需要事先准备：

- `BASE`：用同一套构建环境编译未打补丁的基线，得到基线的 `vmlinux.symvers`。
- `vendor_boot_modules` 和 `vendor_dlkm_modules`：从设备的 `vendor_boot` 和 `vendor_dlkm` 分区取出的模块，不随仓库发布。
- `abi_layout_check.py` 需要 `pahole`。

通过的标准：

- 导出符号没有缺失，CRC 没有变化；
- 两个分区的全部模块都能通过 CRC 检查；
- `check_config.py` 列出的必需选项都在；
- `cfs_rq` 等关键结构的大小和字段偏移与原厂一致。

新增的导出符号会被 `CONFIG_TRIM_UNUSED_KSYMS` 裁掉，正常情况下不会出现在 `vmlinux.symvers` 里。

## 设备上的测试

测试程序和检查脚本是维护者本机的工具，不随仓库发布。NTSync 的测试来自上游 selftests，futex 和 epoll 的测试来自内核 selftests，交叉编译成 arm64 后推到设备上运行（需要 root）。

```sh
sh /data/local/tmp/verify_yudi_kernel.sh
/data/local/tmp/vt_tests/ntsync_test
/data/local/tmp/vt_tests/ntsync_owner_test
/data/local/tmp/vt_tests/futex_waitv_test
/data/local/tmp/vt_tests/epoll_wakeup_test
```

期望结果：

| 测试 | 期望 |
| --- | --- |
| NTSync | 11/11，owner 2/2 |
| futex_waitv | 7/7 |
| epoll | 63/63 |
| zram | 每种压缩算法写入 32 MB 再读回，内容一致 |
| CFS 带宽 | 限制为 20% 时，`nr_throttled` 持续增长 |

v6.18 的 NTSync selftests 把 `stress_counter` 改成了 `volatile`，交叉编译时用这个版本。

### 检查脚本的两个误报

- **ipvlan**：脚本在同一个 dummy 设备上先建 macvlan，再建 ipvlan。两者都要在下层设备上注册接收处理函数，而一个设备只能注册一个，所以 `ip link add` 必然报 `Device or resource busy`。换一个独立的 dummy 设备就正常。
- **BBRv3 诊断信息**：设备自带的 `ss` 版本太旧，不解析 BBR 的信息。在 Termux 里 `pkg install iproute2` 后运行 `ss -tin`，能看到 `bbr:(bw:...,mrtt:...,pacing_gain:...,cwnd_gain:...)`。

## 改动类型对应的额外测试

| 改动 | 额外要测的 |
| --- | --- |
| 挂起、空闲、RCU 相关 | 拔掉 USB 和充电线待机 8 小时，比较掉电，并检查 `/sys/power/suspend_stats` 的失败次数 |
| 内存回收、zram | 打开大量应用制造内存压力，检查 `/proc/vmstat` 的回收和换出计数，以及有没有 OOM |
| 网络 | 反复开关 Wi-Fi、移动数据和热点，反复创建和销毁容器的网络命名空间 |
| 存储、文件系统 | 大文件顺序读写和小文件随机读写；f2fs 改动后检查 `dmesg` 有无报错 |

连着 USB 时设备不会进入挂起，待机测试的数据无效。
