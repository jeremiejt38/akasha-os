# Akasha OS

Custom LibreELEC 12 (Omega) distribution for Raspberry Pi 4, focused on HTPC, media streaming, and cloud gaming.

## Features

- **Media**: Plex, Jellyfin, YouTube Music integration
- **Cloud Gaming**: Steam Link, Moonlight (NVIDIA GameStream/Sunshine), GeForce NOW, Xbox Cloud Gaming, Amazon Luna, Boosteroid via Chromium Docker
- **Smart Power Management**: CEC TV control (auto-off on shutdown), 30min inactivity shutdown, screensaver
- **Custom Skin**: Arctic Horizon 2 with Akasha branding, reorganized menus (Films / Series / Music / Games / Akasha Settings)
- **Controller Support**: Xbox Wireless Controller with corrected axis mapping
- **Akasha Settings Panel**: System info, fan test, CEC test, sleep timers, reboot/shutdown from Kodi UI
- **Argon One Case**: Fan control via I2C (55/60/65C thresholds), power button shutdown with CEC

## Hardware

- Raspberry Pi 4 Model B (2GB RAM)
- Argon One case (I2C fan + power button)
- Xbox Wireless Controller (Bluetooth)
- HDMI CEC-compatible TV

## Quick Install

Flash the latest LibreELEC 12 image for RPi4, then run:

```bash
# From a machine with SSH access to the Pi
git clone https://github.com/jeremiejt38/akasha-os.git
cd akasha-os
./scripts/apply.sh <pi-ip> <pi-password>
```

Or download a pre-built image from [Releases](https://github.com/jeremiejt38/akasha-os/releases).

## Structure

```
akasha-os/
├── boot/               # /flash/ partition (config.txt, cmdline.txt, splash)
├── system/             # /storage/.config/ (autostart, CEC, systemd services)
├── kodi/
│   ├── media/          # Kodi splash screen
│   ├── addons/         # Custom addons (Akasha Settings, Cloud Gaming)
│   ├── scripts/        # Cloud gaming Docker launcher + watchdog
│   └── userdata/       # Controller buttonmaps
├── skin-patches/       # Arctic Horizon 2 modifications
├── scripts/            # Build & deploy tools
└── .github/workflows/  # CI: auto-build updated images
```

## Build

The GitHub Actions workflow automatically:
1. Downloads the latest LibreELEC 12 RPi4 image
2. Mounts and patches it with Akasha OS customizations
3. Publishes a ready-to-flash `.img.gz` as a release artifact

## Dependencies

| Component | Source | Purpose |
|-----------|--------|---------|
| LibreELEC 12 | [libreelec.tv](https://libreelec.tv) | Base OS |
| Arctic Horizon 2 | Kodi repo | Skin |
| Docker | LibreELEC addon repo | Container runtime for gaming |
| Steam Link | [meekys/plugin.program.steamlink](https://github.com/meekys/plugin.program.steamlink) | PC game streaming |
| Moonlight | [veldenb/plugin.program.moonlight-qt](https://github.com/veldenb/plugin.program.moonlight-qt) | NVIDIA game streaming |
| Jellyfin | [jellyfin/jellyfin-kodi](https://github.com/jellyfin/jellyfin-kodi) | Media server client |
| Chromium (Docker) | Debian Bookworm arm32v7 | Cloud gaming browser |

## License

MIT
