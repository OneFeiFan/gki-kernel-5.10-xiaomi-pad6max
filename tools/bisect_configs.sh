#!/bin/bash
# 按配置分组逐个编译，检查厂商模块 CRC 是否被破坏
set -u
RESULT=/home/test/kernel-sources/bisect-result.txt
: > "$RESULT"
cd /home/test/kernel-sources/vanilla-root/common || exit 1

run_variant() {
  name="$1"; shift
  extra="$*"
  echo "########## variant $name ##########" >> "$RESULT"
  git checkout -- arch/arm64/configs/gki_defconfig build.config.gki
  sed -i 's/^CONFIG_LTO_CLANG_FULL=y$/CONFIG_LTO_CLANG_THIN=y/' arch/arm64/configs/gki_defconfig
  sed -i 's/^POST_DEFCONFIG_CMDS="check_defconfig"$/POST_DEFCONFIG_CMDS=""/' build.config.gki
  for c in $extra; do
    if grep -q "^# $c is not set$" arch/arm64/configs/gki_defconfig; then
      sed -i "s/^# $c is not set$/$c=y/" arch/arm64/configs/gki_defconfig
    elif ! grep -q "^$c=y$" arch/arm64/configs/gki_defconfig; then
      echo "$c=y" >> arch/arm64/configs/gki_defconfig
    fi
  done
  cd /home/test/kernel-sources/vanilla-root || return
  BUILD_CONFIG=common/build.config.gki.aarch64 OUT_DIR=/home/test/kernel-sources/out-v-$name \
    build/build.sh -j8 > /home/test/kernel-sources/build-v-$name.log 2>&1
  echo "build_exit=$?" >> "$RESULT"
  for m in /mnt/c/Users/OneFeiFan/binder_gki.ko /mnt/c/Users/OneFeiFan/qcom_glink_smem.ko; do
    python3 /home/test/kernel-sources/tools/crc_check.py "$m" \
      /home/test/kernel-sources/out-v-$name/dist/vmlinux.symvers >> "$RESULT" 2>&1
  done
  cd /home/test/kernel-sources/vanilla-root/common
}

run_variant base
run_variant cgrp CONFIG_CGROUP_DEVICE CONFIG_CGROUP_PIDS CONFIG_DEVTMPFS
run_variant ns CONFIG_USER_NS CONFIG_PID_NS CONFIG_IPC_NS
run_variant nft CONFIG_NETFILTER_XT_MATCH_ADDRTYPE CONFIG_NETFILTER_XT_TARGET_LOG CONFIG_NETFILTER_XT_MATCH_RECENT CONFIG_IP_SET CONFIG_IP_SET_HASH_IP CONFIG_IP_SET_HASH_NET CONFIG_NETFILTER_XT_SET
run_variant sysv CONFIG_SYSVIPC CONFIG_POSIX_MQUEUE
echo DONE >> "$RESULT"
