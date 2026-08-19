# Compatibilité télécommande — Décisions techniques

Suivi du plan `dd440e2e-plan-compatibilite-telecommande-akasha-os.md`. Ce document répond aux
inconnues bloquantes du §0 du plan et documente les choix d'architecture qui en découlent.

## Inconnues levées (§0 du plan)

### 1. Protocole de liaison

**Bluetooth LE, profil HID standard** (pas de dongle RF 2.4GHz, pas de lien classique BR/EDR).
Télécommande `AR` / "Amazon Remote" (MAC `10:BF:67:30:D8:09`), appairée via `bluetoothctl` (voir
`atlas/projects/akasha-os.md`). Deux devices `/dev/input/` exposés : `event6` ("Amazon Remote
Keyboard", boutons) et `event7` ("Amazon Remote", `EV_SYN` seul — rôle non identifié, probablement
un canal de contrôle interne sans input utilisateur).

### 2a. Microphone (bouton assistant vocal)

**Voir le chantier séparé** `atlas/projects/akasha-os-voice-commands.md` (plan `c8c8548a`, mis en
pause). Résumé : le bouton envoie un événement standard (`KEY_VOICECOMMAND`/`KEY_ASSISTANT`), mais
le flux audio réel reste verrouillé derrière un protocole Alexa propriétaire non documenté —
confirmé par une capture Bluetooth en direct (`btmon`) ne montrant aucun trafic sur les 4 services
BLE vendor-specific pendant un appui du bouton.

### 2b. Buzzer / haut-parleur ("retrouver ma télécommande")

**Bloquant, même cause que le micro.** Recherche faite : la fonctionnalité "Remote Finder"
existe bel et bien chez Amazon, mais **uniquement sur le modèle "Alexa Voice Remote Pro"** (2022+,
avec haut-parleur physique dédié) — rien ne garantit que ce modèle générique ("Amazon Remote", sans
nom commercial distinctif) en dispose. Même sur le modèle Pro, le déclenchement passe par le cloud
Alexa puis une commande Bluetooth propriétaire vers la télécommande — le même mur protocolaire que
le micro. **Non implémenté.** Fallback LED envisagé par le plan (§3) non exploré non plus : aucune
caractéristique BLE de contrôle LED identifiée parmi les 4 services vendor-specific (voir liste
complète ci-dessous), et il n'existe pas de moyen de savoir si la télécommande a même une LED
contrôlable à distance sans documentation du protocole.

### 2c. Émetteur IR dans la télécommande

**Existe potentiellement, mais inexploitable en l'état.** Contrairement à l'hypothèse initiale
(les télécommandes Fire TV n'auraient pas d'IR), la recherche confirme que l'"Alexa Voice Remote"
standard **inclut un émetteur IR multidirectionnel** depuis 2018 (contrôle power/volume/mute de la
TV). Mais son déclenchement passe par une combinaison cloud Amazon + commande Bluetooth
propriétaire ("Fire TV OS envoie le code IR à émettre via Bluetooth à la télécommande") — même mur
protocolaire, non percé. **Alternative retenue si le contrôle IR TV est voulu** : un blaster IR
dédié sur GPIO du Raspberry Pi (LIRC, bien supporté, indépendant de la télécommande) plutôt que de
tenter de percer ce protocole. Non implémenté dans cette première itération (voir §5 du plan,
prochaine étape si prioritaire).

### 2d. Batterie

**Résolu, fonctionne dès maintenant.** Service BLE standard `0x180F` (Battery Service) exposé par
la télécommande — confirmé par `bluetoothctl info 10:BF:67:30:D8:09` qui affiche directement
`Battery Percentage: 0x5f (95)` sans aucun code supplémentaire. Implémenté dans
`service.akasha.remote` (voir ci-dessous).

## Services BLE vendor-specific découverts (référence pour un futur chantier de rétro-ingénierie)

