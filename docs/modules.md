# KernelSU 模块

模块仓库：<https://github.com/OneFeiFan/yudi-ksu-modules>

| 模块 | 版本 | 作用 |
| --- | --- | --- |
| `yudi-tweaks` | 1.4 | WebUI 配置内核运行时开关：sysctl、BBRv3、le9uo、zram `lz4kd`、KSM、ADIOS、DAMON；显示 CPU 限制（CFS_BANDWIDTH）和 ntsync 状态 |
| `ntsync` | 1.1 | 开机按 `/sys/class/misc/ntsync/dev` 创建 `/dev/ntsync`，供 Wine/Proton 使用 |

`yudi-tweaks` 默认只开安全项（sysctl、BBRv3、le9uo、zram），配置写入 `/data/adb/yudi-tweaks.conf`，重启后生效。le9uo 是例外：内核补丁默认开启，模块关闭时写 0。zram 切换会先 `swapoff` + `reset`；swap 使用量高时跳过，等下次重启。CPU 限制（`Droidspaces --cpus`）是内核的 CFS_BANDWIDTH 能力，WebUI 只显示状态，没有开关。

安装方式见模块仓库的 README；当前验证状态：`boot_completed=1`、420 个模块、zram `[lz4kd]` 16GB、`bbr3`、le9uo=1、ntsync 节点按 `/sys/class/misc/ntsync/dev` 创建，Droidspaces check 的 CPU limit 为 ✓。p1p4 内核（`gd78a2ae2a9a5-dirty`）带 CRIU DIAG/FHANDLE；selftests：ntsync 10/11（`stress_wait` 是测试程序计数器被编译器提出循环，非内核问题）、owner 2/2、futex_waitv 7/7、epoll 63/63。
