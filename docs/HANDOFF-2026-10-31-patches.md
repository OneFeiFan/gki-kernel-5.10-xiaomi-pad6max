# 交接：补丁整理、zram 内建 + 小米 ExtM、yudi-tweaks 1.7/1.8（2026-10-31）

> 历史快照：本文对应 2026-10-31 的 1.7/1.8 和 26/28 个补丁。文中编号均为当时的旧编号。当前状态（r17：48 个补丁，
> 旧编号对照见 `patches/README.md`；yudi-tweaks 2.2）见 `patches/README.md` 和 `docs/HANDOFF-system-state.md`。

本文件给负责合并的本地 AI。两个仓库各有一个 git bundle，直接拉取即可；下面说明每个提交
做了什么、怎么验证、还剩什么。

## 1. 内核仓库 gki-kernel-5.10-xiaomi-pad6max（分支 pad6max）

前提：本地 HEAD 是 `c6cf39ed6`。

```sh
git pull /path/to/gki-yudi-rework.bundle HEAD
```

bundle 里有四个提交，按顺序：

| 提交 | 内容 |
| --- | --- |
| `d21373fbc` | 按目录重新编号；每个补丁的 `gki_defconfig` 选项改放在各自的原厂锚点行之后（任一补丁可单独去掉）；修正 0002/0009/0022/0023/0026 的来源，补全 0014/0025 来源链；补 Depends-On；把 BBRv3 的 `GSO_LEGACY_MAX_SIZE` 从 0005 移到 0020；0013 补全 nfnetlink_log 修复的 `nf_log_syslog` 一半（5 个日志器改用 `pre_exit`） |
| `a752cd54d` | 一度把 zram 交还厂商模块（被下一个提交取代，保留为历史） |
| 第三个提交 | zram 恢复内建（0016、0017 回到通用系列）；0015 负责启用压缩算法；新增 `patches/xiaomi/0027`（小米官方源码的 ExtM zram）和 `patches/series.xiaomi`；`source/` 改为带小米组的树；文档同步 |
| 第四个提交 | 新增 `xiaomi/0028`：内存冻结（mfz）写回策略，移植自小米 6.6 源码，接口名与取值对照官方 yudi zram.ko；zram 的 sysfs 接口至此与官方完全一致 |

### 最终结构

- `patches/series`：通用系列，26 个，树 `862d916248ae64f3b5c392aea6f5e5355e9eb8d0`。
- `patches/series.xiaomi`：通用系列 + `xiaomi/0027`、`0028`，树
  `67a0c79cadacca880c122281d17130fe31395baa`，也是 `source/` 的内容，yudi 用这个构建。
- 基线：ACK `android12-5.10-lts` `8059ae219630120955ce6281668ffa709fd87521`。
- 真实依赖只有三处：0009→0008、0020→0019、0025→0015；0027 在配置上依赖 0016/0017。

### 合并后自检

```sh
cd common && git checkout 8059ae219630
while read p; do git am ../gki-yudi/patches/$p; done < ../gki-yudi/patches/series.xiaomi
git rev-parse HEAD^{tree}     # 应为 67a0c79cadacca880c122281d17130fe31395baa
```

构建方式不变（`build/build.sh`，`BUILD_CONFIG=common/build.config.gki.aarch64`）。构建后：

- `vmlinux.symvers` 仍应是 7298 个符号、与原厂 CRC 差异 0（用 `tools/` 下的脚本核对）。
- `/proc/config.gz` 应包含 `CONFIG_ZRAM=y`、`CONFIG_ZRAM_WRITEBACK=y`、
  `CONFIG_MIUI_ZRAM_MEMORY_TRACKING=y`、`CONFIG_MI_MEMORY_FREEZE=y`、`CONFIG_CRYPTO_LZ4KD=y`。

