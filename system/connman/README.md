# WiFi reliability fixes (connman)

Root cause of the recurring "WiFi password popup" bug on boot:
the onboard RPi4 WiFi regulatory domain is unset (`country 00:
DFS-UNSET`) at boot, which forces most 5GHz channels into
`PASSIVE-SCAN` mode. This makes the very first association attempt
to a 5GHz AP fail with `invalid-key` (a spurious WPA auth failure,
not an actual wrong password). connman then treats the profile's
passphrase as invalid and asks its registered agent (Kodi) for a
new one — hence the popup.

## Fix 1 — Set the WiFi regulatory domain before connman starts

`system/system.d/wifi-regdomain.service` runs `iw reg set FR` and is
ordered `Before=connman.service`. This unlocks active-scan on the
5170-5250 MHz band (where most home 5GHz SSIDs live) before connman
attempts to associate, eliminating the boot-time `invalid-key`
failure.

Deploy: copy to `/storage/.config/system.d/wifi-regdomain.service`,
then `systemctl daemon-reload && systemctl enable --now wifi-regdomain`.

## Fix 2 — Provisioning file (persist passphrase properly)

`wifi.config.example` → deploy as `/storage/.cache/connman/wifi.config`
(with the real SSID/passphrase, **never commit the real file**).
This is connman's official provisioning mechanism: once a service is
linked to a provisioning file (visible as `Config.file=wifi` in its
`settings`), connman never needs to interactively ask for a passphrase
again for that network.

## Fix 3 — Reduce popup annoyance as a safety net

`connman_main.conf.example` → deploy as `/storage/.config/connman_main.conf`.
Sets `InputRequestTimeout = 1` (down from the 120s default) so that
*if* connman ever does ask for a passphrase interactively, the Kodi
popup auto-dismisses after 1 second instead of blocking the UI.

## Fix 4 — Non-destructive watchdog

`../wifi-watchdog.sh` (deployed as `/storage/.config/wifi-watchdog.sh`,
service `../system.d/wifi-watchdog.service`) periodically checks WiFi
connectivity. It NEVER deletes/recreates connman profiles (that caused
an infinite popup loop in an earlier iteration) — it only ensures the
passphrase is present in the provisioning file and calls `connmanctl
connect`, with a 60s cooldown between attempts.

## Deployment notes

The real passphrase files (`/storage/.cache/connman/wifi.config`,
the per-service `settings` file) live only on the device, never in
this repo.
