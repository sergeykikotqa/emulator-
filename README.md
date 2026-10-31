# NestBox Magisk Lab

Изолированный экспериментальный NestBox для Android 13 (Wayondroid/tawcroot) на телефоне без root у хоста.

**Цель:** запуск Magisk/Kitsune Mask в гостевом Android через службы `init`, затем включение Zygisk и LSPosed. Наличие `su` само по себе ничего не доказывает.

## Статус

- Базовый NestBox 0.8.0 с нативным движком собран: [успешный CI](https://github.com/sergeykikotqa/emulator-/actions/runs/41181004525).
- Экспериментальный Magisk init-overlay: `scripts/prepare_magisk.py`. Скрипт применяется при сборке APK, **не в телефоне**.
- Magisk и Zygisk **пока не подтверждены на устройстве**. Они требуют запуска гостевого Android.
- LSPosed пока **не установлен**: сначала должен заработать Magisk/Zygisk.

## Что делает Magisk-интеграция

1. Получает закреплённый APK Kitsune Mask Canary и проверяет Git blob SHA-1 до распаковки.
2. Вкладывает arm64-бинарники в `assets/magisk/system/etc/init/magisk`.
3. Вкладывает `nestbox-magisk.rc` в `system/product/etc/init`, чтобы гость выполнял настройку при `post-fs-data` и `late_start`.
4. Готовит `/data/adb/magisk` и пытается установить менеджер после завершения загрузки Android.
5. В `GuestProps.kt` включает Magisk overlay **только когда на машине включён Root**; отдельный NestBox `su` оставлен для диагностики.

Уровень доступа: только гость в контейнере, не основной Android телефона.

## Скачать пробный APK

1. Открыть вкладку [Actions](https://github.com/sergeykikotqa/emulator-/actions), выбрать последнюю **успешную** сборку.
2. В **Artifacts** скачать `nestbox-lab-debug-apk`, распаковать ZIP и установить `app-debug.apk`.
3. Экспериментальный APK имеет package ID `app.nbox.lab` и ставится отдельно от обычного NestBox.
4. Создать Android 13 + GApps машину, включить **Root**, запустить Android. При первом запуске подготовка Magisk может потребовать второго перезапуска гостя.

Если виртуальная машина загрузится, проверить не только Root Checker: обнаружен ли менеджер Kitsune Mask, установлен ли Magisk, и определяется ли Zygisk.

Если загрузка падает, сохранить **NestBox Boot Logs / guest logcat** и проверить наличие ошибок `magisk64 --setup-sbin`, SELinux, `post-fs-data`.

## Ограничения

Проект `waydroid-magisk` архивирован. Его метод установки рассчитан на Linux Waydroid и здесь адаптирован экспериментально к Android-хосту с rootless Wayondroid. Архивная сборка Kitsune Mask может оказаться несовместимой. Успешная сборка APK ≠ работающий Magisk.

Это не официальный релиз NestBox. Используются открытые исходники [NestBox](https://github.com/rifatrajbd/NestBox-An-Android-Emulator-Support-Lineage-OS), [Wayondroid](https://github.com/yoro1836/wayondroid) и [waydroid-magisk](https://github.com/nitanmarcel/waydroid-magisk). Исходный NestBox/Wayondroid — GPL-3.0; runtime tawcroot — MIT. Третьесторонние бинарники Kitsune Mask для эксперимента скачиваются во время CI и не коммитятся в этот репозиторий.
