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

## Pack de photos par défaut téléchargé (Wikimedia Commons "Featured pictures")

**Choix actuel (depuis v0.20.x)** : `kodi/scripts/ambient-download-photos.py` télécharge une liste
organisée (`DEFAULT_TITLES`) de photos de paysages issues de la catégorie Wikimedia Commons "Featured
pictures" (relues pour la qualité, licence libre CC-BY/CC-BY-SA/domaine public, format paysage).
Certains originaux dépassent 30 Mpx / 30 Mo, trop lourds pour que le `multiimage` du Pi 4 les décode
confortablement en diaporama : `scripts/prepare-ambient-photos.py`, appelé par `scripts/apply.sh` sur
la machine de build (même patron que `prepare-ambient-videos.py`), télécharge puis redimensionne
chaque photo à 1920x1080 maximum via `ffmpeg` (binaire local ou image Docker
`jrottenberg/ffmpeg:4.4-ubuntu` en repli), ramenant le pack complet à quelques Mo. `install.sh` copie
ensuite ce pack pré-redimensionné dans `/storage/ambient/photos` ; s'il est absent (installation
manuelle sans passer par `apply.sh`), `install.sh` retombe sur `ambient-download-photos.py` exécuté
directement sur le Pi (photos non redimensionnées). Chaque titre est résolu via l'API MediaWiki
(`action=query&prop=imageinfo`) pour obtenir une URL de téléchargement stable ; un fichier manifeste
(`.akasha-ambient-photos`) permet de retirer les anciennes photos du pack par défaut quand la liste
change sans toucher aux photos ajoutées manuellement par l'utilisateur. Le téléchargement n'est pas
fatal : si le réseau est indisponible, l'addon retombe sur son dossier `resources/media/fallback/`.

**Historique** : pack initial NASA EPIC (images de la Terre depuis l'espace, domaine public),
remplacé temporairement par un pack de vidéos de paysages (voir section suivante), puis restauré en
pack de photos suite à un retour utilisateur : le mode vidéo masque l'horloge et la météo (limitation
du plein écran vidéo décrite ci-dessous), ce qui rendait le Mode Ambiant perçu comme "juste une vidéo
qui tourne" plutôt que l'écran de veille horloge/météo/photos demandé. Le pack de photos permet à
l'overlay horloge/météo (`Ambient.xml`) de s'afficher normalement, comme prévu par la spec.

**Alternative écartée** : rester sur NASA EPIC. Écartée parce que les images EPIC (vues de la Terre
depuis l'espace, angle fixe) sont moins "immersives" pour un écran de veille domestique que des
paysages terrestres variés (montagnes, aurores, canyons, cascades), qui est le rendu visé (comparable
aux packs Ambient de Google TV / Apple TV).

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
`Back` de fermer le Mode Ambiant. `xbmc.Player().play(..., windowed=False)` donne un affichage plein
écran fiable. L'`AmbientWindow` (`WindowXML`) est fermée dès que la lecture démarre, car sinon elle
reste au-dessus de la vidéo et cache le contenu.

**Limitation connue** : pendant une vidéo, l'horloge et la météo ne sont pas affichées (ce n'est pas
un `videowindow` intégré). Le `multiimage` est simplement masqué pour éviter qu'une image ne
recouvre le player.

**Raison** : cela réutilise le player vidéo natif de Kodi (décodage matériel, boucle de playlist)
sans réécrire de lecteur. L'utilisateur peut placer soit un dossier de photos, soit un dossier de
vidéos dans `/storage/ambient/photos` ; le Mode Ambiant choisit automatiquement le mode adapté.

**Vidéos par défaut, puis retour en option manuelle (v0.20.x)** : `scripts/apply.sh` appelait
`scripts/prepare-ambient-videos.py` sur la machine de build, qui téléchargeait depuis Wikimedia
Commons un petit pack de vidéos de paysages librement licenciées (CC-BY / CC0 / domaine public) et
les re-encodait en H.264/AAC `.mp4` (nécessaire car LibreELEC/Kodi sur Raspberry Pi 4 n'a pas réussi
à décoder les originaux `.webm`/`.ogv`, VP8/VP9), puis `install.sh` copiait les `.mp4` préparés dans
`/storage/ambient/photos`. Comme `content_manager.resolve_media()` préfère les vidéos aux photos
dès qu'il en trouve dans le dossier configuré, ce pack vidéo était systématiquement choisi au
détriment du pack de photos — et donc l'horloge/météo (masquées en mode vidéo, voir la limitation
ci-dessous) ne s'affichaient jamais avec les réglages par défaut. Suite à ce retour, le pack vidéo
par défaut a été retiré : `install.sh` nettoie désormais tout pack vidéo par défaut installé par une
version antérieure (via son manifeste `.akasha-ambient-videos`) et télécharge le pack de photos à la
place (voir section précédente). `scripts/prepare-ambient-videos.py` et
`kodi/scripts/ambient-download-videos.py` restent disponibles pour qui veut reconstituer un pack
vidéo manuellement, mais ne sont plus appelés automatiquement par `apply.sh`/`install.sh`.

