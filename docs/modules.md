# KernelSU 模块

模块仓库：<https://github.com/OneFeiFan/yudi-ksu-modules>

| 模块 | 版本 | 说明 |
| --- | --- | --- |
| `yudi-tweaks` | 1.5 | 运行时开关和状态页：sysctl、BBRv3、le9uo、zram、KSM、ADIOS、DAMON |
| `ntsync` | 1.1 | 按 `/sys/class/misc/ntsync/dev` 创建 `/dev/ntsync` |

`yudi-tweaks` 默认只开安全项：sysctl 上限、BBRv3、le9uo、zram `lz4kd`。KSM、
ADIOS、DAMON 在 WebUI 里手动打开。配置写到 `/data/adb/yudi-tweaks.conf`，重启后
生效。zram 切换会先 `swapoff` + `reset`，swap 使用量高时跳过。

CPU 限制（`Droidspaces --cpus`）来自内核的 CFS 带宽支持，WebUI 只显示状态。

`ntsync` 从 `/sys/class/misc/ntsync/dev` 读主次设备号创建节点。minor 是内核
动态分配的，不能写死。
