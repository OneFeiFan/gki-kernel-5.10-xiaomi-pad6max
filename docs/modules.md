# KernelSU 模块

模块源码、安装和配置说明在：
<https://github.com/OneFeiFan/yudi-ksu-modules>

| 模块 | 版本 | 作用 |
| --- | --- | --- |
| `yudi-tweaks` | 2.3 | 运行时开关和状态页（GOV、RCU lazy、实验调参），默认值见模块仓库 |
| `ntsync` | 1.1 | 按 `/sys/class/misc/ntsync/dev` 创建 `/dev/ntsync` |

2.3 改进 MFZ 白名单（基础名单取自系统原件、保留云控修改、只删自己写的文件），RCU 惰性回调注明实验项；2.2 新增 RCU 惰性回调开关（实验性，默认关闭）；2.0/2.1 还有 ADIOS、DAMON、TEO 和
5 个实验 sysctl/f2fs 开关。内核侧只提供能力：CFS 带宽供 Droidspaces 限制 CPU，
NTSync 提供 misc 设备。
开关、默认值、WebUI 和验证命令都以模块仓库的 README 为准。
