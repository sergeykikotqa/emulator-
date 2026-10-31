# NestBox Magisk Lab

Isolated Android VM experiment. This repository is **not** the KOLEYA Unity project.

## Goal
Build a separate NestBox Android APK based on the upstream [NestBox](https://github.com/rifatrajbd/NestBox-An-Android-Emulator-Support-Lineage-OS) (0.8.0 sources), then evaluate adapting [waydroid-magisk](https://github.com/nitanmarcel/waydroid-magisk) for a rootless Wayondroid Android 13 guest.

The existing NestBox Android 13 machine on the phone stays untouched. The experimental APK uses the different Android package ID `app.nbox.lab`. It will have its **own machine/data**.

## Current stage
- CI: compile the original source (including NestBox's own `su`), with upstream Wayondroid native libraries.
- No Magisk, Zygisk or LSPosed integration has been proven working.
- Do not use the phone's boot.img / init_boot.img, and do not run the standard Magisk direct installer on the host.

## Build
Open **Actions → Build NestBox laboratory APK** after enabling workflows (if the account has remaining GitHub Actions quota).

Artifact: `nestbox-lab-debug-apk` → `app-debug.apk`.

## Sources and licensing
Upstream NestBox and Wayondroid are GPL-3.0 (see their repositories); the tawcroot runtime is MIT. No APK binaries are committed in this repository. The workflow fetches the original repositories and creates a reproducible build.

## Limitations
GitHub Actions for private repositories consumes included CI minutes. Standard GitHub-hosted runners in public repositories do not consume CI minutes. The Actions quota/status of this particular account has not been verified.
