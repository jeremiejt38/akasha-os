"""Akasha Aura -- settings engine (plan b81d3f6a).

Typed sources behind one interface so the declarative catalog
(settings_catalog.py) can read and *write* real values -- this is what
makes the unified settings panel an actual settings surface rather than
the old shortcut menu (aura_settings_panel.py pre-refactor).

Sources:
    kodi_setting  -- Kodi's own settings via JSON-RPC
                     (Settings.GetSettings + Settings.SetSettingValue)
    addon_setting -- another addon's settings.xml entry via xbmcaddon
    custom        -- named Python callables registered in REGISTRY
    system        -- LibreELEC backends via subprocess (connmanctl,
                     bluetoothctl, files)
    action        -- builtins that leave the panel (ActivateWindow,
                     RunAddon, RunScript)

Everything xbmc/subprocess-related is funnelled through a `Backend`
object injected into the functions, so the whole module is unit-testable
without a Kodi runtime.
"""
import json

try:
    import xbmc
    import xbmcaddon
    import xbmcgui
except ImportError:  # unit tests
    xbmc = xbmcaddon = xbmcgui = None


# ---------------------------------------------------------------------------
# Backend -- thin wrappers around the outside world.
# ---------------------------------------------------------------------------

class Backend(object):
    """Production backend. Tests subclass / replace the methods."""

    def kodi_rpc(self, method, params=None):
        req = {'jsonrpc': '2.0', 'method': method, 'id': 1}
        if params is not None:
            req['params'] = params
        raw = xbmc.executeJSONRPC(json.dumps(req))
        return json.loads(raw).get('result') or {}

    def addon_get(self, addon_id, key):
        return xbmcaddon.Addon(addon_id).getSetting(key)

    def addon_set(self, addon_id, key, value):
        xbmcaddon.Addon(addon_id).setSetting(key, value)

    def run(self, argv, timeout=5):
        """Subprocess runner -> (rc, stdout). Never raises."""
        import subprocess
        try:
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  timeout=timeout)
            return proc.returncode, proc.stdout or ''
        except Exception:
            return -1, ''

    def read_file(self, path):
        try:
            with open(path) as f:
                return f.read()
        except OSError:
            return ''

    def input_text(self, heading, default='', hidden=False):
        dlg = xbmcgui.Dialog()
        if hidden:
            return dlg.input(heading, default,
                             type=xbmcgui.INPUT_ALPHANUM,
                             option=xbmcgui.ALPHANUM_HIDE_INPUT)
        return dlg.input(heading, default, type=xbmcgui.INPUT_ALPHANUM)

    def input_numeric(self, heading, default=''):
        return xbmcgui.Dialog().numeric(0, heading, default)

    def exec_builtin(self, builtin):
        xbmc.executebuiltin(builtin)

    def notify(self, message):
        xbmcgui.Dialog().notification('Akasha OS', message,
                                      xbmcgui.NOTIFICATION_INFO, 3000)

    def addon_version(self, addon_id):
        try:
            return xbmcaddon.Addon(addon_id).getAddonInfo('version')
        except Exception:
            return ''

    def log(self, message):
        if xbmc is not None:
            xbmc.log('Akasha Aura Settings: {}'.format(message), xbmc.LOGINFO)


# ---------------------------------------------------------------------------
# Kodi settings cache -- one GetSettings call feeds every kodi_setting row.
# ---------------------------------------------------------------------------

class KodiSettingsCache(object):
    """id -> descriptor {type, value, options, enabled} from
    Settings.GetSettings. Unknown ids simply miss the map -- the caller
    hides those rows rather than showing a broken one (catalogue ids are
    written ahead of the live-Pi verification snapshot)."""

    def __init__(self, backend):
        self._backend = backend
        self._map = None

    def _ensure(self):
        if self._map is None:
            result = self._backend.kodi_rpc(
                'Settings.GetSettings', {'level': 'expert'})
            self._map = {s['id']: s
                         for s in result.get('settings', []) if 'id' in s}
        return self._map

    def has(self, setting_id):
        return setting_id in self._ensure()

    def get(self, setting_id):
        entry = self._ensure().get(setting_id)
        return None if entry is None else entry.get('value')

    def options(self, setting_id):
        """enum -> [{'value':..,'label':..}], else []."""
        entry = self._ensure().get(setting_id) or {}
        return entry.get('options') or []

    def set(self, setting_id, value):
        result = self._backend.kodi_rpc(
            'Settings.SetSettingValue',
            {'setting': setting_id, 'value': value})
        # SetSettingValue returns true/false; refresh the cached value on
        # success so subsequent reads don't hit a stale snapshot.
        ok = result is True or (isinstance(result, dict)
                                and result.get('result') is True)
        if ok:
            entry = self._ensure().get(setting_id)
            if entry is not None:
                entry['value'] = value
        return ok

    def invalidate(self):
        self._map = None


# ---------------------------------------------------------------------------
# Typed sources. get() returns the raw value, options() the pickable values,
# display() the human-readable subtitle, set() a bool.
# ---------------------------------------------------------------------------

class KodiSettingSource(object):
    def __init__(self, setting_id):
        self.setting_id = setting_id

    def get(self, backend, cache):
        return cache.get(self.setting_id)

    def options(self, backend, cache):
        return cache.options(self.setting_id)

    def set(self, backend, cache, value):
        return cache.set(self.setting_id, value)

    def available(self, backend, cache):
        return cache.has(self.setting_id)


