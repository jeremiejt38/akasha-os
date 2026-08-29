"""Akasha Voice -- pure command interpreter.

Maps French and English voice phrases to Kodi builtins. This module has no
xbmc* dependency so it can be unit-tested with plain python3 -m unittest.

Spec source: c8c8548a-akasha-os-commandes-vocales.md
"""
from __future__ import annotations


COMMANDS = (
    # Section 1 -- Navigation generale
    {'fr': ('ouvre divertissement',), 'en': ('open entertainment',), 'action': 'open_entertainment', 'builtin': 'RunScript(script.akasha.aura)'},
    {'fr': ('va dans jeux',), 'en': ('go to games',), 'action': 'open_games', 'builtin': 'RunScript(script.akasha.aura)'},
    {'fr': ('va dans apps', 'ouvre applications'), 'en': ('go to apps',), 'action': 'open_apps', 'builtin': 'RunScript(script.akasha.aura)'},
    {'fr': ('retour',), 'en': ('go back', 'back'), 'action': 'navigate_back', 'builtin': 'Action(Back)'},
    {'fr': ('accueil',), 'en': ('home',), 'action': 'navigate_home', 'builtin': 'RunScript(script.akasha.aura)'},
    {'fr': ('monte',), 'en': ('up',), 'action': 'move_up', 'builtin': 'Input.Up'},
    {'fr': ('descends',), 'en': ('down',), 'action': 'move_down', 'builtin': 'Input.Down'},
    {'fr': ('gauche',), 'en': ('left',), 'action': 'move_left', 'builtin': 'Input.Left'},
    {'fr': ('droite',), 'en': ('right',), 'action': 'move_right', 'builtin': 'Input.Right'},
    {'fr': ('sélectionne', 'selectionne'), 'en': ('select', 'ok'), 'action': 'select_item', 'builtin': 'Input.Select'},
    {'fr': ('ouvre les paramètres', 'ouvre les parametres'), 'en': ('open settings',), 'action': 'open_settings', 'builtin': 'RunScript(script.akasha.aura,opensettings)'},
    {'fr': ('affiche le menu',), 'en': ('show menu',), 'action': 'show_menu', 'builtin': 'Action(ContextMenu)'},
    {'fr': ("recharge l'interface", 'recharge l interface'), 'en': ('reload interface',), 'action': 'reload_interface', 'builtin': 'ReloadSkin()'},
    {'fr': ('affiche mes bibliothèques', 'affiche mes bibliotheques'), 'en': ('show my libraries',), 'action': 'show_libraries', 'builtin': 'RunScript(script.akasha.aura,divert=library)'},
    {'fr': ('affiche les genres',), 'en': ('show genres',), 'action': 'show_genres', 'builtin': 'RunScript(script.akasha.aura,divert=genres)'},

    # Section 2 -- Lecture media / controle transport
    {'fr': ('lecture',), 'en': ('play',), 'action': 'play', 'builtin': 'PlayerControl(Play)'},
    {'fr': ('pause',), 'en': ('pause',), 'action': 'pause', 'builtin': 'PlayerControl(Pause)'},
    {'fr': ('stop',), 'en': ('stop',), 'action': 'stop', 'builtin': 'Stop'},
    {'fr': ('suivant',), 'en': ('next',), 'action': 'next', 'builtin': 'PlayerControl(Next)'},
    {'fr': ('précédent', 'precedent'), 'en': ('previous',), 'action': 'previous', 'builtin': 'PlayerControl(Previous)'},
    {'fr': ('avance de 30 secondes',), 'en': ('skip forward 30 seconds',), 'action': 'seek_forward_30', 'builtin': 'Seek(30)'},
    {'fr': ('recule de 10 secondes',), 'en': ('skip back 10 seconds',), 'action': 'seek_back_10', 'builtin': 'Seek(-10)'},
    {'fr': ('va à la scène suivante',), 'en': ('go to next chapter',), 'action': 'next_chapter', 'builtin': 'Action(NextScene)'},
    {'fr': ("reprends où j'en étais",), 'en': ('resume playback',), 'action': 'resume_playback', 'builtin': 'PlayerControl(Play)'},
    {'fr': ('recommence depuis le début',), 'en': ('restart from the beginning',), 'action': 'restart_from_beginning', 'builtin': 'PlayerControl(SeekPercentage(0))'},
    {'fr': ('active les sous-titres',), 'en': ('enable subtitles',), 'action': 'enable_subtitles', 'builtin': 'Action(ShowSubtitles)'},
    {'fr': ('désactive les sous-titres',), 'en': ('disable subtitles',), 'action': 'disable_subtitles', 'builtin': 'Action(ShowSubtitles)'},
    {'fr': ('sous-titres en français',), 'en': ('subtitles in french',), 'action': 'french_subtitles', 'builtin': 'Noop'},
    {'fr': ('piste audio originale',), 'en': ('original audio track',), 'action': 'original_audio', 'builtin': 'Action(AudioNextLanguage)'},
    {'fr': ('ralenti',), 'en': ('slow motion',), 'action': 'slow_motion', 'builtin': 'PlayerControl(TempoDown)'},
    {'fr': ('vitesse normale',), 'en': ('normal speed',), 'action': 'normal_speed', 'builtin': 'PlayerControl(Play)'},
    {'fr': ('plein écran',), 'en': ('fullscreen',), 'action': 'fullscreen', 'builtin': 'Action(FullScreen)'},

    # Section 3 -- Volume / affichage
    {'fr': ('monte le son',), 'en': ('volume up',), 'action': 'volume_up', 'builtin': 'Action(VolumeUp)'},
    {'fr': ('baisse le son',), 'en': ('volume down',), 'action': 'volume_down', 'builtin': 'Action(VolumeDown)'},
    {'fr': ('coupe le son',), 'en': ('mute',), 'action': 'mute', 'builtin': 'Mute'},
    {'fr': ('remets le son',), 'en': ('unmute',), 'action': 'unmute', 'builtin': 'Mute'},
    {'fr': ('éteins la tv',), 'en': ('turn off the tv',), 'action': 'tv_off', 'builtin': 'Noop'},
    {'fr': ('allume la tv',), 'en': ('turn on the tv',), 'action': 'tv_on', 'builtin': 'Noop'},
    {'fr': ('change de source hdmi',), 'en': ('switch hdmi source',), 'action': 'switch_hdmi', 'builtin': 'Noop'},
    {'fr': ('passe en hdr',), 'en': ('switch to hdr',), 'action': 'switch_hdr', 'builtin': 'Noop'},
    {'fr': ('résolution 4k',), 'en': ('switch to 4k resolution',), 'action': 'switch_4k', 'builtin': 'Noop'},

    # Section 4 -- Recherche et decouverte de contenu
    {'fr': ('cherche {title}',), 'en': ('search for {title}',), 'action': 'search_title', 'builtin': 'ActivateWindow(Videos,search://{title})'},
    {'fr': ('lance {title}',), 'en': ('play {title}',), 'action': 'play_title', 'builtin': 'PlayMedia({title})'},
    {'fr': ('continue à regarder',), 'en': ('continue watching',), 'action': 'continue_watching', 'builtin': 'RunScript(script.akasha.aura,divert=continue_watching)'},
    {'fr': ('quoi de neuf sur plex ?',), 'en': ("what's new on plex?",), 'action': 'plex_recent', 'builtin': 'RunScript(script.akasha.aura,divert=recent)'},
    {'fr': ('recommandations',), 'en': ('recommendations',), 'action': 'recommendations', 'builtin': 'RunScript(script.akasha.aura,divert=recommendations)'},
    {'fr': ('films récemment ajoutés',), 'en': ('recently added movies',), 'action': 'recent_movies', 'builtin': 'ActivateWindow(Videos,videodb://movies/recentlyadded/)'},
    {'fr': ("cherche des films d'action",), 'en': ('search for action movies',), 'action': 'action_movies', 'builtin': 'ActivateWindow(Videos,videodb://movies/genres/Action/)'},
    {'fr': ('lance un épisode aléatoire',), 'en': ('play a random episode',), 'action': 'random_episode', 'builtin': 'PlayerControl(RandomOn)'},
    {'fr': ('montre-moi les films non vus',), 'en': ('show unwatched movies',), 'action': 'unwatched_movies', 'builtin': 'ActivateWindow(Videos,videodb://movies/titles/?xsp={"rules":{"field":"playcount","operator":"is","value":"0"}})'},
    {'fr': ('ajoute {title} à ma liste',), 'en': ('add {title} to my watchlist',), 'action': 'add_watchlist', 'builtin': 'Noop'},

    # Section 5 -- Musique
    {'fr': ('joue de la musique',), 'en': ('play music',), 'action': 'play_music', 'builtin': 'PlayMedia(musicdb://songs/)'},
    {'fr': ('lance ma playlist {playlist}',), 'en': ('play my {playlist} playlist',), 'action': 'play_playlist', 'builtin': 'PlayMedia(special://profile/playlists/music/{playlist}.m3u)'},
    {'fr': ('joue {artist}',), 'en': ('play {artist}',), 'action': 'play_artist', 'builtin': 'PlayMedia(musicdb://artists/{artist}/)'},
    {'fr': ('musique aléatoire',), 'en': ('random music', 'shuffle music'), 'action': 'shuffle_music', 'builtin': 'PlayerControl(RandomOn)'},
    {'fr': ('chanson suivante',), 'en': ('next song',), 'action': 'next_song', 'builtin': 'PlayerControl(Next)'},
    {'fr': ('quelle chanson est en cours ?',), 'en': ('what song is this?',), 'action': 'current_song_info', 'builtin': 'Action(Info)'},
    {'fr': ('ajoute cette chanson à mes favoris',), 'en': ('add this song to my favorites',), 'action': 'favorite_song', 'builtin': 'Noop'},

    # Section 6 -- Cloud gaming
    {'fr': ('lance steam link',), 'en': ('launch steam link',), 'action': 'launch_steam_link', 'builtin': 'RunAddon(script.steamlink)'},
    {'fr': ('ouvre moonlight',), 'en': ('open moonlight',), 'action': 'launch_moonlight', 'builtin': 'RunAddon(script.moonlight)'},
    {'fr': ('lance geforce now',), 'en': ('launch geforce now',), 'action': 'launch_geforce_now', 'builtin': 'RunScript(script.akasha.aura,gaming=geforce_now)'},
    {'fr': ('ouvre xbox cloud gaming',), 'en': ('open xbox cloud gaming',), 'action': 'launch_xbox_cloud', 'builtin': 'RunScript(script.akasha.aura,gaming=xbox_cloud)'},
    {'fr': ('lance boosteroid',), 'en': ('launch boosteroid',), 'action': 'launch_boosteroid', 'builtin': 'RunScript(script.akasha.aura,gaming=boosteroid)'},
    {'fr': ('reprends ma partie',), 'en': ('resume my game',), 'action': 'resume_game', 'builtin': 'RunScript(script.akasha.aura,gaming=resume)'},
    {'fr': ('quitte le jeu',), 'en': ('quit the game',), 'action': 'quit_game', 'builtin': 'RunScript(script.akasha.aura,gaming=quit)'},
    {'fr': ('vérifie ma connexion réseau',), 'en': ('check my network connection',), 'action': 'network_check', 'builtin': 'Noop'},

    # Section 7 -- Energie / systeme
    {'fr': ('mets en veille',), 'en': ('go to sleep', 'standby'), 'action': 'standby', 'builtin': 'Suspend'},
    {'fr': ('éteins akasha', 'eteins akasha'), 'en': ('shut down akasha',), 'action': 'shutdown', 'builtin': 'Powerdown'},
    {'fr': ('redémarre',), 'en': ('restart',), 'action': 'restart', 'builtin': 'Reboot'},
    {'fr': ('statut du système',), 'en': ('system status',), 'action': 'system_status', 'builtin': 'Noop'},
    {'fr': ('vérifie les mises à jour',), 'en': ('check for updates',), 'action': 'check_updates', 'builtin': 'Noop'},

    # Section 8 -- Multi-utilisateur
    {'fr': ("change d'utilisateur",), 'en': ('switch user',), 'action': 'switch_user', 'builtin': 'ActivateWindow(LoginScreen)'},
    {'fr': ('connecte-toi en tant que {user}',), 'en': ('log in as {user}',), 'action': 'login_user', 'builtin': 'Noop'},
)


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation for matching."""
    text = text.lower()
    for char in "'!?:;.,-":
        text = text.replace(char, ' ')
    return ' '.join(text.split())


def _pattern_prefix(pattern: str) -> str | None:
    """Return fixed prefix before the first {slot}, or the whole pattern."""
    if '{' not in pattern:
        return _normalize(pattern)
    prefix = pattern.split('{', 1)[0].strip()
    return _normalize(prefix)


def _extract_slot(phrase: str, pattern: str) -> str:
    """Extract the variable part of a phrase following a slotted pattern."""
    prefix = _pattern_prefix(pattern)
    norm = _normalize(phrase)
    if not norm.startswith(prefix):
        return ''
    value = norm[len(prefix):].strip()
    return value


def _best_match(phrase: str, patterns: tuple[str, ...]) -> tuple[int, str | None]:
    """Return (score, matched_pattern) for the patterns against a phrase."""
    best_score = 0
    best_pattern = None
    for pattern in patterns:
        prefix = _pattern_prefix(pattern)
        if not prefix:
            continue
        if '{' in pattern:
            if _normalize(phrase).startswith(prefix):
                # Slotted patterns: prefer longer prefix to avoid ambiguities.
                score = len(prefix.split()) + 1
                if score > best_score:
                    best_score = score
                    best_pattern = pattern
        else:
            if prefix in _normalize(phrase):
                score = len(prefix.split())
                if score > best_score:
                    best_score = score
                    best_pattern = pattern
    return best_score, best_pattern


def handle(phrase: str, lang: str = 'fr') -> str | None:
    """Return the Kodi builtin for a given voice phrase, or None."""
    if not phrase:
        return None
    best_cmd = None
    best_score = 0
    best_pattern = None
    for command in COMMANDS:
        patterns = command.get(lang) or command['fr']
        score, matched = _best_match(phrase, patterns)
        if score > best_score:
            best_score = score
            best_cmd = command
            best_pattern = matched
    if not best_cmd or best_score == 0:
        return None
    builtin = best_cmd['builtin']
    if best_pattern and '{' in best_pattern:
        # Fill the slot value into the builtin string.
        value = _extract_slot(phrase, best_pattern)
        slot_name = best_pattern[best_pattern.find('{') + 1:best_pattern.find('}')]
        builtin = builtin.replace('{' + slot_name + '}', value)
    return builtin