**Fermeture sur `Back`** : en plein écran, Kodi n'associe pas toujours `Back`/`Escape` à `Stop`
lorsque le player est lancé depuis un script. Le keymap
`kodi/userdata/keymaps/akasha-ambient.xml` mappe donc `Back`/`Escape`/`B` à `Stop` dans
`FullscreenVideo`. `AmbientWindow._video_monitor_loop()` détecte `isPlaying() == False` et ferme
la fenêtre immédiatement. La fermeture (`exit()`) arrête explicitement le player pour libérer les
ressources vidéo avant le transfert vers `akasha-sleep.py`.

## Tous les réglages centralisés dans Akasha Settings (v0.20.x)

**Choix** : `script.akasha.settings` (le menu "Akasha Settings" natif de la télécommande) expose
désormais chaque réglage du Mode Ambiant directement dans ses propres écrans (`Dialog.select`,
`Dialog.browse`, `Dialog.input`, `Dialog.numeric`) : activation, délai avant activation, dossier de
contenu, délai avant assombrissement, délai avant veille complète, météo activée/désactivée, ville,
coordonnées. Ces fonctions lisent/écrivent directement les réglages de `script.akasha.ambient` via
`xbmcaddon.Addon('script.akasha.ambient').getSetting()/setSetting()`.

**Alternative écartée (précédente)** : un unique item de menu "Configurer le Mode Ambiant..." qui
appelait `Addon.OpenSettings(script.akasha.ambient)`, renvoyant l'utilisateur vers l'écran de
réglages natif — distinct visuellement d'Akasha Settings.

**Raison** : le mainteneur veut que "tous les settings" du Mode Ambiant soient accessibles depuis
Akasha Settings, sans changer d'écran. `script.akasha.ambient/resources/settings.xml` reste la
source de vérité (stockage des valeurs, et écran de secours si l'addon est ouvert directement), mais
n'est plus le point d'entrée attendu pour l'utilisateur final.

## Réutilisation de `akasha-sleep.py` pour l'état SLEEP

**Choix** : après `sleep_after_seconds`, appel de
`xbmc.executebuiltin('RunScript(/storage/.kodi/scripts/akasha-sleep.py)')`, puis fermeture de la
fenêtre Ambient.

**Raison** : évite de dupliquer la séquence CEC standby + veille + réveil-sur-interaction déjà
implémentée et validée. Utilisation du builtin `RunScript` plutôt que
`subprocess.Popen([sys.executable, ...])`, suite au bug découvert sur
`script.akasha.guide/default.py` où `sys.executable` ne pointait pas vers un interpréteur Python
utilisable depuis le runtime Kodi embarqué.

## Ambient/sleep triggering while the user was actively watching content (2026-08-19)

**Constat utilisateur** : Akasha OS s'est mis en veille alors que l'utilisateur regardait du
contenu. Rappel du comportement voulu : la veille ne se déclenche que manuellement ou après une
inactivité *dans le mode Ambiant lui-même* ; le mode Ambiant, lui, ne doit s'activer que si (a)
aucune activité n'est détectée dans l'interface (`xbmc.getGlobalIdleTime()`) **et** (b) aucune
application/addon/extension n'est actuellement utilisée au premier plan.

**Cause** : `service.akasha.ambient/service.py::_should_trigger()` ne vérifiait que l'idle time et
`xbmc.Player().isPlaying()` — ce qui protège bien la lecture native Kodi (bibliothèque locale,
Jellyfin, la plupart des lectures Plex), mais pas un addon tiers avec sa propre fenêtre
personnalisée (ex. un client Plex qui ne passe pas systématiquement par `xbmc.Player()`, ou qui ne
réinitialise pas le minuteur d'inactivité global de Kodi pendant qu'il capture lui-même les
entrées). Dans ce cas, `idle_time` continue de grimper et `isPlaying()` peut rester `False` alors
que l'utilisateur regarde activement du contenu — Ambient se déclenche, puis, sans aucune
interaction pour l'arrêter (l'utilisateur suit son contenu, ne touche pas la télécommande), le
minuteur de veille interne d'Ambient (`ambient_window.py::_ticker_loop`) finit par déclencher la
mise en veille réelle.

**Corrigé** : nouvelle fonction pure et testée `config.is_foreground_app_active(is_window_active_fn)`
— retourne `True` si la fenêtre active n'est ni l'écran d'accueil natif (`home`) ni l'un des écrans
d'Akasha Aura lui-même (IDs `1194`-`1200`, parcourir Aura sans interaction reste couvert par le
seul idle time, comme avant). Toute autre fenêtre active (un addon tiers avec sa propre UI) bloque
désormais le déclenchement d'Ambient, quelle que soit la durée d'inactivité mesurée par Kodi.
Câblé dans `_should_trigger()` via `xbmc.getCondVisibility('Window.IsActive(...)')`.

Ce correctif ne couvre que le déclenchement *initial* d'Ambient (`service.akasha.ambient`) ; une
fois Ambient réellement actif, l'utilisateur reprend la main dès la moindre entrée
(`AmbientWindow.onAction` ferme immédiatement Ambient — spec section 17, "réveil immédiat").
