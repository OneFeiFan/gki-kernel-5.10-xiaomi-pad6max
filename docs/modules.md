# KernelSU 模块

模块仓库：<https://github.com/OneFeiFan/yudi-ksu-modules>

| 模块 | 作用 |
| --- | --- |
| `yudi-tweaks` | WebUI 配置内核运行时开关：sysctl、BBRv3、le9uo、zram `lz4kd`、KSM、ADIOS、DAMON |
| `ntsync` | 开机创建 `/dev/ntsync`，供 Wine/Proton 使用 |

`yudi-tweaks` 默认只开安全项（sysctl、BBRv3、le9uo、zram），配置写入 `/data/adb/yudi-tweaks.conf`，重启后生效。zram 切换会先 `swapoff` + `reset`；swap 使用量高时跳过，等下次重启。

安装方式见模块仓库的 README；设备已验证 `boot_completed=1`、zram `[lz4kd]` 16GB、`bbr3`、le9uo=1、NTSync 节点存在。
