#!/usr/bin/env python3
"""Experimental Magisk init overlay for NestBox's Wayondroid Android 13 guest.

Runs on GitHub Actions AFTER cloning upstream NestBox and BEFORE assembleDebug.
No host boot partitions are modified; only the experimental APK's assets are staged.

Research source: https://github.com/nitanmarcel/waydroid-magisk (GPL-3.0)
Kitsune Mask canary archive: https://github.com/NotMaybe/magiskdelta
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path
from zipfile import ZipFile

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/prepare_magisk.py <nestbox-checkout>")

repo = Path(sys.argv[1]).resolve()
guest_props = repo / "app/src/main/java/app/nestbox/engine/modern/GuestProps.kt"
assert guest_props.is_file(), f"Missing NestBox checkout: {guest_props}"

# Pin both the revision and its git blob SHA-1; no unverified 'latest' artifacts.
REV = "852063a393a1b561640d06026d9e97183b07ba80"
BLOB_SHA1 = "e44957ea66d280d05b3dc1fb65673fe6c2ab0025"
URL = f"https://raw.githubusercontent.com/NotMaybe/magiskdelta/{REV}/app-release.apk"
request = urllib.request.Request(URL, headers={"User-Agent": "NestBox-Magisk-Lab/1"})
with urllib.request.urlopen(request, timeout=120) as response:
    payload = response.read()
git_hash = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
if git_hash != BLOB_SHA1:
    raise SystemExit(f"Kitsune APK Git blob checksum mismatch: {git_hash}")
print(f"Kitsune APK verified: {len(payload)} bytes, blob {git_hash}")

# NestBox's existing guest-overlay mechanism installs these files before guest init runs.
# Store the binaries in assets/magisk, NOT assets/guest/a13gapps: only install with vm.root=ON.
directory = repo / "app/src/main/assets/magisk/system/etc/init/magisk"
directory.mkdir(parents=True, exist_ok=True)
present = set()
with ZipFile(__import__("io").BytesIO(payload)) as archive:
    names = archive.namelist()
    for name in names:
        if name.startswith("lib/arm64-v8a/lib") and name.endswith(".so"):
            filename = name.rsplit("/", 1)[-1]
            target = filename.removeprefix("lib").removesuffix(".so")
            (directory / target).write_bytes(archive.read(name))
            present.add(target)
    for name in ("lib/armeabi-v7a/libmagisk32.so",):
        if name in names:
            (directory / "magisk32").write_bytes(archive.read(name))
            present.add("magisk32")
    for name in ("assets/util_functions.sh", "assets/addon.d.sh", "assets/boot_patch.sh"):
        if name in names:
            (directory / name.rsplit("/", 1)[-1]).write_bytes(archive.read(name))
(directory / "magisk.apk").write_bytes(payload)
(directory / "config").write_text("KEEPVERITY=true\nKEEPFORCEENCRYPT=true\nRECOVERYMODE=false\n")
required = {"magisk64", "magiskpolicy"}
if not required.issubset(present):
    raise SystemExit(f"Missing required Magisk binaries: {sorted(required - present)}; found {sorted(present)}")
print("Staged Kitsune binaries: " + ", ".join(sorted(present)))

init_dir = repo / "app/src/main/assets/magisk/system/product/etc/init"
init_dir.mkdir(parents=True, exist_ok=True)
(init_dir / "nestbox-magisk.rc").write_text("""# Experimental Waydroid-style Kitsune Magisk injection into NestBox guest init.
# Derived from nitanmarcel/waydroid-magisk, patch_bootanim(). Guest-only.
on post-fs-data
    start logd
    exec u:r:su:s0 root root -- /system/etc/init/magisk/magisk64 --auto-selinux --setup-sbin /system/etc/init/magisk
    exec u:r:su:s0 root root -- /system/etc/init/magisk/magiskpolicy --live --magisk "allow * magisk_file lnk_file *"
    mkdir /sbin/.magisk 0700 root root
    mkdir /sbin/.magisk/mirror 0700 root root
    mkdir /sbin/.magisk/block 0700 root root
    copy /system/etc/init/magisk/config /sbin/.magisk/config
    rm /dev/.magisk_unblock
    start nestbox_magisk_postfs
    wait /dev/.magisk_unblock 15
    rm /dev/.magisk_unblock

service nestbox_magisk_postfs /sbin/magisk --auto-selinux --post-fs-data
    user root
    seclabel u:r:su:s0
    disabled
    oneshot

service nestbox_magisk_late /sbin/magisk --auto-selinux --service
    class late_start
    user root
    seclabel u:r:su:s0
    oneshot

on property:sys.boot_completed=1
    start nestbox_magisk_seed
    mkdir /data/adb/magisk 0755 root root
    exec u:r:su:s0 root root -- /sbin/magisk --auto-selinux --boot-complete

service nestbox_magisk_seed /system/bin/sh /system/etc/init/magisk/nestbox-seed.sh
    user root
    seclabel u:r:su:s0
    disabled
    oneshot

on property:init.svc.zygote=restarting
    exec u:r:su:s0 root root -- /sbin/magisk --auto-selinux --zygote-restart

