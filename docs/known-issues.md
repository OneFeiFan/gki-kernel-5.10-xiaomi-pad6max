# 已知问题

## 尚未充分验证的改动

下面这些改动已经通过构建和 KMI 门禁，设备也能正常开机，但还缺少针对性的测试。测试方法见 [verification.md](verification.md)。

- **RCU 惰性回调**（默认关闭）：打开后，厂商驱动里通过 `call_rcu()` 提交的回调在空闲时最多会推迟约 10 秒执行。需要反复挂起唤醒、开关网络和相机、制造内存压力，并对比待机功耗。
- **挂起期间保留 cpuidle**：改变了挂起流程。需要拔掉 USB 待机，确认挂起没有失败。出问题时优先去掉这一项（`08-power/0023-suspend-keep-cpuidle.patch`）。
- **缩短 `synchronize_rcu()` 等待**：上游 2025 年的新改动。启动参数里写了 `kernel.panic_on_rcu_stall=1`，但运行时 `/proc/sys/kernel/panic_on_rcu_stall` 实际为 0，不会因 RCU 卡住自动重启；做长时间测试时以 sysctl 为准。
- **binder 位图查找、Sultan 的小优化**：位于进程间通信等高频路径，需要长时间日常使用观察。
- **TEO 和节能工作队列的功耗**：还没有做拔线待机的对比。

## 开机时的 RCU 警告

每次开机，`dmesg` 里会出现一次 `WARNING ... kernel/rcu/tree_plugin.h:297 rcu_note_context_switch`。

原因在厂商的键盘驱动 `nanosic_driver`：它在 power supply 的原子通知回调里查询供电状态，这个查询会进入电池驱动并等待 ADSP 回复，而原子通知链运行在 RCU 读侧临界区里，不允许睡眠。

本内核使用可抢占 RCU，在临界区里睡眠只会让 RCU 宽限期多等这一段时间，正常情况下只有几毫秒，不影响功能。原厂内核加载同样的驱动时也会报这条警告。

## 安全更新

基线是 Linux 5.10.272。Linux 5.10.273 还没有合入 Android 通用内核，期间公开的漏洞里，与容器相关的 4 个已经手工修复（`04-security/0013-container-security-fixes.patch`），其中一个已包含在 5.10.273 里，升级基线时要去掉重复的部分。详细的对照见 [notes/ecosystem-survey-2026-10-30.md](notes/ecosystem-survey-2026-10-30.md)。

## 其他限制

- 没有开启 `CONFIG_DEBUG_INFO_BTF`，依赖 CO-RE 的 eBPF 程序不能使用。
- 设备自带的 `ss` 版本太旧，看不到 BBRv3 的诊断信息，可以用 Termux 的 iproute2 代替。
