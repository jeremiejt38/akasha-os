#!/usr/bin/env python3
"""
wifi-silent-agent.py — Akasha OS silent connman Agent

Registers itself as connman's D-Bus Agent BEFORE Kodi's own
LibreELEC-settings addon does. connman only allows a single
registered Agent at a time, so once we're registered, Kodi's
RegisterAgent call fails silently and its "WiFi password" popup
can never appear again.

Whenever connman calls RequestInput (e.g. after a transient
"invalid-key" auth failure at boot — a known RPi4/iwd timing issue,
not an actually wrong password), we reply instantly with the known
passphrase from /storage/.cache/connman/wifi.config. No dialog, no
user interaction, ever.

Logs every agent callback to /storage/.config/wifi-watchdog.log so
it can be diagnosed after the fact.
"""

import asyncio
import configparser
import time

import dbussy as dbus
from dbussy import DBUS
import ravel

AGENT_PATH = "/kodi/agent/akasha_silent"
PROVISIONING_FILE = "/storage/.cache/connman/wifi.config"
LOG_FILE = "/storage/.config/wifi-watchdog.log"


def log_event(message):
    with open(LOG_FILE, "a") as f:
        f.write("%s [silent-agent] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), message))


def load_known_networks():
    """Parse the connman provisioning file into {ssid_name: (passphrase, ssid_hex)}."""
    networks = {}
    parser = configparser.ConfigParser()
    try:
        parser.read(PROVISIONING_FILE)
    except Exception as e:
        log_event("ERROR reading provisioning file: %s" % e)
        return networks
    for section in parser.sections():
        if section == "global":
            continue
        name = parser.get(section, "Name", fallback=None)
        passphrase = parser.get(section, "Passphrase", fallback=None)
        ssid_hex = parser.get(section, "SSID", fallback=None)
        if not ssid_hex and name:
            # Derive hex from the displayed name; this matches how connman encodes simple SSIDs
            ssid_hex = name.encode("utf-8").hex()
        if name and passphrase:
            networks[name] = (passphrase, ssid_hex.lower() if ssid_hex else None)
    return networks


def extract_service_ssid_hex(service_path):
    """Extract the hex SSID from a connman service object path.

    Service paths look like:
      /net/connman/service/wifi_<mac>_<ssidhex>_managed_psk
    """
    parts = service_path.rstrip("/").split("_")
    if len(parts) >= 4 and parts[0].endswith("/service/wifi"):
        return parts[2].lower()
    return None


@ravel.interface(ravel.INTERFACE.SERVER, name="net.connman.Agent")
class SilentAgent:

    @ravel.method(name="Release", in_signature="", out_signature="")
    def Release(self):
        log_event("Release() called (agent unregistered)")

    @ravel.method(name="ReportError", in_signature="os", out_signature="")
    def ReportError(self, service, error):
        log_event("ReportError(service=%s, error=%s) — silently acknowledged" % (service, error))

    @ravel.method(name="RequestBrowser", in_signature="os", out_signature="")
    def RequestBrowser(self, service, url):
        log_event("RequestBrowser(service=%s, url=%s) — ignored" % (service, url))

    @ravel.method(name="RequestInput", in_signature="oa{sv}", out_signature="a{sv}")
    def RequestInput(self, service, fields):
        networks = load_known_networks()
        response = {}
        wanted_name = None
        wanted_pass = None

        # connman service paths contain the hex-encoded SSID, not the plain name.
        # Match either by that hex value or by the human-readable name as a fallback.
        service_ssid_hex = extract_service_ssid_hex(service)
        for ssid_name, (passphrase, ssid_hex) in networks.items():
            if service_ssid_hex and ssid_hex and service_ssid_hex == ssid_hex:
                wanted_name = ssid_name
                wanted_pass = passphrase
                break
            if ssid_name and ssid_name in service:
                wanted_name = ssid_name
                wanted_pass = passphrase
                break

        if wanted_name and wanted_pass and "Passphrase" in fields:
            response["Passphrase"] = ("s", wanted_pass)
            log_event("RequestInput(service=%s) — replied with known passphrase" % service)
        else:
            log_event(
                "RequestInput(service=%s, fields=%s) — no known passphrase, ignoring"
                % (service, list(fields.keys()))
            )
        return response

    @ravel.method(name="Cancel", in_signature="", out_signature="")
    def Cancel(self):
        log_event("Cancel() called")


async def mainline():
    loop = dbus.get_event_loop()
    conn = await ravel.system_bus_async(loop)
    conn.register(path=AGENT_PATH, fallback=False, interface=SilentAgent())

    manager = await conn["net.connman"]["/"].get_async_interface("net.connman.Manager")
    try:
        await manager.RegisterAgent(AGENT_PATH)
        log_event("Registered as connman Agent at %s" % AGENT_PATH)
    except Exception as e:
        log_event("ERROR registering agent (already registered?): %s" % e)

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    loop = dbus.get_event_loop()
    loop.run_until_complete(mainline())
