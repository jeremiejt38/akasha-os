"""Akasha Quick Start -- first-run detection and step metadata.

No xbmc* import so this stays unit-testable with plain `python3 -m
unittest`, and safely delegated to Talos (see docs/talos-strategy.md in
the akasha-os repo).
"""
import os

MARKER_PATH = '/storage/.config/akasha-os/quickstart-completed'

# (step_id, title) in the order fixed by the cahier des charges 3aba4284
# section 2. STEP_NETWORK is the only blocking one (no "Passer" until
# connectivity is confirmed, see section 3).
STEP_WELCOME = 0
STEP_LANGUAGE = 1
STEP_NETWORK = 2
STEP_DISPLAY = 3
STEP_CONTROLLERS = 4
STEP_ACCOUNTS = 5
STEP_CLOUD_GAMING = 6
STEP_POWER = 7
STEP_PROFILE = 8
STEP_SUMMARY = 9

STEPS = (
    (STEP_WELCOME, 'Bienvenue'),
    (STEP_LANGUAGE, 'Langue et region'),
    (STEP_NETWORK, 'Connexion reseau'),
    (STEP_DISPLAY, 'Affichage et son'),
    (STEP_CONTROLLERS, 'Manette et telecommande'),
    (STEP_ACCOUNTS, 'Comptes de contenu'),
    (STEP_CLOUD_GAMING, 'Cloud gaming'),
    (STEP_POWER, 'Preferences energie'),
    (STEP_PROFILE, 'Profil utilisateur'),
    (STEP_SUMMARY, 'Recapitulatif'),
)

# Steps where "Passer"/"Configurer plus tard" is not offered -- section 3:
# "Suivant/Precedent toujours disponibles (sauf etape 3 tant que la
# connectivite n'est pas validee)". Bienvenue/Recapitulatif have no
# meaningful "skip" either (nothing to configure there).
NON_SKIPPABLE_STEPS = (STEP_WELCOME, STEP_NETWORK, STEP_SUMMARY)


def is_completed(marker_path=MARKER_PATH):
    return os.path.exists(marker_path)


def mark_completed(marker_path=MARKER_PATH):
    """Persist the "first run done" marker. Only ever called from the real
    Summary step's "Terminer" button (see section 1: an early exit must
    NOT count as completed)."""
    os.makedirs(os.path.dirname(marker_path), exist_ok=True)
    with open(marker_path, 'w') as f:
        f.write('1')


def reset_completed(marker_path=MARKER_PATH):
    """Used only for manual relaunch / testing -- the wizard itself never
    calls this; completion is one-directional in normal use."""
    try:
        os.remove(marker_path)
    except OSError:
        pass


def step_title(step_id):
    for sid, title in STEPS:
        if sid == step_id:
            return title
    return ''


def is_skippable(step_id):
    return step_id not in NON_SKIPPABLE_STEPS


def clamp_step(step_id):
    return max(0, min(step_id, len(STEPS) - 1))
