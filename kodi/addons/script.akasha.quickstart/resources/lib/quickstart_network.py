"""Akasha Quick Start -- network detection/scan/connect helpers.

LibreELEC uses connman (connmanctl) for network management, not Kodi's
own network settings (system:network only covers proxy/bandwidth --
confirmed in docs/settings/decisions.md). Real connectivity is verified
with an actual HTTP request rather than just "connected to the router",
per plan 3aba4284 section 3.

Parsing (parse_connman_services) has no xbmc*/subprocess dependency so
it stays unit-testable; the actual system calls are thin wrappers kept
separate so tests can exercise the parsing logic against captured
connmanctl output without touching the real network stack.
"""
import glob
import re
import subprocess
import urllib.request

CONNECTIVITY_CHECK_URL = 'http://connectivitycheck.gstatic.com/generate_204'
CONNECTIVITY_TIMEOUT = 4

_SERVICE_ID_RE = re.compile(r'((?:ethernet|wifi)_\S+)\s*$')


def parse_connman_services(output):
    """Parse `connmanctl services` plain-text output.

    Each line looks like (favorite marker `*` optional, columns aligned
    with padding, not a fixed delimiter):
        *AO Wired                ethernet_dca632af47be_cable
        *   Bbox-3AEEFA4E        wifi_..._managed_psk
            Freebox 324429       wifi_..._managed_psk

    Returns a list of {'name', 'service_id', 'favorite', 'is_wifi'}, in
    the order connmanctl printed them (already best-signal-first).
    """
    services = []
    for line in output.splitlines():
        if not line.strip():
            continue
        favorite = line.startswith('*')
        rest = line[1:] if favorite else line
        match = _SERVICE_ID_RE.search(rest)
        if not match:
            continue
        service_id = match.group(1)
        name = rest[:match.start()].strip()
        if not name:
            continue
        services.append({
            'name': name,
            'service_id': service_id,
            'favorite': favorite,
            'is_wifi': service_id.startswith('wifi_'),
        })
    return services


def has_internet_access(url=CONNECTIVITY_CHECK_URL, timeout=CONNECTIVITY_TIMEOUT):
    """Real connectivity check (an actual request), not just "has an IP"."""
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def ethernet_carrier_present():
    """True if any physical (non-loopback, non-wireless) interface reports
    a link carrier -- independent of connman's own service bookkeeping,
    used to decide whether to auto-skip the Wi-Fi picker (section 3:
    "cas Ethernet deja actif au demarrage")."""
    for path in glob.glob('/sys/class/net/*/carrier'):
        iface = path.split('/')[-2]
        if iface == 'lo' or iface.startswith('wl'):
            continue
        try:
            with open(path) as f:
                if f.read().strip() == '1':
                    return True
        except OSError:
            continue
    return False


def get_services():
    result = subprocess.run(
        ['connmanctl', 'services'], capture_output=True, text=True, timeout=10)
    return parse_connman_services(result.stdout)


def scan_wifi(timeout=15):
    subprocess.run(['connmanctl', 'scan', 'wifi'], timeout=timeout)


def list_wifi_networks():
    scan_wifi()
    return [s for s in get_services() if s['is_wifi']]


def connect_wifi(service_id, passphrase=None, timeout=25):
    """Connect to a Wi-Fi service.

    `connmanctl connect <service>` run directly (not through connmanctl's
    own multi-command script mode) blocks synchronously until the
    connection actually succeeds or fails and prints "Connected ..." --
    confirmed live against a real network. Piping commands through
    script mode instead (`agent on\\nconnect ...\\nquit`) was tried first
    but `quit` was processed before `connect` actually finished,
    returning "idle" every time regardless of the real outcome. The
    passphrase (only needed for a network without saved credentials) is
    piped over stdin to the same single command, which connman's own
    interactive agent prompt reads.
    """
    args = ['connmanctl', 'connect', service_id]
    try:
        result = subprocess.run(
            args, input=(passphrase + '\n') if passphrase else None,
            capture_output=True, text=True, timeout=timeout)
        output = (result.stdout or '') + (result.stderr or '')
        ok = 'connected' in output.lower() and 'error' not in output.lower()
        return ok, output
    except subprocess.TimeoutExpired:
        return False, 'Timeout en attente de connmanctl'
