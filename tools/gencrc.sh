#!/bin/bash
# 用构建目录（O=out-p2）里记录的编译命令，对单个编译单元跑 cpp + genksyms。
# 用法: gencrc.sh <tag> <tu 路径(不带 .o)> [源码树根目录]
#   tag    输出文件前缀(/tmp/<tag>.{i,crc,types,err})
#   tu     例如 kernel/module 或 kernel/cgroup/cgroup
#   树根   可选；给出时把编译命令里的源码树路径替换成它（用于纯净 HEAD worktree）
set -e

OUT=${4:-/home/test/kernel-sources/out-p2/common}
TMP=/home/test/kernel-sources/work/gencrc
mkdir -p "$TMP"
cd "$OUT"

tag=$1
tu=$2
tree=$3
base=$(basename "$tu")
dir=$(dirname "$tu")
cmdfile="$dir/.$base.o.cmd"

if [ ! -f "$cmdfile" ]; then
    echo "NO_CMD $cmdfile" >&2
    exit 2
fi

cmd=$(head -1 "$cmdfile" | sed 's/^[^:]*:= //')

CLANG=/home/test/kernel-sources/extracted/prebuilts-master/clang/host/linux-x86/clang-r416183b/bin/clang
if [ ! -x "$CLANG" ]; then
    CLANG=$(command -v clang) || { echo "NO_CLANG" >&2; exit 2; }
fi
cmd="${cmd/#clang /$CLANG }"

# 把编译改成预处理 + 定义 __GENKSYMS__
cmd=$(printf '%s' "$cmd" | sed "s#-c -o $tu\.o #-E -D__GENKSYMS__ #")

if [ -n "$tree" ]; then
    cmd=${cmd//\/home\/test\/kernel-sources\/vanilla-root\/common/$tree}
fi

eval "$cmd" > "$TMP/$tag.i" 2> "$TMP/$tag.cpp.err" || {
    echo "CPP_FAIL $tag" >&2
    tail -5 "$TMP/$tag.cpp.err" >&2
    exit 3
}

./scripts/genksyms/genksyms -r /dev/null -T "$TMP/$tag.types" \
    < "$TMP/$tag.i" > "$TMP/$tag.crc" 2> "$TMP/$tag.gk.err" || {
    echo "GENK_FAIL $tag" >&2
    tail -5 "$TMP/$tag.gk.err" >&2
    exit 4
}

echo "== $tag =="
grep -E "^__crc_(module_layout|cgroup_taskset_next|kmalloc_caches|_dev_err|_dev_info) " "$TMP/$tag.crc" || true
echo "-- 导出符号总数: $(grep -c '^__crc_' "$TMP/$tag.crc") --"