本地只做过：两个 series 的完整应用与树哈希核对；单独应用和"去掉一个"测试；用 clang 18.1.3
交叉编译 `drivers/block/zram`、`kernel/module.c`、`nf_log_ipv4`、`nf_log_ipv6`。**没有做完整
内核构建，也没有实机验证。**

## 2. 模块仓库 yudi-ksu-modules

前提：本地 HEAD 是 `db5d7c0`。

```sh
git pull /path/to/yudi-ksu-modules-1.8.bundle HEAD
```

| 提交 | 内容 |
| --- | --- |
| `32cdcea`（1.7） | zram 算法改为在源头设置：复制 `/system_ext/etc/perfinit.conf`，只把 `comp_algo` 换成选定算法，以无系统方式覆盖（`zram_conf.sh`，安装时和 post-fs-data 生成）。`service.sh` 不再重置 zram，只核对；高级开关 `ZRAM_FORCE` 保留重建兜底（先保存再恢复写回设备和额度）。算法检查改看 `/proc/crypto` |
| `78433c1`（1.8） | 默认屏蔽移植包的 4 个月亮内存模块（`/vendor/etc/moon_modules/*.ko`，由 vendor `init.qti.kernel.rc` 加载）：空文件覆盖使其加载失败，覆盖未生效的那次开机由 `service.sh` 在开机后卸载。`MOON_MODS=1` 恢复 |

模块与本次内核直接配合，无需再改。

## 3. 实机验证清单（刷入新内核 + yudi-tweaks 1.8 后）

```sh
su
cat /proc/swaps                                   # zram0 存在且已启用
lsmod | grep -E 'zram|zsmalloc|moon'              # 都不应出现（zram 内建、月亮模块已屏蔽）
dmesg | grep -iE 'built in, skipping'             # 厂商 zram.ko / zsmalloc.ko 被跳过
cat /sys/block/zram0/comp_algorithm               # [lz4kd]
cat /sys/block/zram0/backing_dev                  # /dev/block/dm-XX（ExtM 写回设备）
ls /sys/block/zram0 | grep -E 'idle_stat|time_list|pages_life|low_compress_ratio|wb_pages_max'
grep PerfInit /data/adb/ksu/log/logcat.log | grep -iE 'not exist|dm-linear|comp_algorithm'
logcat -d -s ExtM | tail -20                      # 看 Flush finished / Mark IDLE finished
dmesg | grep -iE 'ExtM|Flush finished|Mark IDLE'
cat /sys/block/zram0/bd_stat                      # 运行几小时后第 2、3 列应大于 0
ls /sys/block/zram0 | grep mfz                    # mfz_enable mfz_disk_quota mfz_compr_data_size mfz_idle_stat
cat /sys/block/zram0/mfz_enable /sys/block/zram0/mfz_disk_quota
cat /dev/memcg/freeze-app/memory.anno_writeback_enable      # 开机完成后应为 2
cat /dev/memcg/protected-app/memory.anno_writeback_control  # 应为 1
cat /dev/memcg/freeze-app/cgroup.procs | head               # 有冻结应用时非空
cat /sys/block/zram0/mfz_compr_data_size                    # 有冻结应用进入 zram 后大于 0
cat /data/adb/yudi-tweaks.log
```

期望：PerfInit 只剩 `writeback_quota`（及可能的 `zgroup_enable`）报 not exist；`bd_stat` 有 6 列，后 3 列是冻结应用的写回统计；
不再出现 `capacity change ... to 0`（模块不再重置 zram）；ExtM 日志里能看到标记空闲和写回。

另外，0013 的日志器改动建议在容器里反复创建、销毁带 LOG 规则的网络命名空间，看 dmesg 无报错。

## 4. 还没做的

- 内存冻结（mfz）已在 0028 移植，待实机验证。
- `writeback_quota`、`zgroup_enable`：没有任何公开源码。
- 可选：ADIOS 从 3.2.0 升级到 3.3.0。
- 审查报告与过程记录见 claude.ai 上的"yudi GKI 5.10 补丁审查报告"。
