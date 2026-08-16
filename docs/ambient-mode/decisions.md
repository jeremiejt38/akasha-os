# Mode Ambiant — Décisions techniques

## Historique : screensaver natif abandonné après test réel (bug Kodi)

**Choix initial** : `screensaver.akasha.ambient`, extension `xbmc.ui.screensaver`, en s'appuyant
sur la détection d'inactivité native de Kodi (`screensaver.time`).

**Constat en conditions réelles** : quel que soit le contenu du script (boucle directe dans
`onInit()`, thread séparé, `xbmc.sleep()` ou `Monitor.waitForAbort()`, avec ou sans `multiimage`),
Kodi tuait systématiquement le script Python ~20 secondes après son activation :

```
CPythonInvoker(N, .../screensaver.akasha.ambient/default.py): script didn't stop in 5 seconds - let's kill it
```

Ce comportement est documenté de longue date dans la communauté Kodi (voir un fil du forum Kodi sur
`screensaver.xbmc.slideshow` décrivant exactement le même symptôme dès XBMC v12) : les screensavers
Python peuvent devenir des fenêtres "zombies" — gelées à l'écran, ne répondant plus à aucune entrée
— après avoir été tués par ce watchdog. Ce n'est pas un bug introduit par ce code.

**Pivot retenu** : abandon de l'extension `xbmc.ui.screensaver`. Le Mode Ambiant est désormais deux
addons :
- `script.akasha.ambient` : une fenêtre `xbmcgui.WindowXMLDialog` ouverte via `RunScript`, exactement
  le même patron que `GuideWindow` (`kodi/scripts/akasha-guide.py`), qui fonctionne de façon fiable
  en production sur ce projet. Elle se ferme sur n'importe quelle entrée (`onAction`).
- `service.akasha.ambient` : un service (`xbmc.service`) qui surveille lui-même
  `xbmc.getGlobalIdleTime()` et déclenche `RunScript(script.akasha.ambient)` une fois le délai
  configuré atteint — le rôle que jouerait normalement le screensaver natif de Kodi, mais sans
  passer par son mécanisme interne (donc sans le watchdog qui pose problème).

Testé en conditions réelles : la fenêtre déclenchée manuellement reste active sans limite de temps,
répond immédiatement à toute entrée, et le transfert vers `akasha-sleep.py` (veille CEC) fonctionne.

## Fausse alerte initiale : "l'inactivité n'est jamais détectée"

