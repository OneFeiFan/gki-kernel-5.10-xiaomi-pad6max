# KernelSU 模块

模块源码、安装和配置说明在：
<https://github.com/OneFeiFan/yudi-ksu-modules>

| 模块 | 版本 | 作用 |
| --- | --- | --- |
| `yudi-tweaks` | 1.5 | 运行时开关和状态页，默认值见模块仓库 |
| `ntsync` | 1.1 | 按 `/sys/class/misc/ntsync/dev` 创建 `/dev/ntsync` |

内核侧只提供能力：CFS 带宽供 Droidspaces 限制 CPU，NTSync 提供 misc 设备。
开关、默认值、WebUI 和验证命令都以模块仓库的 README 为准。
