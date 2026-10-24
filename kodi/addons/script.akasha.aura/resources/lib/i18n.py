"""Akasha Aura -- user-visible string table (single source of truth).

Kodi resolves <label>33xxx</label> tags and Addon.getLocalizedString()
through resources/language/*/strings.po. Those .po files are generated
from this table by running this module directly:

    PYTHONPATH=resources/lib python3 resources/lib/i18n.py

French is the primary language; English ships as Kodi's mandatory
resource.language.en_gb fallback. Python code calls tr(msgid), which
prefers the Kodi-resolved string and falls back to the French entry so
the addon stays usable (and unit-testable) without a live Kodi runtime.
"""

try:
    import xbmcaddon
except ImportError:  # unit tests / generation outside Kodi
    xbmcaddon = None

# msgctxt id -> (french, english)
STRINGS = {
    # --- top bar / tabs / sidebar / switcher ----------------------------
    33001: ('Recherche', 'Search'),
    33002: ('Divertissement', 'Entertainment'),
    33003: ('Jeux', 'Games'),
    33004: ('App', 'Apps'),
    33005: ('Accueil', 'Home'),
    33006: ('Bibliothèques', 'Libraries'),
    33007: ('Plus', 'More'),
    33008: ('Recommandé', 'Recommended'),
    33009: ('Catégories', 'Categories'),
    33010: ('Bibliothèque', 'Library'),
    33011: ('Collections', 'Collections'),
    33012: ('Mes Apps', 'My Apps'),
    33013: ('Store', 'Store'),
    33014: ('Tendances', 'Trending'),
    33015: ('Pour vous', 'For You'),
    33016: ('Autres', 'Other'),
    33017: ('Applications récentes', 'Recent apps'),
    33018: ('Double Home pour ouvrir', 'Double-press Home to open'),
    33019: ('Paramètres', 'Settings'),
    33020: ('Retour', 'Back'),
    33021: ('Lancer', 'Launch'),
    33022: ('Épingler / Désépingler', 'Pin / Unpin'),
    33023: ('Désinstaller', 'Uninstall'),

    # --- divertissement browse / library / games / power ----------------
    33050: ('Séries TV', 'TV Shows'),
    33051: ('Films', 'Movies'),
    33052: ('Tout', 'All'),
    33053: ('Tous', 'All'),
    33054: ('Non vus', 'Unwatched'),
    33055: ('Vus', 'Watched'),
    33056: ("Date d'ajout", 'Date added'),
    33057: ('Titre', 'Title'),
    33058: ('Date de sortie', 'Release date'),
    33059: ('Note', 'Rating'),
    33060: ('Ajout', 'Added'),
    33061: ('Filtre', 'Filter'),
    33062: ('Trier par', 'Sort by'),
    33063: ('Genre', 'Genre'),
    33064: ('Lire', 'Play'),
    33065: ('Aléatoire', 'Shuffle'),
    33066: ('Réinitialiser les filtres', 'Reset filters'),
    33067: ('Aucune bibliothèque vidéo disponible', 'No video library available'),
    33068: ('{} — erreur de chargement', '{} — loading error'),
    33069: ('{} élément(s)', '{} item(s)'),
    33070: ('pour « {} »', 'for "{}"'),
    33071: ('{} — {} catégorie(s)', '{} — {} categories'),
    33072: ('Aucun résultat pour « {} »', 'No results for "{}"'),
    33073: ('Connecté au Connector Akasha OS', 'Connected to Akasha OS Connector'),
    33074: ('Connexion au Connector échouée', 'Connector connection failed'),
    33075: ('Lecture indisponible (flux introuvable)', 'Playback unavailable (stream not found)'),
    33076: ('Section', 'Section'),
    33077: ('Gérer les bibliothèques', 'Manage libraries'),
    33078: ('Désépingler {}', 'Unpin {}'),
    33079: ('Épingler {}', 'Pin {}'),
    33080: ('Monter {}', 'Move {} up'),
    33081: ('Descendre {}', 'Move {} down'),
    33082: ('Autres applications de jeu', 'Other game apps'),
    33083: ('SteamLink non configuré — clé API et SteamID64 requis',
            'SteamLink not configured — API key and SteamID64 required'),
    33084: ('Erreur de chargement de la bibliothèque Steam',
            'Failed to load the Steam library'),
    33085: ('{} jeu(x) Steam', '{} Steam game(s)'),
    33086: ('Sunshine non configuré — URL, utilisateur et mot de passe requis',
            'Sunshine not configured — URL, username and password required'),
    33087: ('Erreur de chargement des applications Sunshine',
            'Failed to load Sunshine apps'),
    33088: ('{} application(s) Sunshine', '{} Sunshine app(s)'),
    33089: ("Mettre l'appareil et le téléviseur en veille ?",
            'Put the device and TV to sleep?'),
    33090: ('Redémarrer', 'Restart'),
    33091: ('Redémarrer Akasha', 'Restart Akasha'),
    33092: ('Redémarrer Akasha maintenant ?', 'Restart Akasha now?'),
    33093: ('Redémarrer le système', 'Reboot the system'),
    33094: ('Redémarrer le système maintenant ?', 'Reboot the system now?'),
    33095: ('Éteindre le système maintenant ?\n(La TV sera aussi éteinte via CEC)',
            'Power off now?\n(The TV will also turn off via CEC)'),
    33096: ('par', 'by'),
    33097: ('Résultats pour « {} »', 'Results for "{}"'),

    # --- detail window / person page ------------------------------------
    33100: ('Cast & Crew', 'Cast & Crew'),
    33101: ('Série', 'Show'),
    33102: ('Saison {}', 'Season {}'),
    33103: ('{} Saison{}', '{} Season{}'),
    33104: ('Regarder', 'Watch'),
    33105: ('Reprendre S{} E{}', 'Resume S{} E{}'),
    33106: ('Reprendre · {} restantes', 'Resume · {} left'),
    33107: ('Recommencer', 'Restart'),
    33108: ('Bande-annonce', 'Trailer'),
    33109: ('Bonus', 'Extras'),
    33110: ('Ajouter à ma liste', 'Add to my list'),
    33111: ('Noter', 'Rate'),
    33112: ('Marquer comme vu', 'Mark as watched'),
    33113: ('Marquer comme non vu', 'Mark as unwatched'),
    33114: ("Plus d'actions", 'More actions'),
    33115: ('Sous-titres', 'Subtitles'),
    33116: ('Infos fichier', 'File info'),
    33117: ('Réalisé par {}', 'Directed by {}'),
    33118: ('Marqué comme vu', 'Marked as watched'),
    33119: ('Marqué comme non vu', 'Marked as unwatched'),
    33120: ('Note enregistrée : {}', 'Rating saved: {}'),
    33121: ('Aucun épisode lisible', 'No playable episode'),
    33122: ('Transcodage refusé par le serveur', 'Transcoding refused by the server'),
    33123: ('URL invalide : {}', 'Invalid URL: {}'),
    33124: ('Watchlist indisponible', 'Watchlist unavailable'),
    33125: ('Filmographie ({} titre{})', 'Filmography ({} title{})'),
    33126: ('Aucun titre de cette personne dans les bibliothèques.',
            'No titles for this person in your libraries.'),
    33127: ('Acteur', 'Actor'),
    33128: ('saison(s)', 'season(s)'),
    33129: ('épisode(s)', 'episode(s)'),
    33130: ('Qualité indisponible sur ce flux', 'Quality unavailable on this stream'),
    33131: ('{} restantes', '{} left'),
    33132: ('Vidéo', 'Video'),
    33133: ('Film', 'Movie'),
    33135: ('Saison', 'Season'),
    33136: ('Épisode', 'Episode'),
    33137: ('Continuer à regarder', 'Continue Watching'),
    33138: ('Ajoutés récemment', 'Recently Added'),
    33139: ('Sorties récentes', 'Recently Released'),
    33140: ('Vus récemment', 'Recently Watched'),
    33141: ('dans {}', 'in {}'),
    33154: ('Réalisateur', 'Director'),

    # Discover/provider hub titles (Plex "Tendances" rows)
    33160: ('Nouvelles bandes-annonces', 'New trailers'),
    33161: ('Bandes-annonces en vogue', 'Trending trailers'),
    33162: ('Recommandé sur vos services', 'Recommended on your services'),
    33163: ('Les plus suivis cette semaine', 'Most watchlisted this week'),
    33164: ('Bandes-annonces de votre Watchlist', 'Trailers from your Watchlist'),
    33165: ('Disponibles sur vos services', 'Available on your services'),
    33166: ('Bientôt disponible', 'Coming soon'),
    33167: ('Disponibles à la location', 'Available to rent'),
    33168: ('Parcourir par genre', 'Browse by genre'),
    33169: ("Cette semaine dans l'histoire", 'This week in history'),
    33170: ('Blockbusters à venir', 'Upcoming blockbusters'),
    33171: ('Vos services', 'Your services'),

    # --- search ----------------------------------------------------------
    33150: ('Séries', 'Shows'),
    33151: ('Épisodes', 'Episodes'),
    33152: ('Personnes', 'People'),

    # --- player OSD menu -------------------------------------------------
    33200: ('Pistes', 'Tracks'),
    33201: ('Audio', 'Audio'),
    33202: ('Désactivés', 'Off'),
    33203: ('Aucune piste détectée', 'No track detected'),
    33204: ('Piste {}', 'Track {}'),
    33205: ('Qualité', 'Quality'),
    33206: ('Qualité indisponible hors lecture Plex',
            'Quality unavailable outside Plex playback'),
    33207: ('Avancé', 'Advanced'),
    33208: ('Pistes audio et sous-titres…', 'Audio & subtitle tracks…'),
    33209: ('Paramètres vidéo Kodi…', 'Kodi video settings…'),
    33210: ('Originale', 'Original'),
    33211: ('Paramètres audio Kodi…', 'Kodi audio settings…'),

    # --- settings panel --------------------------------------------------
    33250: ('Réseau & Connectivité', 'Network & Connectivity'),
    33251: ('Wi-Fi, Ethernet, VPN (LibreELEC)', 'Wi-Fi, Ethernet, VPN (LibreELEC)'),
    33252: ('Proxy et bande passante (Kodi)', 'Proxy and bandwidth (Kodi)'),
    33253: ('Comptes & Services', 'Accounts & Services'),
    33254: ('Cloud gaming (Steam, Sunshine/Moonlight)',
            'Cloud gaming (Steam, Sunshine/Moonlight)'),
    33255: ('Affichage & Son', 'Display & Sound'),
    33256: ('Résolution, HDR, HDMI-CEC, sortie audio (Kodi)',
            'Resolution, HDR, HDMI-CEC, audio output (Kodi)'),
    33257: ('Manettes & Télécommandes', 'Controllers & Remotes'),
    33258: ('Appairage Bluetooth (LibreELEC)', 'Bluetooth pairing (LibreELEC)'),
    33259: ('Batterie et destination des touches volume',
            'Battery and volume-key routing'),
    33260: ('Bibliothèque & Lecture', 'Library & Playback'),
    33261: ('Langue audio et sous-titres par défaut (Kodi)',
            'Default audio & subtitle language (Kodi)'),
    33262: ('Réglages de bibliothèque/lecture vidéo (Kodi)',
            'Video library/playback settings (Kodi)'),
    33263: ('Apparence & Interface', 'Appearance & Interface'),
    33264: ("Langue de l'interface, région, écran de veille (Kodi)",
            'Interface language, region, screensaver (Kodi)'),
    33265: ('Habillage du skin (Kodi)', 'Skin settings (Kodi)'),
    33266: ('Overlay système, Mode Ambiant (Akasha)',
            'System overlay, Ambient Mode (Akasha)'),
    33267: ('Stockage', 'Storage'),
    33268: ('Sources et gestionnaire de fichiers (Kodi)',
            'Sources & file manager (Kodi)'),
    33269: ('Énergie', 'Power'),
    33270: ('Veille écran, extinction auto (Kodi)',
            'Screen idle, auto power-off (Kodi)'),
    33271: ('Délai veille/extinction, ventilateur (Akasha)',
            'Sleep/shutdown delay, fan (Akasha)'),
    33272: ('Système & Mises à jour', 'System & Updates'),
    33273: ('Nom système, sauvegarde, MAJ LibreELEC',
            'System name, backup, LibreELEC updates'),
    33274: ('Vérifier les mises à jour Akasha OS', 'Check for Akasha OS updates'),
    33275: ('Mises à jour et sources des extensions (Kodi)',
            'Addon updates & sources (Kodi)'),
    33276: ('Profils & Utilisateurs', 'Profiles & Users'),
    33277: ('Gérer les profils (Kodi)', 'Manage profiles (Kodi)'),
    33278: ('Tous les paramètres Kodi', 'All Kodi settings'),
    33279: ('Tous les paramètres LibreELEC', 'All LibreELEC settings'),

    # --- app / store -----------------------------------------------------
    33300: ('{} application(s) installée(s)', '{} app(s) installed'),
    33301: ('{} application(s) proposée(s)', '{} app(s) available'),
    33302: ('Installé', 'Installed'),
    33303: ('Non installé', 'Not installed'),
    33304: ('Catégorie : {}', 'Category: {}'),
    33305: ('Désinstaller {} ?', 'Uninstall {}?'),
    33306: ('{} est déjà installé. Le désinstaller ?',
            '{} is already installed. Uninstall it?'),
    33307: ('{} installé', '{} installed'),
    33308: ('{} retiré', '{} removed'),
    33309: ('{} enregistré', '{} registered'),
    33310: ('Installation non confirmée : {}', 'Install not confirmed: {}'),
    33311: ('Téléchargement échoué pour {}', 'Download failed for {}'),
    33312: ('Paquet vérifié pour {}', 'Package verified for {}'),
    33313: ('Vérification échouée pour {}', 'Verification failed for {}'),
    33314: ('Catalogue actualisé', 'Catalog refreshed'),
    33315: ('Voir les détails', 'View details'),
    33316: ('Aucune application épinglée — utilisez « Gérer les applications »',
            'No pinned app — use "Manage apps"'),
    33317: ('Applications épinglées', 'Pinned apps'),
    33318: ('Rafraîchir le catalogue', 'Refresh catalog'),
    33319: ('Applications', 'Applications'),
    33320: ('Gérer les applications', 'Manage apps'),
}

