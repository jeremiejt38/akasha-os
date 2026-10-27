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

import os

try:
    import xbmc
except ImportError:
    xbmc = None
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
    33106: ('Reprendre • {} restantes', 'Resume • {} left'),
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
    33155: ('Ouvrir', 'Open'),
    33156: ('Reprendre', 'Resume'),
    33157: ('Mise en veille', 'Sleep'),
    33158: ('Arrêter le système', 'Shut down the system'),
    33159: ('Films et séries', 'Movies & Shows'),
    33160: ('Sortie', 'Release'),
    33161: ('Retirer de Continuer à regarder',
            'Remove from Continue Watching'),
    33146: ('Retiré de Continuer à regarder',
            'Removed from Continue Watching'),
    33144: ('Installer', 'Install'),
    33145: ('Tous publics', 'All audiences'),

    # Discover/provider hub titles (Plex "Tendances" rows)
    33185: ('Nouvelles bandes-annonces', 'New trailers'),
    33186: ('Bandes-annonces en vogue', 'Trending trailers'),
    33187: ('Recommandé sur vos services', 'Recommended on your services'),
    33188: ('Les plus suivis cette semaine', 'Most watchlisted this week'),
    33189: ('Bandes-annonces de votre Watchlist', 'Trailers from your Watchlist'),
    33190: ('Disponibles sur vos services', 'Available on your services'),
    33191: ('Bientôt disponible', 'Coming soon'),
    33192: ('Disponibles à la location', 'Available to rent'),
    33193: ('Parcourir par genre', 'Browse by genre'),
    33194: ("Cette semaine dans l'histoire", 'This week in history'),
    33195: ('Blockbusters à venir', 'Upcoming blockbusters'),
    33196: ('Vos services', 'Your services'),
    33180: ('Chargement…', 'Loading…'),

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

    # --- unified settings panel (plan b81d3f6a) --------------------------
    33401: ('État du réseau', 'Network status'),
    33402: ('Adresse IP', 'IP address'),
    33403: ('Wi-Fi', 'Wi-Fi'),
    33404: ('Activer ou désactiver la carte Wi-Fi',
            'Turn the Wi-Fi adapter on or off'),
    33405: ('Réseaux Wi-Fi et connexions…', 'Wi-Fi networks & connections…'),
    33406: ('Liste des réseaux, mot de passe, IP statique (LibreELEC)',
            'Network list, password, static IP (LibreELEC)'),
    33410: ('Résolution', 'Resolution'),
    33411: ('Résolution et fréquence de sortie vidéo',
            'Video output resolution and rate'),
    33412: ("Adapter la fréquence au contenu", 'Match content frame rate'),
    33413: ("Bascule la fréquence de la TV pendant la lecture",
            'Switches the TV rate during playback'),
    33414: ('Sortie audio', 'Audio output'),
    33415: ('Périphérique de sortie du son', 'Sound output device'),
    33416: ('Configuration des canaux', 'Channel configuration'),
    33417: ('Nombre de canaux annoncé au récepteur',
            'Channel count reported to the receiver'),
    33418: ('Passthrough', 'Passthrough'),
    33419: ('Envoie le son brut à la TV/ampli (AC3, DTS…)',
            'Sends raw audio to the TV/receiver (AC3, DTS…)'),
    33420: ('Passthrough AC3', 'AC3 passthrough'),
    33421: ('Passthrough DTS', 'DTS passthrough'),
    33422: ("Calibration de l'écran", 'Screen calibration'),
    33423: ('Ajuster les bords et le rapport de pixel',
            'Adjust edges and pixel ratio'),
    33430: ('Plex', 'Plex'),
    33431: ('Compte et bibliothèque Plex', 'Plex account and library'),
    33432: ('Jellyfin', 'Jellyfin'),
    33433: ('YouTube Music', 'YouTube Music'),
    33434: ('URL du serveur Plex', 'Plex server URL'),
    33435: ('Token Plex (X-Plex-Token)', 'Plex token (X-Plex-Token)'),
    33436: ('Clé API Steam', 'Steam API key'),
    33437: ('SteamID64', 'SteamID64'),
    33438: ('URL du serveur Sunshine', 'Sunshine server URL'),
    33439: ('Utilisateur Sunshine', 'Sunshine username'),
    33440: ('Mot de passe Sunshine', 'Sunshine password'),
    33450: ('Appareils Bluetooth', 'Bluetooth devices'),
    33451: ('Appareils appairés : connecter ou oublier',
            'Paired devices: connect or forget'),
    33452: ('Appairer un appareil…', 'Pair a device…'),
    33453: ('Recherche et appairage Bluetooth (LibreELEC)',
            'Bluetooth discovery and pairing (LibreELEC)'),
    33454: ('Télécommande Akasha', 'Akasha remote'),
    33460: ("Langue audio préférée", 'Preferred audio language'),
    33461: ('Langue choisie en priorité à la lecture',
            'Language picked first during playback'),
    33462: ('Langue des sous-titres', 'Subtitle language'),
    33463: ('Langue de sous-titres préférée',
            'Preferred subtitle language'),
    33464: ('Réglages de lecture avancés…', 'Advanced playback settings…'),
    33470: ("Langue de l'interface", 'Interface language'),
    33471: ("Langue des menus d'Akasha OS", 'Akasha OS menu language'),
    33472: ('Région', 'Region'),
    33473: ('Format de date', 'Date format'),
    33474: ("Format de l'heure", 'Time format'),
    33475: ('Pays du fuseau horaire', 'Time zone country'),
    33476: ('Fuseau horaire', 'Time zone'),
    33477: ("Délai de l'écran de veille", 'Screensaver delay'),
    33478: ("Minutes d'inactivité avant l'écran de veille",
            'Idle minutes before the screensaver'),
    33479: ('Mode Ambiant', 'Ambient Mode'),
    33480: ('Écran de veille photo Akasha en veille',
            'Akasha photo screensaver when idle'),
    33481: ('Overlay système', 'System overlay'),
    33490: ("Extinction de l'écran", 'Screen power-off'),
    33491: ("Délai avant mise en veille de l'écran",
            'Delay before the screen sleeps'),
    33492: ('Arrêt automatique', 'Auto shutdown'),
    33493: ('Délai avant arrêt du système', 'Delay before system shutdown'),
    33494: ("Mode d'extinction", 'Shutdown behaviour'),
    33500: ('Nom du système', 'System name'),
    33501: ('Version Akasha OS', 'Akasha OS version'),
    33502: ('Version LibreELEC', 'LibreELEC version'),
    33503: ('Température CPU', 'CPU temperature'),
    33504: ('Mémoire disponible', 'Available memory'),
    33505: ('Mises à jour des extensions', 'Addon updates'),
    33506: ('Mode de mise à jour des extensions Kodi',
            'How Kodi addons are updated'),
    33507: ('Sources inconnues', 'Unknown sources'),
    33508: ("Autoriser l'installation d'extensions hors store",
            'Allow installing addons outside the store'),
    33509: ('Mises à jour Akasha OS…', 'Akasha OS updates…'),
    33510: ('Sauvegarde et restauration…', 'Backup & restore…'),
    33511: ('Sauvegarde du système (LibreELEC)',
            'System backup (LibreELEC)'),
    33520: ('Gestionnaire de fichiers', 'File manager'),
    33530: ('Activé', 'On'),
    33531: ('Désactivé', 'Off'),
    33532: ('Connecté : {}', 'Connected: {}'),
    33533: ('Non configuré', 'Not configured'),
    33534: ('Connecté', 'Connected'),
    33535: ('Déconnecté', 'Disconnected'),
    33536: ('Connecter', 'Connect'),
    33537: ('Déconnecter', 'Disconnect'),
    33538: ('Oublier', 'Forget'),
    33539: ('{} appareil(s) appairé(s)', '{} paired device(s)'),
    33540: ('Aucun appareil appairé', 'No paired device'),
    33541: ('{} °C', '{} °C'),
    33542: ('{} Mo', '{} MB'),
    33543: ('Jamais', 'Never'),
    33544: ('{} min', '{} min'),
    33545: ('Non connecté', 'Not connected'),
    33546: ('Valeur inchangée', 'Value unchanged'),
    33547: ("Échec de l'enregistrement", 'Failed to save'),
    33548: ('Ethernet', 'Ethernet'),
    33549: ('Masqué', 'Hidden'),

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
    33321: ('Application web', 'Web app'),
    33322: ('Web', 'Web'),
    33323: ('Version : {}', 'Version: {}'),
    33324: ("Type d'installation : {}", 'Install type: {}'),
    33325: ('Source : {}', 'Source: {}'),
    33326: ('Lien profond : {}', 'Deep link: {}'),
    33327: ('Se connecter (Connector Akasha OS)',
            'Sign in (Akasha OS Connector)'),
    33328: ('Sans titre', 'Untitled'),

    # --- divertissement state view (B17): offline / error / empty ---------
    33550: ('Serveur inaccessible', 'Server unreachable'),
    33551: ('Vérifiez que votre serveur est allumé et connecté au réseau.',
            'Check that your server is powered on and connected to the network.'),
    33552: ('Réessayer', 'Retry'),
    33553: ('Impossible de charger le contenu', 'Unable to load content'),
    33554: ('Une erreur est survenue. Réessayez dans un instant.',
            'Something went wrong. Try again in a moment.'),
    33555: ('Votre bibliothèque est vide', 'Your library is empty'),
    33556: ('Aucun résultat', 'No results'),
    33557: ('Effacer les filtres', 'Clear filters'),
    33558: ('Plex n’est pas configuré', 'Plex is not configured'),
    33559: ('Renseignez le serveur et le jeton Plex dans les réglages.',
            'Set the Plex server and token in Settings.'),
    33560: ('Aucun contenu à afficher', 'Nothing to show'),

    # --- up next card (B1): post-play chaining between episodes -----------
    33561: ('À suivre', 'Up Next'),
    33562: ('Lecture dans {} s', 'Playing in {} s'),
    33563: ('Lire maintenant', 'Play now'),
    33564: ('Annuler', 'Cancel'),

    # --- OSD chapters list (B14) ------------------------------------------
    33565: ('Chapitres', 'Chapters'),
    33566: ('Chapitre {}', 'Chapter {}'),
    33567: ('Aucun chapitre', 'No chapters'),

    # --- Skip Intro / Skip Credits chip (B2) ------------------------------
    33568: ("Passer l'intro", 'Skip Intro'),
    33569: ('Passer le générique', 'Skip Credits'),
    33570: ('Passer', 'Skip'),

    # --- Dynamic library filters (B4) --------------------------------------
    33571: ('Filtres avancés…', 'Advanced filters…'),
    33572: ('Aucun filtre disponible', 'No filters available'),
    33573: ('Filtrer par {}', 'Filter by {}'),

    # --- More Like This (B7) -----------------------------------------------
    33574: ('Titres similaires', 'Similar Titles'),
    33575: ('Aucun titre similaire', 'No similar titles'),

    # --- Own watch history (B6) --------------------------------------------
    33576: ('Activité', 'Activity'),
    33577: ('Votre activité', 'Your activity'),
    33578: ("Vous l'avez regardé le {}", 'You watched it on {}'),

    # --- Go to Show from an episode (B11) ----------------------------------
    33579: ('Aller à la série', 'Go to Show'),

    # --- Enriched search (B8) ----------------------------------------------
    33580: ("Effacer l'historique", 'Clear history'),
    33581: ('Genre', 'Genre'),

    # --- Server playlists (B10) --------------------------------------------
    33582: ('Playlists', 'Playlists'),

    # --- Version picker (B12) ----------------------------------------------
    33583: ('Lire la version…', 'Play Version'),

    # --- Search Popular Searches heading ------------------------------------
    33584: ('Recherches populaires', 'Popular Searches'),

    # Plex-style OSD meta duration ("43 minutes", "1 h 15 min")
    33585: ('minutes', 'minutes'),

    # Plex search hint line above Popular Searches
    33586: ('Titres, personnes, genres et plus encore…',
            'Search titles, people, genres and more…'),

    # Dark confirm / message sheets (aura_menu.confirm / .message)
    33587: ('Confirmer', 'Confirm'),
    33588: ('OK', 'OK'),
    33589: ('Bandes-annonces et bonus', 'Trailers & Extras'),

    # Sidebar "My Lists" row (Plex parity -- lists the server playlists)
    33590: ('Mes listes', 'My Lists'),
    33591: ('Aucune liste', 'No lists yet'),
}