Quatre services propriétaires Amazon, tous non documentés publiquement, confirmés associés au
protocole Alexa (fils OSMC/GitHub trouvés avec les mêmes UUID sur d'autres télécommandes Amazon) :

| Service UUID | Handle | Caractéristiques notify-capable |
|---|---|---|
| `cfbfb000-762c-4912-a043-20e3ecde0a2d` | 0xff02 | `cfbfb001` |
| `cfbfa000-762c-4912-a043-20e3ecde0a2d` | 0xfe02 | `cfbfa001`, `cfbfa002`, `cfbfa004` |
| `5de20000-5e8d-11e6-8b77-86f30ca893d3` | 0xfda2 | `5dd24a18`, `5de24a19` |
| `fe151500-5e8d-11e6-8b77-86f30ca893d3` | 0xfca2 | `fe151501`, `fe151503` |

Capture `btmon` en direct pendant un appui du bouton micro : **aucun trafic sur ces 4 services** —
seule une notification HID standard (handle `0x003b`, service `00001812`) a été observée, ce qui
confirme qu'une poignée de main d'initiation (écriture GATT) non documentée est nécessaire pour
activer n'importe quelle fonction avancée (audio, buzzer, IR) via ces services.

## Architecture retenue

### Daemon vs code Kodi natif — arbitrage empirique

Le plan proposait un daemon `akasha-remote-daemon` centralisant toute la logique, y compris la
distinction appui simple/long/double sur Home. **Testé empiriquement sur le device réel** : Kodi
(SDL2) pose un verrou exclusif (`EVIOCGRAB`) sur `/dev/input/event6` — un script Python séparé
ouvrant ce même device en lecture simple (sans grab) pendant que Kodi tourne normalement **reçoit
zéro événement**, même en pressant des touches. Un daemon lisant les événements bruts en parallèle
de Kodi ne fonctionne donc pas sans montage invasif (accaparer le device avant Kodi + périphérique
virtuel `uinput` filtré que Kodi lirait à la place) — risque de régression sur la navigation
existante jugé trop élevé.

**Architecture hybride retenue** :
- `service.akasha.remote` (nouveau, service Kodi `xbmc.service`) : tout ce qui ne touche pas à la
  capture d'input — pour l'instant, uniquement le monitoring de batterie via `bluetoothctl` (voir
  ci-dessous). Candidat naturel pour de futures tentatives GATT (buzzer/IR) si le protocole
  propriétaire est un jour percé.
- Distinction appui simple/long/double sur Home : **reste dans le code Kodi natif**, pas de daemon
  séparé, pas de risque sur le grab existant :
  - **Long press** : géré nativement par Kodi via le modificateur de keymap `mod="longpress"`
    (fonctionne sur les keymaps clavier, seuil ~250ms, `KEY_HOLD_TRESHOLD` côté C++ Kodi) — aucun
    code custom nécessaire. La télécommande envoie la touche `browser_home` (scancode 0xac), pas
    `home`, donc le keymap utilise `<browser_home mod="longpress">RunScript(script.akasha.guide)`.
  - **Double press** : Kodi n'a pas de modificateur "double press" natif. Pont IPC mis en place :
    quand Aura est déjà ouvert, un nouvel appui sur Home écrit un timestamp dans
    `/tmp/akasha-aura-home-press` et envoie `NotifyAll("akasha.aura", "HomePress", ...)` ;
    l'instance `AuraWindow` active écoute via un thread `xbmc.Monitor` (`home_press_monitor.py`) et
    applique la logique pure `classify_press` (`press_timing.py`) :
    - simple appui -> retour à l'onglet "Divertissement" d'Aura + fermeture des sous-fenêtres ;
    - double appui -> switcher d'applications minimal (dialogue natif listant les apps épinglées
      plus raccourcis système, en attendant un switcher skinné complet).

### Pas de librairie BLE Python disponible

LibreELEC ne fournit ni `gatttool` (déprécié dans bluez récent) ni `bleak`/`bluepy` (pip
indisponible sur ce système minimal). `bluetoothctl` (5.83) reste le seul outil confirmé
disponible, utilisé en sous-processus + parsing texte (`bluetoothctl_parser.py`, module pur testé)
pour la lecture de batterie. Toute future tentative GATT (buzzer/IR) devra passer soit par
`bluetoothctl`'s menu `gatt` interactif (scriptable via stdin, contraignant), soit par du D-Bus
direct (`dbus-python` — à vérifier si disponible).

## Livré dans cette itération

- `service.akasha.remote` : nouveau service Kodi, surveille la batterie de la télécommande
  (`bluetoothctl info`), notification Kodi unique en dessous du seuil configuré (hystérésis, pas de
  spam — `battery_alert.BatteryAlertTracker`), état persisté dans
  `/storage/.akasha/remote_state.json`. Réglages dans les settings de l'addon (adresse MAC,
  intervalle de sondage, seuil d'alerte).
- Keymap : appui court Home → Aura, appui long Home → Guide (`browser_home` + `mod="longpress"`).
- Double-appui Home → app switcher minimal (pont IPC NotifyAll + `home_press_monitor.py`).
- Volume : routage configurable vers Kodi local (`VolumeUp`/`VolumeDown`/`Mute`) ou TV via CEC
  (`cec-ctl --user-control-pressed ui-cmd=volume-up/down/mute`). Mode IR prévu mais non
  implémenté faute de matériel dédié.
- Bouton Power : déclenche `akasha-sleep.py` (CEC standby + HDMI off + wake-on-input).

## Reste à faire (prochaines itérations)

- App switcher skinné complet (remplacer le dialogue natif par une fenêtre Akasha dédiée).
- Bouton roue crantée → Akasha Settings (§9, keymap trivial une fois le keycode confirmé
  empiriquement sur le device).
- Touches services de streaming → no-op (§10) : keycodes non confirmés sur ce modèle de
  télécommande (peut ne pas avoir de boutons dédiés Netflix/Prime/Amazon — à vérifier avec
  l'utilisateur).
- Volume : implémenté (routage Akasha/CEC). Mode IR nécessite un blaster dédié.
- Bouton Power : implémenté (appelle `akasha-sleep.py`).
- App switcher skinné complet (remplacer le dialogue natif par une fenêtre Akasha dédiée).
- Affichage de la batterie et du sélecteur de mode volume dans Akasha Settings > Télécommande
  (nouvelle catégorie UI, pas encore ajoutée à `script.akasha.settings`).
- Buzzer/IR via la télécommande : bloqué par le protocole propriétaire, non retenté sauf décision
  explicite de l'utilisateur de poursuivre la rétro-ingénierie (cf. `docs/remote/decisions.md`
  §2b/2c ci-dessus pour le point de reprise exact — services/caractéristiques déjà identifiés).