Pendant les tests initiaux, `xbmc.getGlobalIdleTime()` semblait rester bloqué à `0` en continu
(vérifié y compris après un reboot complet, via `xbmc.getGlobalIdleTime()` et l'API JSON-RPC
indépendante `System.IdleTime(N)`). Investigation matérielle (moniteur `evdev` sur les 6
périphériques d'entrée, moniteur du bus CEC via `cec-ctl --monitor`) : **aucun** trafic d'entrée
réel pendant ces fenêtres de test, donc ce n'était pas un flux d'entrée physique parasite.

**Root cause réelle : méthodologie de test, pas un bug.** Le rythme des tests (redémarrages
`systemctl restart kodi` très rapprochés, appels `kodi-send`/JSON-RPC en continu pour observer
l'état via PixelCamera) ne laissait jamais un intervalle réellement calme de plusieurs minutes.
Chaque redémarrage de Kodi relance aussi une resynchronisation Jellyfin (websocket, scan
bibliothèque), visible dans les logs pendant 1-2 minutes après chaque démarrage. En laissant
l'appareil réellement inactif (aucun test en cours) pendant la durée complète du délai configuré
(5 minutes par défaut), `service.akasha.ambient` a déclenché `script.akasha.ambient` correctement :

```
Akasha Ambient Trigger: idle for 302s, activating Ambient Mode
```

La fenêtre est ensuite restée active et stable plus de 10 minutes (fichier de verrou rafraîchi en
continu, aucune erreur), confirmant que le déclenchement automatique par inactivité fonctionne
comme prévu. Leçon retenue : pour tester une fonctionnalité liée à l'inactivité, laisser
l'appareil réellement tranquille pendant toute la durée du délai, sans requêtes JSON-RPC/`kodi-send`
qui pourraient elles-mêmes fausser l'observation (même si elles ne réinitialisent pas le
compteur, elles empêchent de distinguer un vrai calme d'un calme interrompu par le test lui-même).

## Rotation d'images via le contrôle natif `multiimage`

**Choix** : le fond du Mode Ambiant est un contrôle skin `<control type="multiimage">` pointant
vers le dossier configuré, avec fondu enchaîné et ordre aléatoire natifs.

**Alternative écartée** : une classe `ContentManager` Python qui construirait elle-même la playlist
et appellerait `setImage()` sur un timer.

**Raison** : `multiimage` fait déjà tout ce dont le MVP a besoin (rotation, anti-répétition
immédiate, fondu) sans code Python, ce qui réduit la surface de bug sur un composant visible en
continu. Un `ContentManager` Python reste utile pour la logique testable indépendamment du skin
(validation de dossier, repli sur le contenu de secours) : voir `resources/lib/content_manager.py`.

## Pack de photos par défaut téléchargé (NASA EPIC)

**Choix** : `install.sh` appelle `kodi/scripts/ambient-download-photos.py` qui récupère un pack
public d'images de la Terre depuis l'API [NASA EPIC](https://epic.gsfc.nasa.gov/) et les stocke dans
`/storage/ambient/photos`. Les images EPIC sont produites par la NASA/NOAA et sont dans le domaine
public.

**Raison** : cela donne au Mode Ambiant un contenu par défaut immédiatement utilisable (paysages
terrestres vus de l'espace) sans pour autant embarquer d'assets binaires tiers dans le dépôt Git.
Le téléchargement n'est pas fatal : si le réseau est indisponible, l'addon retombe sur son dossier
`resources/media/fallback/`.

**Alternative écartée** : pack CC0/Wikimedia/placeholders. Écartée parce que les API sans clé sont
souvent à URLs dynamiques ou rate-limitées, et que Wikimedia exige une vérification de licence
image par image. NASA EPIC fournit des URLs stables, des métadonnées JSON propres et un statut de
domaine public clair.

## Horloge sans code Python

**Choix** : labels skin utilisant les info-labels natifs `$INFO[System.Time]` / `$INFO[System.Date]`.

**Raison** : Kodi les fournit déjà formatés et localisés ; un module `ClockProvider` séparé n'aurait
aucune valeur ajoutée pour la v0.12.

## Météo Open-Meteo, pas de vraie détection de luminosité matérielle

**Choix** : client HTTP minimal (stdlib `urllib`, pas de dépendance externe) vers Open-Meteo, cache
JSON local, ville configurée manuellement (pas de géolocalisation automatique).

**Raison** : pas de clé API à gérer/protéger, cohérent avec l'esprit "pas de dépendance cloud" de la
spec d'origine. La géolocalisation automatique est reportée (complexité et confidentialité) au
profit d'une ville saisie manuellement, comme le recommande explicitly la spec elle-même
(section 12.2).

## Assombrissement simulé, pas de contrôle de rétroéclairage matériel

**Choix** : calque noir semi-transparent (`colordiffuse` piloté par une propriété de fenêtre).

**Raison** : Akasha OS pilote un Raspberry Pi connecté en HDMI à une TV externe ; il n'existe pas de
rétroéclairage local à contrôler (contrairement à un écran de tablette/laptop). Le seul contrôle
d'énergie réel disponible côté TV est CEC (marche/veille), déjà couvert par `akasha-sleep.py`.

## Anti-marquage par presets de position (réutilise le patron `Guide.xml`)

**Choix** : le bloc horloge/météo bascule entre 4 presets de coin toutes les 10 minutes, via
`Window.Property` + groupes conditionnels dans le skin — même mécanisme que
`AkashaGuidePreset` dans `Guide.xml`.

**Alternative écartée** : décalage pixel-par-pixel dynamique via des valeurs numériques calculées en
Python et injectées dans les coordonnées du skin.

**Raison** : les balises de position (`<left>`, `<top>`) de Kodi n'évaluent pas de manière fiable des
info-labels numériques dynamiques à chaque frame ; un système de presets discrets, déjà utilisé et
validé dans ce projet, est plus robuste et suffisant pour l'objectif anti-marquage.

## Vidéos d'ambiance en boucle : `xbmc.Player` plein écran

**Choix** : quand le dossier de contenu contient des vidéos, `content_manager.resolve_media()`
retourne `media_type='videos'` et une liste de chemins. `AmbientWindow` démarre un `xbmc.PlayList`
et appelle `xbmc.Player().play(..., windowed=False)`. Un thread surveille `isPlaying()` et ferme
la fenêtre dès que l'utilisateur appuie sur `Back`/`Stop` (ce qui arrête le player plein écran).

**Pourquoi le plein écran et non un `videowindow` intégré** : dans nos tests réels sur
LibreELEC/Kodi 21, `xbmc.Player().play(..., windowed=True)` n'affichait pas correctement la vidéo
soit derrière le dialog (`WindowXMLDialog`), soit sans jamais relâcher le focus, ce qui empêchait
`Back` de fermer le Mode Ambiant. Le player plein écran natif est stable et permet la boucle / le
`RepeatAll` fiable.

**Limitation connue** : pendant une vidéo, l'horloge et la météo ne sont pas affichées (ce n'est pas
un `videowindow` intégré). Le `multiimage` est simplement masqué pour éviter qu'une image ne
recouvre le player.

**Raison** : cela réutilise le player vidéo natif de Kodi (décodage matériel, boucle de playlist)
sans réécrire de lecteur. L'utilisateur peut placer soit un dossier de photos, soit un dossier de
vidéos dans `/storage/ambient/photos` ; le Mode Ambiant choisit automatiquement le mode adapté.

**Pack de vidéos par défaut** : `install.sh` appelle `kodi/scripts/ambient-download-videos.py`,
qui télécharge depuis Wikimedia Commons un petit pack de vidéos de paysages librement licenciées
(CC-BY / CC0 / domaine public). Le script utilise l'API MediaWiki pour résoudre les titres en URLs
de téléchargement direct et filtre les formats paysage >= 1280x720. Aucune clé API n'est requise.

**Fermeture sur `Back`** : en plein écran, Kodi n'associe pas toujours `Back`/`Escape` à `Stop`
lorsque le player est lancé depuis un script. Le keymap
`kodi/userdata/keymaps/akasha-ambient.xml` mappe donc `Back`/`Escape`/`B` à `Stop` dans
`FullscreenVideo`. `AmbientWindow._video_monitor_loop()` détecte `isPlaying() == False` et ferme
la fenêtre immédiatement. La fermeture (`exit()`) arrête explicitement le player pour libérer les
ressources vidéo avant le transfert vers `akasha-sleep.py`.

## Réutilisation de `akasha-sleep.py` pour l'état SLEEP

**Choix** : après `sleep_after_seconds`, appel de
`xbmc.executebuiltin('RunScript(/storage/.kodi/scripts/akasha-sleep.py)')`, puis fermeture de la
fenêtre Ambient.

**Raison** : évite de dupliquer la séquence CEC standby + veille + réveil-sur-interaction déjà
implémentée et validée. Utilisation du builtin `RunScript` plutôt que
`subprocess.Popen([sys.executable, ...])`, suite au bug découvert sur
`script.akasha.guide/default.py` où `sys.executable` ne pointait pas vers un interpréteur Python
utilisable depuis le runtime Kodi embarqué.