MONTH_ABBRS = {
    'fr': ('janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.',
           'août', 'sept.', 'oct.', 'nov.', 'déc.'),
    'en': ('Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.', 'Jul.',
           'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.'),
}

_addon = None

# msgid -> (fr singular, fr plural, en singular, en plural) for 'N noun'
# labels Plex renders with proper agreement ('3 saisons', not '(s)').
_PLURALS = {
    33069: ('{} élément', '{} éléments', '{} item', '{} items'),
    33128: ('{} saison', '{} saisons', '{} season', '{} seasons'),
    33129: ('{} épisode', '{} épisodes', '{} episode', '{} episodes'),
}


def tr_count(count, msgid):
    """Localized 'count noun' with proper singular/plural agreement.
    French pluralizes only above 1; English pluralizes everything != 1."""
    fr_one, fr_many, en_one, en_many = _PLURALS[msgid]
    if _lang() == 'en':
        return (en_one if count == 1 else en_many).format(count)
    return (fr_one if count <= 1 else fr_many).format(count)


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


_MEASURE_FONTS = {}


def _measure_font(size):
    """PIL font matching the skin's Inter faces for text-width checks."""
    if size in _MEASURE_FONTS:
        return _MEASURE_FONTS[size]
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    candidates = []
    try:
        if xbmc is not None:
            candidates.append(os.path.join(
                xbmc.translatePath('special://skin/fonts'),
                'Inter-Unicode-Regular.ttf'))
    except Exception:
        pass
    try:
        if xbmcaddon is not None:
            candidates.append(os.path.join(
                xbmcaddon.Addon('skin.arctic.horizon.2').getAddonInfo('path'),
                'fonts', 'Inter-Unicode-Regular.ttf'))
    except Exception:
        pass
    for path in candidates:
        if os.path.exists(path):
            _MEASURE_FONTS[size] = ImageFont.truetype(path, size)
            return _MEASURE_FONTS[size]
    return None


