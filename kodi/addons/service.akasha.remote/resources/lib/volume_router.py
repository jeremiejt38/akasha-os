"""Akasha Remote — volume routing logic.

Maps the remote's volume buttons to one of three destinations:
- 'akasha' : Kodi's own volume (default, no external dependencies).
- 'cec'    : send CEC volume commands to the TV/AVR via cec-ctl.
- 'ir'     : not implemented, would require a dedicated IR blaster.

This module has no xbmc dependency so it can be unit-tested in isolation.
"""
import subprocess

VOLUME_UP = 'volume_up'
VOLUME_DOWN = 'volume_down'
VOLUME_MUTE = 'mute'

ACTIONS = (VOLUME_UP, VOLUME_DOWN, VOLUME_MUTE)

VOLUME_MODES = ('akasha', 'cec', 'ir')


def mode_from_setting(raw):
    """Convert the enum setting index to a mode string."""
    try:
        index = int(raw)
    except (TypeError, ValueError):
        return 'akasha'
    if 0 <= index < len(VOLUME_MODES):
        return VOLUME_MODES[index]
    return 'akasha'

KODI_BUILTINS = {
    VOLUME_UP: 'VolumeUp',
    VOLUME_DOWN: 'VolumeDown',
    VOLUME_MUTE: 'Mute',
}

CEC_UI_CMDS = {
    VOLUME_UP: 'volume-up',
    VOLUME_DOWN: 'volume-down',
    VOLUME_MUTE: 'mute',
}


def route(action, mode, kodi_executebuiltin=None, cec_run=None):
    """Route a volume action according to the configured mode.

    Parameters
    ----------
    action : str
        One of VOLUME_UP, VOLUME_DOWN, VOLUME_MUTE.
    mode : str
        One of 'akasha', 'cec', 'ir'.
    kodi_executebuiltin : callable
        Callback used in 'akasha' mode to run Kodi builtins (injected so
        this module stays testable without xbmc).
    cec_run : callable
        Callback used in 'cec' mode to run cec-ctl (injected for testing).

    Returns
    -------
    bool
        True if the action was handled, False if the mode/action is unknown.
    """
    if action not in ACTIONS:
        return False
    if mode == 'akasha':
        if kodi_executebuiltin is None:
            return False
        kodi_executebuiltin(KODI_BUILTINS[action])
        return True
    if mode == 'cec':
        if cec_run is None:
            return False
        cec_run(CEC_UI_CMDS[action])
        return True
    if mode == 'ir':
        # IR routing requires dedicated hardware and a code database.
        return False
    return False


def cec_volume_command(ui_cmd, device='/dev/cec0'):
    """Return a cec-ctl command list for the given UI command."""
    return [
        'cec-ctl', '-d', device,
        '--user-control-pressed', 'ui-cmd={}'.format(ui_cmd),
    ]


def run_cec_volume_command(ui_cmd, device='/dev/cec0', run=subprocess.run):
    """Send a CEC volume command and the corresponding release message."""
    cmd = cec_volume_command(ui_cmd, device)
    run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run(
        ['cec-ctl', '-d', device, '--user-control-released'],
        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