class AddonSettingSource(object):
    def __init__(self, addon_id, key):
        self.addon_id = addon_id
        self.key = key

    def get(self, backend, cache):
        return backend.addon_get(self.addon_id, self.key)

    def options(self, backend, cache):
        return []

    def set(self, backend, cache, value):
        try:
            backend.addon_set(self.addon_id, self.key, value)
            return True
        except Exception:
            return False

    def available(self, backend, cache):
        try:
            self.get(backend, cache)
            return True
        except Exception:
            return False


class CustomSource(object):
    """Delegates to callables registered by name in REGISTRY -- keeps the
    catalog declarative while allowing real dynamic behaviour."""

    def __init__(self, getter, setter=None, options=None):
        self.getter = getter
        self.setter = setter
        self.opts = options

    def get(self, backend, cache):
        fn = REGISTRY.get(self.getter)
        return None if fn is None else fn(backend)

    def options(self, backend, cache):
        if self.opts is None:
            return []
        fn = REGISTRY.get(self.opts)
        return [] if fn is None else fn(backend)

    def set(self, backend, cache, value):
        fn = REGISTRY.get(self.setter) if self.setter else None
        return False if fn is None else bool(fn(backend, value))

    def available(self, backend, cache):
        return self.getter in REGISTRY


class SystemSource(object):
    """connman / bluetooth / libreelec ops via subprocess."""

    def __init__(self, backend_op):
        self.backend_op = backend_op  # (backend, op) tuple

    def get(self, backend, cache):
        backend_name, op = self.backend_op
        return _system_get(backend, backend_name, op)

    def options(self, backend, cache):
        return []

    def set(self, backend, cache, value):
        backend_name, op = self.backend_op
        return _system_set(backend, backend_name, op, value)

    def available(self, backend, cache):
        return True


# ---------------------------------------------------------------------------
# System backends (connman / bluetoothctl / files). Keep each op tiny: they
# run on demand when a screen is built, never eagerly.
# ---------------------------------------------------------------------------

def _system_get(backend, name, op):
    if name == 'connman':
        if op == 'net_status':
            # "*AO Wired ethernet_..._cable" / "*AR WifiName wifi_..._psk"
            rc, out = backend.run(['connmanctl', 'services'])
            for line in out.splitlines():
                if line.startswith('*A'):
                    parts = line.strip().split()
                    kind = 'wifi' if 'wifi' in line else 'ethernet'
                    return {'kind': kind, 'name': ' '.join(parts[1:-1])}
            return {'kind': None, 'name': ''}
        if op == 'wifi_enabled':
            rc, out = backend.run(['connmanctl', 'technologies'])
            for line in out.splitlines():
                if line.strip().startswith('/net/connman/technology/wifi'):
                    # next lines: Powered = True/False
                    idx = out.splitlines().index(line)
                    for sub in out.splitlines()[idx:idx + 8]:
                        if 'Powered' in sub:
                            return 'True' in sub
                    break
            return None
        if op == 'ip_address':
            rc, out = backend.run(
                ['sh', '-c', 'ip -4 addr show scope global | '
                             'awk \'/inet /{print $2}\' | head -1'])
            return out.strip().split('/')[0] if out.strip() else ''
    if name == 'bluetooth':
        if op == 'paired_devices':
            rc, out = backend.run(['bluetoothctl', 'devices', 'Paired'])
            devices = []
            for line in out.splitlines():
                # "Device AA:BB:CC:DD:EE:FF Name"
                if line.startswith('Device '):
                    parts = line.split(' ', 2)
                    if len(parts) == 3:
                        devices.append({'mac': parts[1], 'name': parts[2]})
            return devices
    if name == 'sysinfo':
        if op == 'hostname':
            rc, out = backend.run(['hostname'])
            return out.strip()
        if op == 'cpu_temp':
            raw = backend.read_file('/sys/class/thermal/thermal_zone0/temp')
            try:
                return round(int(raw.strip()) / 1000.0, 1)
            except (ValueError, OSError):
                return None
        if op == 'le_version':
            return backend.read_file('/etc/os-release')
        if op == 'free_mem':
            raw = backend.read_file('/proc/meminfo')
            for line in raw.splitlines():
                if line.startswith('MemAvailable'):
                    return int(line.split()[1]) // 1024
            return None
    return None


def _system_set(backend, name, op, value):
    if name == 'connman':
        if op == 'wifi_enabled':
            rc, _ = backend.run(
                ['connmanctl', 'enable' if value else 'disable', 'wifi'])
            return rc == 0
    if name == 'bluetooth':
        if op == 'connect':
            rc, _ = backend.run(['bluetoothctl', 'connect', value], timeout=15)
            return rc == 0
        if op == 'disconnect':
            rc, _ = backend.run(['bluetoothctl', 'disconnect', value],
                                timeout=10)
            return rc == 0
        if op == 'remove':
            rc, _ = backend.run(['bluetoothctl', 'remove', value])
            return rc == 0
    return False


# ---------------------------------------------------------------------------
# Custom getters/setters registry (Akasha-specific behaviours).
# ---------------------------------------------------------------------------

def _akasha_version(backend):
    # Akasha OS version lives in the Kodi GUI header patch + addon version.
    return backend.addon_version('script.akasha.aura')


def _le_version(backend):
    for line in backend.read_file('/etc/os-release').splitlines():
        if line.startswith('VERSION_ID='):
            return line.split('=', 1)[1].strip('"')
        if line.startswith('LIBREELEC_VERSION='):
            return line.split('=', 1)[1].strip('"')
    return ''


REGISTRY = {
    'akasha.version': _akasha_version,
    'le.version': _le_version,
}