def text_width(text, size):
    """Rendered pixel width of `text` in the skin's Inter face at `size`
    -- or None when PIL/the TTF is unavailable (tests, stripped builds)."""
    if not text:
        return 0
    try:
        font = _measure_font(size)
        return font.getbbox(text)[2] if font else None
    except Exception:
        return None


def ellipsize(text, size, budget_px=190):
    """Trim `text` to fit a card caption with a true '…' ellipsis, like
    Plex -- Kodi's own truncation appends '...' plus a stray space.
    Kodi renders Inter ~1.2x wider than PIL, so the PIL budget is 190px
    for a 240px label. Returns the input untouched when measuring fails.
    """
    if not text:
        return text
    try:
        font = _measure_font(size)
        if font is None or font.getbbox(text)[2] <= budget_px:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.getbbox(text[:mid] + '…')[2] <= budget_px:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + '…'
    except Exception:
        return text


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


# Shipped languages, in STRINGS tuple order: (french, english, ...).
# Adding a language = append its resource.language.<code> name here and
# grow every STRINGS tuple with one more entry -- the generator below
# then emits resources/language/<code>/strings.po automatically.
LANGUAGES = ('fr_fr', 'en_gb')


def _write_po(path, language, index):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(_po_lines(language, index)))


if __name__ == '__main__':
    import os.path
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'language')
    for index, language in enumerate(LANGUAGES):
        _write_po(os.path.join(
            base, 'resource.language.{}'.format(language), 'strings.po'),
            language, index)
    print('wrote', len(STRINGS), 'strings to', base)
