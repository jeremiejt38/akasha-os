"""Akasha Overlay — system stats overlay service.

Pushes live system info (CPU governor, frequency, fan, load) into Kodi skin
strings so that they can be displayed by a skin overlay. The overlay itself is
rendered by the skin; this service only refreshes the dynamic values.

The overlay is toggled from Akasha Settings (script.akasha.settings) via the
"overlay.enabled" setting. Visibility is controlled by the skin setting
Skin.HasSetting(akasha_overlay).
"""
import os
import subprocess
import time
import xbmc
import xbmcaddon

SETTINGS_ID = 'script.akasha.settings'
SETTING_KEY = 'overlay.enabled'
CHECK_INTERVAL = 1.0


class SystemStats:
    def __init__(self):
        self.last_cpu = {}

    @staticmethod
    def _read_int(path, default=0):
        try:
            with open(path, 'r') as f:
                return int(f.read().strip())
        except Exception:
            return default

    @staticmethod
    def _read_str(path, default='?'):
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except Exception:
            return default

    def cpu_usage(self):
        """Return overall CPU usage percentage."""
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
            parts = list(map(int, line.split()[1:8]))
            idle = parts[3]
            total = sum(parts)
            prev_total = self.last_cpu.get('total', total)
            prev_idle = self.last_cpu.get('idle', idle)
            self.last_cpu['total'] = total
            self.last_cpu['idle'] = idle
            diff_total = total - prev_total
            diff_idle = idle - prev_idle
            if diff_total <= 0:
                return 0
            return int((diff_total - diff_idle) * 100 / diff_total)
        except Exception:
            return 0

    def cpu_freq(self):
        try:
            freqs = []
            for cpu in os.listdir('/sys/devices/system/cpu'):
                if not cpu.startswith('cpu'):
                    continue
                path = '/sys/devices/system/cpu/{}/cpufreq/scaling_cur_freq'.format(cpu)
                if os.path.exists(path):
                    freqs.append(self._read_int(path) // 1000)
            if freqs:
                return sum(freqs) // len(freqs)
        except Exception:
            pass
        return 0

    def cpu_governor(self):
        return self._read_str('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', '?')

    def ram_usage(self):
        try:
            total = avail = 0
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        total = int(line.split()[1])
                    elif line.startswith('MemAvailable:'):
                        avail = int(line.split()[1])
                        break
            if total:
                return (total - avail) * 100 // total
        except Exception:
            pass
        return 0

    def cpu_temp(self):
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                return round(int(f.read().strip()) / 1000.0, 1)
        except Exception:
            return 0

    def fan_status(self):
        try:
            result = subprocess.run(
                ['/storage/.kodi/addons/virtual.system-tools/bin/i2cget', '-y', '1', '0x1a'],
                capture_output=True, text=True, timeout=1
            )
            val = int(result.stdout.strip(), 16)
            if val == 0:
                return '0%'
            # Argon One fan register can return either a percentage or a raw 0-255 value.
            if val <= 100:
                pct = val
            else:
                pct = round(val / 2.55)
            return '{}%'.format(min(pct, 100))
        except Exception:
            return '?'

    def load_avg(self):
        try:
            with open('/proc/loadavg', 'r') as f:
                return f.read().split()[0]
        except Exception:
            return '?'

    def uptime(self):
        try:
            with open('/proc/uptime', 'r') as f:
                seconds = float(f.readline().split()[0])
            days = int(seconds) // 86400
            hours = (int(seconds) % 86400) // 3600
            mins = (int(seconds) % 3600) // 60
            if days:
                return '{}j{:02d}h{:02d}'.format(days, hours, mins)
            return '{}h{:02d}'.format(hours, mins)
        except Exception:
            return '?'

    def update(self):
        # Seed CPU usage sample, then wait briefly for a second reading.
        self.cpu_usage()
        time.sleep(0.3)
        return {
            'cpu': self.cpu_usage(),
            'freq': self.cpu_freq(),
            'gov': self.cpu_governor(),
            'ram': self.ram_usage(),
            'temp': self.cpu_temp(),
            'fan': self.fan_status(),
            'load': self.load_avg(),
            'uptime': self.uptime(),
        }


def get_enabled():
    try:
        addon = xbmcaddon.Addon(SETTINGS_ID)
        return addon.getSetting(SETTING_KEY).lower() == 'true'
    except Exception:
        return False


def set_skin_strings(data):
    """Push dynamic values into Skin.String properties for the overlay."""
    # Use SetProperty on the Home window so they are reachable from the global overlay.
    try:
        xbmc.executebuiltin('Skin.SetString(akasha_overlay_governor,{})'.format(data['gov']))
        xbmc.executebuiltin('Skin.SetString(akasha_overlay_freq,{})'.format(data['freq']))
        xbmc.executebuiltin('Skin.SetString(akasha_overlay_load,{})'.format(data['load']))
        xbmc.executebuiltin('Skin.SetString(akasha_overlay_fan,{})'.format(data['fan']))
        xbmc.executebuiltin('Skin.SetString(akasha_overlay_temp,{})'.format(data['temp']))
        xbmc.executebuiltin('Skin.SetString(akasha_overlay_uptime,{})'.format(data['uptime']))
    except Exception as e:
        xbmc.log('Akasha Overlay: error setting skin strings: {}'.format(e), xbmc.LOGERROR)


def main():
    monitor = xbmc.Monitor()
    stats = SystemStats()

    # Wait for the GUI before touching skin properties
    if monitor.waitForAbort(5):
        return

    while not monitor.abortRequested():
        try:
            enabled = get_enabled()
            if enabled:
                data = stats.update()
                set_skin_strings(data)
            else:
                # Keep CPU sample seeded while disabled so the first enabled reading is instant.
                stats.cpu_usage()
        except Exception as e:
            xbmc.log('Akasha Overlay error: {}'.format(e), xbmc.LOGERROR)

        monitor.waitForAbort(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