MONTH_ABBRS = {
    'fr': ('janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.',
           'août', 'sept.', 'oct.', 'nov.', 'déc.'),
    'en': ('Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.', 'Jul.',
           'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.'),
}

_addon = None


def tr(msgid):
    """Localized string for `msgid`; French fallback outside Kodi/tests."""
    global _addon
    if xbmcaddon is not None:
        try:
            if _addon is None:
                _addon = xbmcaddon.Addon()
            s = _addon.getLocalizedString(msgid)
            if s:
                return s
        except Exception:
            pass
    return STRINGS.get(msgid, ('', ''))[0]


def _lang():
    """'en' when Kodi resolves English, 'fr' otherwise (default)."""
    if xbmcaddon is None:
        return 'fr'
    return 'en' if tr(33001) == STRINGS[33001][1] else 'fr'


def fmt_air_date(iso_date):
    """'2025-10-19' -> '19 oct. 2025' (fr) / 'Oct 19, 2025' (en)."""
    if not iso_date:
        return ''
    try:
        year, month, day = iso_date[:10].split('-')
        day, month = int(day), int(month)
        abbr = MONTH_ABBRS[_lang()][month - 1]
    except (ValueError, IndexError):
        return ''
    if _lang() == 'en':
        return '{} {}, {}'.format(abbr, day, year)
    return '{} {} {}'.format(day, abbr, year)


