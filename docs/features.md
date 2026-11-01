# 功能

内核的默认行为与原厂一致，大部分功能需要由 [yudi-tweaks](https://github.com/OneFeiFan/yudi-ksu-modules) 模块在开机后打开。下表是速查，各功能的细节见后面的章节。

| 功能 | 内核默认 | 开关方式 |
| --- | --- | --- |
| BBRv3 | 不启用，拥塞控制仍是 cubic | yudi-tweaks「BBRv3」，默认打开 |
| le9uo | 启用 | yudi-tweaks「le9uo」，或 `vm.workingset_protection` |
| Kcompressd | 启用 | 没有开关 |
| zram 压缩算法 | 由系统的 PerfInit 设置 | yudi-tweaks「zram 算法」，默认 lz4kd |
| KSM | 关闭 | yudi-tweaks「KSM」 |
| ADIOS | 不作为默认调度器 | yudi-tweaks「ADIOS」 |
| DAMON_RECLAIM | 关闭 | yudi-tweaks「DAMON_RECLAIM」 |
| 空闲调度器 | 厂商的 `qcom-cpu-lpm` | yudi-tweaks「cpuidle governor」 |
| RCU 惰性回调 | 关闭 | yudi-tweaks「RCU_LAZY」，或 `/sys/module/rcutree/parameters/enable_rcu_lazy` |
| 节能工作队列 | 启用 | 启动参数 `workqueue.power_efficient=0` 可以关闭 |
| PLB | 关闭 | `net.ipv4.tcp_plb_enabled` |

## 容器

内核打开了 Docker、LXC 和 Droidspaces 需要的功能：

- cgroup v1 的 devices、pids、perf_event 和 net_cls 控制器；
- nftables、bridge netfilter、IPv6 NAT、IPVS 和 SCTP；
- VXLAN、VLAN、IPVLAN、MACVLAN、L2TP、FOU 和 GRE 等虚拟网络设备，以及 tc；
- blkio 限速、Btrfs、checkpoint/restore 与 CRIU 需要的诊断接口、`FHANDLE`。

**CPU 配额**：CFS 带宽控制让 Droidspaces 的 `--cpus` 可以限制容器的 CPU 用量。原厂 KMI 里的 `task_group` 和 `cfs_rq` 不能改变布局，所以新增的状态放在 KABI 预留字段和 `cfs_rq` 末尾的填充区里，结构大小不变。

**net_cls**：控制器已经打开，但内核没有设置默认的 classid。需要按容器分流时，再写对应的 tc 或 nftables 规则。

**FHANDLE**：容器里可以运行 systemd。不要给容器 `CAP_DAC_READ_SEARCH` 权限，否则它可以通过文件句柄绕过目录权限。

## Wine 和 Proton

- **NTSync**：Windows 同步原语的内核实现。内核注册的是 misc 设备，设备节点 `/dev/ntsync` 由 ntsync 模块按 `/sys/class/misc/ntsync/dev` 创建，因为它的次设备号是动态分配的。
- **futex_waitv**：一次等待多个 futex，64 位和 32 位系统调用都有。
- **epoll_pwait2**：纳秒精度超时的 epoll 等待。

## 内存

### le9uo

在内存回收时保护一部分文件缓存（工作集），减少应用切回时重新读盘造成的卡顿。默认启用，`vm.workingset_protection` 设为 0 可以关闭。

如果保护阈值把所有回收目标都清零，内核会按当前回收优先级重新分配扫描量，避免回收停滞导致卡死。此时如果匿名页无法换出（没有可用的 swap，或者这次回收不允许换出），只扫描文件页。

### Kcompressd

kswapd 回收内存时，原本要自己把匿名页压缩后写进 zram。Kcompressd 把这一步交给每个内存节点上的专门线程，回收线程不再被压缩拖慢。只对 zram 这类同步换出设备、且由 kswapd 发起的匿名页写回生效。它的状态放在独立的数组里，没有改动 `pglist_data`，所以不影响 KMI。

### zram

zram 和 zsmalloc 编进了内核，由本仓库维护。原厂 vendor 分区里的 zram.ko 和 zsmalloc.ko 会被内核的模块屏蔽名单跳过。可用的压缩算法包括 LZ4、LZ4K、LZ4KD、LZO 和 zstd。

开机时，小米的 PerfInit（`/system_ext/xbin/system_perf_init`）读取 `/system_ext/etc/perfinit.conf` 里的 `comp_algo` 来初始化 zram，并把 zram 的容量设为与物理内存相同。yudi-tweaks 通过覆盖这份配置来更换算法，因此不需要在开机后重置 zram。

HyperOS 移植包在 `/vendor/etc/moon_modules/` 里带有 4 个第三方的闭源内存模块，它们和 le9uo、Kcompressd 的作用重叠，yudi-tweaks 默认会阻止它们加载。

### 内存扩展（ExtM）

移植自小米开源的 `spinel-v-oss` 内核（5.10.233）。它把 zram 里长时间未访问、压缩率又低的页写到闪存上的文件里，腾出内存：

- PerfInit 开机时创建 `/data/extm/extm_file`，用 dm-linear 映射成块设备，再设为 zram 的写回设备；
- 系统的 ExtM 服务每 2 分钟把空闲的页标记一次，累计亮屏 10 分钟后的那次熄屏时，在当天的额度内触发写回；
- 写回分批进行，优先写回压缩率低的页；亮屏时系统发送 SIGUSR1 中止正在进行的写回；
- sysfs 接口与原厂 zram.ko 完全一致，共 30 个，包括 `idle_stat`、`time_list`、`low_compress_ratio`、`pages_life` 等统计。

手动触发一次写回，可以用来确认写回设备工作正常：

```sh
echo all > /sys/block/zram0/idle
echo "idle 10000 0" > /sys/block/zram0/writeback
cat /sys/block/zram0/bd_stat      # 第三列是写到闪存的页数
```

### 内存冻结（MFZ）

移植自小米 6.6 内核（`bixi-v-oss`）的内存冻结写回策略，配合系统的冻结服务使用：

- 内核按内存 cgroup 打标记：开机时 `init.rc` 给 `/dev/memcg/freeze-app` 写入 `memory.anno_writeback_enable`，这个 cgroup 里的进程，其页面进入 zram 时会被标记为冻结页；
- 这些页可以使用专门预留的写回空间（`mfz_disk_quota`，由 PerfInit 按 `persist.sys.mfz.disk_quota` 设置，默认 2048 MB）；
- 受保护的应用组（`init.rc` 写入 `memory.anno_writeback_protected` 的 cgroup）的页永远不写回；
- 系统的内存冻结服务只处理名单里的应用，按冻结应用占用的内存分三档：超过 2 GB 压缩，超过 3 GB 写回，超过 4 GB 结束进程；
- 名单在 `/product/etc/mfz.xml` 和 `/data/system/mfz.xml`，yudi-tweaks 可以往里面添加应用。

第三方墓碑应用（NoActive 等）的冻结不会把应用移进 `freeze-app`，所以使用它们时 MFZ 不起作用。

内核没有实现 PerfInit 日志里提到的 `writeback_quota` 和 `zgroup_enable`：前者是日志的笔误，实际检查的是 `mfz_disk_quota`；后者是玄戒芯片机型另一套内存架构的开关，没有公开源码。不要用空文件冒充 `zgroup_enable`，否则 PerfInit 会切换到内核并不支持的模式。

## 网络

**BBRv3**：Google 的 BBR 第三版拥塞控制，连同它依赖的 TCP 基础改动一起回移。内核默认仍是 cubic，yudi-tweaks 默认会切换到 BBRv3。

**PLB**：随 BBRv3 一起加入的保护性负载均衡，用于数据中心的 IPv6 多路径网络，手机上没有用处，默认关闭。

**cubic 修正**：回移了 HyStart 轮次判断和 BIG TCP 下 ACK 延迟估计的两个上游修正。

## 存储

**ADIOS**：一个面向低延迟的 IO 调度器（3.2.0）。默认调度器不变（UFS 上是厂商设置的 cpq），可以用 yudi-tweaks 切换。

**zstd 1.5.7**：内核的 zstd 库从 1.4.10 升级到 1.5.7，zram、f2fs、btrfs 和 initramfs 解压都会用到。5.10 的 EROFS 不支持 zstd。

**f2fs**：回移了 10 个上游的稳定性修正。

## 省电与调度

**TEO 空闲调度器**：ACK 的 5.10 基线已经带有 TEO，这里回移了它在 2021 到 2024 年间的上游改进。默认的空闲调度器仍是厂商的 `qcom-cpu-lpm`，可以用 yudi-tweaks 切换。熄屏短测中 TEO 的深睡占比略高，实际功耗还没有测。

**RCU 惰性回调**：空闲时把 RCU 回调攒起来批量处理，减少 CPU 唤醒。它只在卸载了 RCU 回调的 CPU 上生效，本机的启动参数 `rcu_nocbs=0-7` 已经卸载了全部 8 个 CPU。开机和挂起期间由独立的计数器强制立即处理，不受设备启动参数里 `rcu_expedited=1` 的影响。默认关闭，属于实验功能，打开前先做挂起唤醒和网络开关的测试。

**节能工作队列**：默认启用 `WQ_POWER_EFFICIENT_DEFAULT`，让可以迁移的后台工作尽量在已经唤醒的 CPU 上执行。实际功耗还没有对比。

**挂起与空闲**：挂起过程中保留 cpuidle，并减少 s2idle 期间的无效唤醒。有任务待运行时，CPU 不再进入空闲。

**未改动的调度参数**：PELT 的时间倍数保持 1，实测改为 2 没有明显收益。UCLAMP 由 ACK 基线提供，默认值保持不变。

## 其他

- **binder**：用位图查找描述符，进程间通信更快。新增的数据放在 `binder_proc_ext` 里，原厂 KMI 中的 `binder_proc` 布局不变。
- **内存分配**：为 kernfs、cgroup、dma-buf 和 sync_file 的高频小对象建立专用缓存；整页复制和清零改用 `copy_page()` 和 `clear_page()`；Sultan Alsawaf 的一组减少小块分配的优化。
- **RCU 等待**：缩短 `synchronize_rcu()` 的等待时间。
- **长按电源键同步**：按住电源键 2 秒，内核同步一次文件系统，避免随后的强制重启丢失数据。

## 没有采用的

| 内容 | 原因 |
| --- | --- |
| menu 空闲调度器的上游改进 | 在 5.10.272 上冲突 |
| SSG IO 调度器 | 短测没有稳定收益，顺序写慢了约 18% |
| 多代 LRU（MGLRU） | 需要改动多个 KMI 结构，风险高，需要单独评估 |
| schedutil 和 CFS 选核的调整 | 本机由高通的 WALT 负责调频和选核，这类改动不生效 |
| 关闭安全缓解措施、跳过模块 CRC 检查 | 用安全换取很小的性能 |