on property:init.svc.zygote=stopped
    exec u:r:su:s0 root root -- /sbin/magisk --auto-selinux --zygote-restart
""")
(directory / "nestbox-seed.sh").write_text("""#!/system/bin/sh
# Populate Magisk's data directory for subsequent guest boots.
# A first boot can finish without the daemon being ready; restart the guest afterward.
mkdir -p /data/adb/magisk
for f in /system/etc/init/magisk/*; do
    case "$f" in *.apk|*.rc|*/config|*.sh) continue ;; esac
    cp -f "$f" "/data/adb/magisk/${f##*/}" || exit 1
done
chmod 700 /data/adb
chmod 755 /data/adb/magisk /data/adb/magisk/*
chown -R 0:0 /data/adb/magisk
""")

# Allow Magisk native files in assets to retain their executable bit. NestBox's standard
# copyAssetTree() only marks files under /bin/ as executable, which excludes /etc/init/magisk/.
s = guest_props.read_text()
before = 'if (assets.list("guest/${rom.id}").orEmpty().isNotEmpty()) copyAssetTree(assets, "guest/${rom.id}", files)'
after = before + '''
        // Magisk laboratory overlay: separate from the ROM and gated by the guest Root switch.
        if (vm.root && assets.list("magisk").orEmpty().isNotEmpty())
            copyAssetTree(assets, "magisk", files)'''
if s.count(before) != 1:
    raise SystemExit("Upstream GuestProps changed: expected guest asset copy anchor")
s = s.replace(before, after, 1)
before_mode = 'Os.chmod(dst.path, if ("/bin/" in path) 0b111_101_101 else 0b110_100_100)'
after_mode = '''val magiskExecutable = "/system/etc/init/magisk/" in path &&
                !path.endsWith(".apk") && !path.endsWith(".rc") && !path.endsWith("/config")
            Os.chmod(dst.path, if ("/bin/" in path || magiskExecutable) 0b111_101_101 else 0b110_100_100)'''
if s.count(before_mode) != 1:
    raise SystemExit("Upstream GuestProps changed: expected asset chmod anchor")
s = s.replace(before_mode, after_mode, 1)
guest_props.write_text(s)

# NestBox already installs APKs reliably via 'pm install' after the guest is RUNNING.
# The init-triggered manager install above can run before package manager is ready,
# so install the manager from ModernEngine.tuneRunningGuest(), using the same existing
# guest command pathway as NestBox's Transfer -> Install APK.
modern_engine = repo / "app/src/main/java/app/nestbox/engine/modern/ModernEngine.kt"
engine = modern_engine.read_text()
tune_anchor = '''        vm?.spoof?.let { p ->
            if (p.region != "Off") sh(Spoof.liveCommands(p).joinToString("; "), 20_000)'''
tune_replacement = '''        // NestBox Magisk Lab: let Android finish boot before asking PackageManager to install
        // Kitsune.  The guest's init services only handle Magisk's daemon/boot stages.
        // A successful root check does not prove the Magisk daemon is functional.
        if (vm?.root == true) {
            // Stage exactly as NestBox's working Transfer -> Install APK implementation does.
            // This also installs the manager when the init/rootfs overlay is not active yet.
            val staged = File(guestDir(id), "rootless/data/local/tmp/nestbox-kitsune.apk")
            val output = runCatching {
                staged.parentFile?.mkdirs()
                context.assets.open("magisk/system/etc/init/magisk/magisk.apk").use { src ->
                    staged.outputStream().use { src.copyTo(it) }
                }
                staged.setReadable(true, false)
                sh("pm install -r -t /data/local/tmp/nestbox-kitsune.apk", 120_000)
            }.getOrElse { "Magisk manager install error: ${it.message}" }
            staged.delete()
            android.util.Log.i("NestBoxMagiskLab", "manager installation: ${output.take(600)}")
            // One short diagnostic record only; this is not a per-frame logger.
            val daemon = runCatching {
                sh("if test -x /sbin/magisk; then /sbin/magisk -v; else echo Magisk binary absent; fi", 12_000)
            }.getOrElse { "Magisk daemon check error: ${it.message}" }
            android.util.Log.i("NestBoxMagiskLab", "daemon check: ${daemon.take(300)}")
            runCatching {
                File(guestDir(id), "nestbox-magisk-result.txt")
                    .writeText("Manager install:\\n$output\\nDaemon check:\\n$daemon\\n")
            }
        }
        vm?.spoof?.let { p ->
            if (p.region != "Off") sh(Spoof.liveCommands(p).joinToString("; "), 20_000)'''
if engine.count(tune_anchor) != 1:
    raise SystemExit("Upstream ModernEngine changed: expected tuneRunningGuest() anchor")
engine = engine.replace(tune_anchor, tune_replacement, 1)
modern_engine.write_text(engine)

# Retain NestBox's own setuid su as a fallback for a failing Magisk daemon; Root Checker
# detecting su does NOT prove Magisk or Zygisk is working.
print("GuestProps patched; init overlay and manager staged (Root toggle must be ON)")
