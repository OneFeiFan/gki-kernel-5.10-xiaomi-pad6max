#!/system/bin/sh

echo "===== props ====="
getprop | grep -E 'ro\.(build|product|vendor|board|hardware|boot|soc|gfx|miui)|ro\.system\.ddr|persist\.sys\.stability' | sort

echo "===== kernel ====="
uname -a
cat /proc/cmdline
getprop ro.boot.slot_suffix
getprop ro.boot.verifiedbootstate
getprop ro.boot.flash.locked
getprop ro.boot.hardware
getprop ro.board.platform
getprop ro.soc.manufacturer
getprop ro.soc.model

echo "===== gpu props ====="
getprop | grep -iE 'gpu|kgsl|adreno|vulkan|gles|opengl' | sort

echo "===== kgsl sysfs ====="
ls -l /sys/class/kgsl 2>/dev/null
for f in gpu_model gpu_busy_percentage gpu_available_frequencies gpu_clock_stats \
	 gpu_min_clock gpu_max_clock gpu_clock gpu_governor gpu_busy \
	 devfreq/cur_freq devfreq/min_freq devfreq/max_freq \
	 devfreq/available_frequencies devfreq/governor devfreq/available_governors \
	 devfreq/trans_stat; do
	if [ -e "/sys/class/kgsl/kgsl-3d0/$f" ]; then
		echo "--- $f"
		cat "/sys/class/kgsl/kgsl-3d0/$f" 2>/dev/null
	fi
done

echo "===== kgsl module ====="
lsmod | grep -iE 'kgsl|adreno|gpu|msm|drm|sde|ion|dmabuf' || true
for m in msm_kgsl kgsl adreno; do
	if [ -d "/sys/module/$m" ]; then
		echo "module $m"
		cat "/sys/module/$m/version" 2>/dev/null
		cat "/sys/module/$m/parameters/"* 2>/dev/null | head -40
	fi
done

echo "===== kgsl dmesg ====="
dmesg | grep -iE 'kgsl|adreno|gpu' | tail -40

echo "===== graphics userland ====="
ls -l /vendor/lib64 2>/dev/null | grep -iE 'gles|vulkan|gsl|adreno|llvm|gpu' | head -30
ls -l /vendor/lib 2>/dev/null | grep -iE 'gles|vulkan|gsl|adreno|llvm|gpu' | head -30
getprop ro.gfx.driver.0
getprop ro.gfx.driver.1
getprop ro.hardware.vulkan

echo "===== surfaceflinger ====="
timeout 15 dumpsys SurfaceFlinger 2>/dev/null | grep -iE 'GLES|Vulkan|GPU|Driver|Adreno' | head -30

echo "===== modules ====="
echo "loaded_count=$(lsmod | wc -l)"
lsmod | head -10
ls -ld /vendor/lib/modules /vendor_dlkm/lib/modules /lib/modules 2>/dev/null
for d in /vendor/lib/modules /vendor_dlkm/lib/modules /lib/modules; do
	[ -d "$d" ] && echo "$d count=$(ls "$d"/*.ko 2>/dev/null | wc -l)"
done

echo "===== thermal ====="
for z in /sys/class/thermal/thermal_zone*; do
	[ -e "$z/type" ] || continue
	printf '%s %s %s\n' "$z" "$(cat "$z/type" 2>/dev/null)" "$(cat "$z/temp" 2>/dev/null)"
done | head -50

echo "===== devfreq ====="
for d in /sys/class/devfreq/*; do
	[ -e "$d/name" ] || continue
	printf '%s name=%s cur=%s min=%s max=%s gov=%s\n' "$d" \
		"$(cat "$d/name" 2>/dev/null)" \
		"$(cat "$d/cur_freq" 2>/dev/null)" \
		"$(cat "$d/min_freq" 2>/dev/null)" \
		"$(cat "$d/max_freq" 2>/dev/null)" \
		"$(cat "$d/governor" 2>/dev/null)"
done | head -30

echo "===== storage ====="
cat /proc/partitions
df -h 2>/dev/null | head -20

echo "===== selinux / ksu ====="
getenforce
ls -l /data/adb/modules 2>/dev/null

echo "===== sysctl ====="
for f in /proc/sys/vm/max_map_count /proc/sys/fs/inotify/max_user_watches \
	 /proc/sys/fs/inotify/max_user_instances /proc/sys/vm/swappiness \
	 /proc/sys/net/ipv4/tcp_congestion_control /proc/sys/net/core/default_qdisc; do
	echo -n "$f="
	cat "$f" 2>/dev/null
done
