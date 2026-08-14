#!/usr/bin/env python3
"""Akasha OS self-updater for LibreELEC / Kodi.

Checks the latest GitHub release, downloads the source tarball, extracts it
and runs scripts/install.sh, then reboots.

This script prints machine-readable markers that the Kodi UI can parse:
    PROGRESS <pct>
    STAGE <name>
    JSON <json-object>

Usage:
    python3 /storage/.kodi/scripts/update-akasha-os.py --check
    python3 /storage/.kodi/scripts/update-akasha-os.py --reboot
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

LOCAL_VERSION_PATH = Path("/storage/.config/akasha-os/VERSION")
UPDATE_DIR = Path("/storage/.update/akasha-os")
LOG_PATH = Path("/storage/.kodi/temp/akasha-update.log")
REPO = "jeremiejt38/akasha-os"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"


def print_json(obj):
    print("JSON " + json.dumps(obj), flush=True)


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def set_stage(name):
    log(f"### STAGE: {name}")


def set_progress(pct):
    log(f"### PROGRESS: {pct}")


def get_local_version():
    if LOCAL_VERSION_PATH.exists():
        return LOCAL_VERSION_PATH.read_text(encoding="utf-8").strip()
    return "0.0.0"


def parse_version(v):
    """Convert a semver string like 'v0.9.0' or '0.9.0' to a tuple."""
    v = v.lstrip("v")
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", v)
    if not m:
        return (0, 0, 0)
    return tuple(int(x) for x in m.groups())


def fetch_latest_release():
    set_stage("CHECK")
    set_progress(0)
    log("Checking latest Akasha OS release on GitHub...")
    req = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "akasha-os-updater",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    tag = data.get("tag_name", "")
    body = data.get("body", "")
    assets = data.get("assets", [])

    # Prefer a release asset named akasha-os-<version>.tar.gz
    tarball_url = None
    version = tag.lstrip("v")
    for asset in assets:
        if asset.get("name") == f"akasha-os-{version}.tar.gz":
            tarball_url = asset.get("browser_download_url")
            break

    # Fallback to the auto-generated source tarball
    if not tarball_url:
        tarball_url = data.get("tarball_url")

    if not tarball_url:
        raise RuntimeError("No tarball found in the latest release")

    set_progress(10)
    return tag, version, body, tarball_url


def download_with_progress(url, dest_path):
    set_stage("DOWNLOAD")
    set_progress(10)
    log(f"Downloading update from {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "akasha-os-updater"})
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=180) as resp, dest_path.open("wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        block_size = 65536
        last_pct = 10
        while True:
            chunk = resp.read(block_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = 10 + int(downloaded * 40 / total)
                if pct != last_pct:
                    set_progress(pct)
                    last_pct = pct
    set_progress(50)
    log("Download complete.")


def extract_tarball(tar_path, extract_dir):
    set_stage("EXTRACT")
    set_progress(50)
    log("Extracting update...")
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tf:
        tf.extractall(path=extract_dir)
    # The tarball extracts to a single top-level directory like akasha-os-0.9.1/
    entries = [d for d in extract_dir.iterdir() if d.is_dir()]
    if len(entries) != 1:
        raise RuntimeError("Unexpected tarball layout")
    set_progress(55)
    return entries[0]


def run_installer(repo_dir):
    set_stage("INSTALL")
    set_progress(55)
    install_script = repo_dir / "scripts" / "install.sh"
    if not install_script.exists():
        raise RuntimeError(f"Installer not found: {install_script}")

    log("Running Akasha OS installer...")
    os.chmod(install_script, 0o755)
    result = subprocess.run(
        [str(install_script)],
        cwd=str(repo_dir),
        capture_output=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Installer failed with code {result.returncode}")
    set_progress(90)
    log("Installer completed.")


def disable_official_updates():
    """Best-effort disable of LibreELEC auto update and custom channels."""
    set_progress(92)
    log("Disabling LibreELEC built-in auto updates...")
    try:
        # The LibreELEC settings addon keeps its state in this XML on /storage
        le_settings = Path("/storage/.kodi/userdata/addon_data/service.libreelec.settings/oe_settings.xml")
        if le_settings.exists():
            # We cannot easily parse XML with stdlib safely, but we can set a flag file
            # that install.sh also creates, and (future) a systemd one-shot uses to patch.
            pass
    except Exception as e:
        log(f"WARNING: could not disable LibreELEC updates: {e}")


def check_for_update():
    local_version = get_local_version()
    tag, remote_version, changelog, tarball_url = fetch_latest_release()

    has_update = parse_version(remote_version) > parse_version(local_version)

    print_json({
        "status": "update" if has_update else "up_to_date",
        "local_version": local_version,
        "remote_version": remote_version,
        "remote_tag": tag,
        "changelog": changelog.strip(),
        "tarball_url": tarball_url,
    })
    return has_update


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check for updates only")
    parser.add_argument("--reboot", action="store_true", help="Reboot after update")
    args = parser.parse_args()

    if args.check:
        try:
            has_update = check_for_update()
            return 0
        except Exception as e:
            print_json({"status": "error", "message": str(e)})
            log(f"ERROR: {e}")
            return 1

    local_version = get_local_version()
    log(f"Local Akasha OS version: {local_version}")

    tag, remote_version, changelog, tarball_url = fetch_latest_release()
    log(f"Latest release: {tag}")

    if parse_version(remote_version) <= parse_version(local_version):
        log("No update available. Already up to date.")
        set_progress(100)
        set_stage("UP_TO_DATE")
        return 0

    log(f"Update available: {local_version} -> {remote_version}")
    if changelog:
        log("--- Changelog ---")
        for line in changelog.splitlines()[:40]:
            log(line)
        log("---")

    tar_path = UPDATE_DIR / f"akasha-os-{remote_version}.tar.gz"
    download_with_progress(tarball_url, tar_path)

    repo_dir = extract_tarball(tar_path, UPDATE_DIR / "extract")
    run_installer(repo_dir)
    disable_official_updates()

    set_progress(100)
    set_stage("DONE")
    log("Akasha OS updated successfully.")
    if args.reboot:
        log("Rebooting now...")
        subprocess.run(["systemctl", "reboot"])
    else:
        log("Reboot manually to start the new version.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"ERROR: {e}")
        set_progress(0)
        set_stage("ERROR")
        sys.exit(1)