def _esc(text):
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def _po_lines(language, index):
    yield 'msgid ""'
    yield 'msgstr ""'
    yield '"Project-Id-Version: script.akasha.aura\\n"'
    yield '"Content-Type: text/plain; charset=UTF-8\\n"'
    yield '"Language: {}\\n"'.format(language)
    yield ''
    for msgid in sorted(STRINGS):
        fr, en = STRINGS[msgid]
        # Kodi format: msgid = English source, msgstr = translation
        # (empty msgstr in en_gb means identity).
        translation = (fr, en)[index] if index else fr
        yield ''
        yield '# {}'.format(fr.replace('\n', ' '))
        yield 'msgctxt "#{}"'.format(msgid)
        yield 'msgid "{}"'.format(_esc(en))
        yield 'msgstr "{}"'.format('' if index == 1 else _esc(fr))
    yield ''


def _write_po(path, language):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    index = 0 if language == 'fr_fr' else 1
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(_po_lines(language, index)))


if __name__ == '__main__':
    import os.path
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'language')
    _write_po(os.path.join(base, 'resource.language.fr_fr', 'strings.po'),
              'fr_fr')
    _write_po(os.path.join(base, 'resource.language.en_gb', 'strings.po'),
              'en_gb')
    print('wrote', len(STRINGS), 'strings to', base)
