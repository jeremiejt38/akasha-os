# Paramètres unifiés Akasha OS — Décisions techniques

## Plan a5a87f03 — Phase 0 : audit exhaustif de l'existant

Audit mené en conditions réelles sur le Pi (JSON-RPC `Settings.GetSections`/`GetCategories`/
`GetSettings`, exploration manuelle de `service.libreelec.settings` via PixelCamera/`kodi-send`,
lecture directe de `script.akasha.settings/default.py`).

### Point de vigilance signalé (cahier section 5, dernier point)

Kodi seul expose **plus de 300 réglages individuels** répartis sur 36 catégories (voir tableau
ci-dessous). Un audit littéral réglage-par-réglage de l'intégralité de ce volume — y compris les
réglages PVR (non utilisés, Akasha OS n'a pas de tuner TV), Jeux/RetroPlayer (non utilisé, les jeux
passent par SteamLink/Moonlight, pas par l'émulation native Kodi), ou les dizaines d'options
avancées de sous-titrage/cache réseau/passthrough audio — serait disproportionné pour une seule
session et ferait perdre le fil de l'objectif réel (une interface unifiée pour ce qui compte
vraiment au quotidien, pas une réplique complète de Kodi).

**Découpage proposé, conforme à l'esprit de la section 3 du cahier ("ne pas reconstruire 100% dès
le premier jet")** :
- Audit **au niveau catégorie** pour l'intégralité de Kodi/LibreELEC/Akasha (tableau ci-dessous) —
  suffisant pour décider, catégorie par catégorie, "repris / partiellement repris / laissé en
  Avancé", sans lister les ~300 réglages un par un.
- Audit **au niveau réglage individuel**, détaillé, uniquement pour les 4 catégories prioritaires
  de la Phase 2 (Réseau & Connectivité, Comptes & Services, Affichage & Son, Manettes &
  Télécommandes) — ce sont celles qui seront implémentées en premier, donc celles qui ont
  réellement besoin de cette granularité maintenant. Les catégories de la Phase 3 recevront leur
  propre micro-audit détaillé au moment de leur implémentation plutôt que tout d'un bloc ici.

### Tableau catégorie → cible (niveau 1 : vue d'ensemble)

| Source | Catégorie source | Nb réglages | Catégorie Akasha cible | Décision |
|---|---|---|---|---|
| Kodi (games) | Général | 3 | — | Avancé (RetroPlayer non utilisé sur Akasha OS) |
| Kodi (games) | Succès | 3 | — | Avancé (idem) |
| Kodi (interface) | Habillage | 9 | Apparence & Interface | Partiel (uniquement ce qui a un sens hors "changer de skin", ex. police/zoom) |
| Kodi (interface) | Région | 12 | Apparence & Interface (+ Assistant premier démarrage, cf. `3aba4284`) | Repris (langue, fuseau horaire, format date/heure — déjà l'étape 2 du Quick Start) |
| Kodi (interface) | Écran de veille | 6 | Apparence & Interface | Partiel (délai + type ; le Mode Ambiant Akasha le remplace déjà en grande partie, voir `script.akasha.settings`) |
| Kodi (interface) | Verrouillage maître | 2 | Profils & Utilisateurs | Avancé pour l'instant (peu probable en usage salon actuel, à revoir si profils multiples activés) |
| Kodi (interface) | Démarrage | 2 | Système & Mises à jour | Avancé |
| Kodi (media) | Médiathèque | 15 | Bibliothèque & Lecture | Partiel (le scraping Kodi natif n'est pas le chemin principal, Aura utilise Plex/connector — la plupart de ces réglages sont sans effet réel sur l'expérience Akasha) |
| Kodi (media) | Général (listes fichiers) | 6 | — | Avancé |
| Kodi (media) | Vidéos | 23 | Bibliothèque & Lecture | Partiel (sous-titres par défaut, langue audio par défaut ; le reste avancé) |
| Kodi (media) | Musique | 17 | — | Avancé (YouTube Music est le chemin principal, pas la bibliothèque musicale Kodi) |
| Kodi (media) | Images | 3 | — | Avancé |
| Kodi (player) | Vidéos | 17 | Bibliothèque & Lecture | Partiel |
| Kodi (player) | Musique | 11 | — | Avancé |
| Kodi (player) | Disques | 12 | — | Avancé (pas de lecteur physique sur le boîtier) |
| Kodi (player) | Images | 4 | — | Avancé |
| Kodi (player) | Langue | 6 | Bibliothèque & Lecture | Repris (langue audio/sous-titres préférée — utile au quotidien) |
| Kodi (player) | Sous-titres | 21 | Bibliothèque & Lecture | Partiel (police/taille/couleur seulement) |
| Kodi (pvr) | *(8 catégories, 47 réglages au total)* | 47 | — | **Hors scope entier** (pas de tuner TV sur Akasha OS) |
| Kodi (services) | Général | 2 | Système & Mises à jour | Avancé |
| Kodi (services) | Contrôle | 9 | — | Avancé (contrôle distant HTTP/UPnP déjà couvert par `service.akasha.remote`) |
| Kodi (services) | UPnP/DLNA | 7 | — | Avancé |
| Kodi (services) | AirPlay | 5 | — | Avancé |
| Kodi (services) | Client SMB | 7 | — | Avancé |
| Kodi (services) | Client NFS | 2 | — | Avancé |
| Kodi (services) | Mise en cache | 4 | — | Avancé |
| Kodi (services) | Météo | 2 | Apparence & Interface | Avancé (le Mode Ambiant a sa propre config météo dans Akasha Settings) |
| Kodi (system) | Affichage | 13 | **Affichage & Son** | **Repris** (résolution, taux de rafraîchissement — cœur de l'étape 4 du Quick Start) |
| Kodi (system) | Audio | 19 | **Affichage & Son** | **Repris** (périphérique de sortie, passthrough, volume interface) |
| Kodi (system) | Entrée | 6 | **Manettes & Télécommandes** | **Repris** (manettes, disposition clavier) |
| Kodi (system) | Accès Internet | 7 | **Réseau & Connectivité** | Partiel (proxy/bande passante — avancé ; le Wi-Fi/Ethernet réel est géré par LibreELEC, pas Kodi, voir plus bas) |
| Kodi (system) | Gestion de l'énergie | 5 | Énergie | Repris (délai veille écran, délai arrêt auto — déjà en grande partie dupliqué dans Akasha Settings) |
| Kodi (system) | Extensions | 7 | Système & Mises à jour | Partiel (mises à jour auto, sources inconnues) |
| Kodi (system) | Journalisation | 7 | — | Avancé (diagnostic, pas un réglage utilisateur) |
| LibreELEC | Système (nom, clavier, PIN, sauvegarde/restauration, reset, MAJ) | ~10 | Système & Mises à jour | Repris (c'est la vraie source de vérité pour nom d'hôte, sauvegarde, mise à jour LibreELEC) |
| LibreELEC | Réseau (Wi-Fi actif, filaire actif, NTP, VPN) | ~6 | **Réseau & Connectivité** | **Repris** — c'est ICI, pas dans Kodi, que vit le vrai statut réseau |
| LibreELEC | Connexions (liste Wi-Fi + connexion) | dynamique | **Réseau & Connectivité** | **Repris intégralement** — réutilisé tel quel par l'étape 3 du Quick Start (`3aba4284`) |
| LibreELEC | Bluetooth (appairage) | dynamique | **Manettes & Télécommandes** | **Repris intégralement** — réutilisé tel quel par l'étape 5 du Quick Start |
| LibreELEC | Services (Samba/SSH/Cron/Avahi/Syslog) | ~8 | — | Avancé (administration système, pas un réglage utilisateur quotidien) |
| LibreELEC | À propos | — | Système & Mises à jour | Repris (affichage seul) |
| Akasha (`script.akasha.settings`) | Mise à jour Akasha OS | 1 | Système & Mises à jour | Repris intégralement |
| Akasha | Infos système (température CPU) | 1 | Système & Mises à jour | Repris intégralement |
| Akasha | Overlay système | 1 | Apparence & Interface | Repris intégralement |
| Akasha | Mode Ambiant (activation, délais, dossier, météo) | 8 | Apparence & Interface | Repris intégralement |
| Akasha | Veille & Extinction (délai écran, délai arrêt, mode extinction) | 3 | Énergie | Repris intégralement — **fusionne avec les réglages d'énergie Kodi ci-dessus, pas de doublon dans le panneau final** |
| Akasha | Matériel (test ventilateur, test CEC) | 2 | Énergie | Repris intégralement |
| Akasha | Actions (Redémarrer/Éteindre) | 3 | *(hors périmètre)* | **Non repris dans le panneau** : ce sont les mêmes actions déjà présentes dans le menu contextuel Paramètres (`04bda1b4`), pas des réglages — cohérent avec la note d'ajustement en tête du cahier `a5a87f03` |
| Comptes de contenu | Plex (`script.plexmod`), Jellyfin (`plugin.video.jellyfin`), YouTube Music (`plugin.video.youtube`) | — | **Comptes & Services** | Partiel pour l'instant : chaque service a déjà son propre écran de connexion/compte dans son addon respectif (pas de flux `plex.tv/link` unifié construit à ce jour dans Aura — les settings actuels d'Aura pour Plex sont une URL+token en texte brut). Phase 2 doit décider si on construit un vrai flux unifié ou si on se contente d'un point d'entrée vers l'écran natif de chaque addon (voir "Points ouverts" plus bas). |
| Cloud gaming | Steam Link, Moonlight, Sunshine | — | Comptes & Services / module Jeux | Repris partiellement — configuration déjà dans `script.akasha.aura` (`steam.*`, `sunshine.*`), pas dans Kodi natif |

### Détail des 4 catégories prioritaires de la Phase 2 (niveau réglage)

#### 1. Réseau & Connectivité
- **Source réelle : LibreELEC**, pas Kodi (`system:network` de Kodi ne couvre que le proxy HTTP et
  la limite de bande passante — pas le Wi-Fi/Ethernet lui-même).
- LibreELEC "Réseau" : interface active (Wi-Fi/filaire), adresse IP, méthode (DHCP/statique),
  état, serveurs NTP, VPN (visible dans l'onglet mais non exploré en détail dans cette session,
  Akasha OS n'a pas de VPN client actif à ce jour d'après `docs/network.md` d'Atlas).
- LibreELEC "Connexions" : liste des réseaux Wi-Fi détectés + connexion (mot de passe via clavier
  virtuel) — **c'est l'écran exact dont l'étape 3 du Quick Start (`3aba4284`) a besoin**, à réutiliser
  tel quel plutôt que réimplémenté.
- Kodi `system:network` (proxy, bande passante) : Avancé.

#### 2. Comptes & Services
- Plex : `script.plexmod` a son propre écran de compte (déjà l'app Plex authentique, voir
  `docs/aura/decisions.md`). Aura stocke séparément `plex.server_url`/`plex.token` en configuration
  manuelle (pas de lien compte).
- Jellyfin : `plugin.video.jellyfin` gère sa propre connexion serveur.
- YouTube Music : `plugin.video.youtube` gère sa propre connexion compte Google.
- Cloud gaming : Steam (`steam.api_key`/`steam.steam_id`) et Sunshine/Moonlight
  (`sunshine.server_url`/`username`/`password`) déjà configurables dans les settings de
  `script.akasha.aura`, pas de compte à lier à proprement parler pour Steam Link/Moonlight/GeForce
  NOW/Xbox Cloud Gaming/Amazon Luna/Boosteroid (ce sont des clients de streaming, l'authentification
  se fait dans leur propre client au premier lancement, pas dans un écran de settings Kodi).
- **Point ouvert à trancher en Phase 2** : construire un vrai panneau "Comptes" qui centralise
  l'état (connecté/non connecté) de chaque service avec un bouton "Configurer" qui ouvre l'écran
  natif de l'addon concerné (repris partiellement, périmètre raisonnable), plutôt que de
  réimplémenter chaque flux de connexion (ex. `plex.tv/link`) dans l'UI Akasha — earlier plans
  n'ont pas construit ce flux, seulement mentionné son existence future.

#### 3. Affichage & Son
- Kodi `system:display` (13 réglages) : résolution, taux de rafraîchissement, calibration,
  espace colorimétrique, mode 3D — **repris intégralement**, ce sont de vrais réglages Kodi actifs.
- Kodi `system:audio` (19 réglages) : périphérique de sortie, passthrough (AC3/DTS), volume
  interface — **repris intégralement**.
- HDMI-CEC : gestion déjà présente côté Akasha (veille CEC TV, `akasha-sleep.py`,
  `cec-standby.sh`) plutôt que dans les réglages Kodi standards (Kodi n'a pas de case "CEC
  on/off" simple dans `system:display` sur cette version) — le réglage CEC user-facing pertinent
  est donc "activer/désactiver la synchronisation veille TV", à construire côté Akasha plutôt qu'à
  chercher dans Kodi.

#### 4. Manettes & Télécommandes
- Kodi `system:input` (6 réglages) : `input.controllerconfig` (configurer les manettes connectées)
  est le point d'entrée natif pour l'appairage/mapping manette — **repris intégralement**.
- Bluetooth : géré par LibreELEC (onglet "Bluetooth"), pas par Kodi — **repris intégralement**,
  réutilisé tel quel par l'étape 5 du Quick Start (`3aba4284`).
- Télécommande IR/CEC : déjà configurée au niveau système (`scripts/diagnose-joystick.py`,
  keymap déjà installés par `scripts/install.sh`), pas un écran de réglage utilisateur à proprement
  parler aujourd'hui — à re-examiner si un vrai besoin de reconfiguration en direct émerge.

## Phases 1 à 4 : panneau unifié implémenté

Sur demande explicite de Jérémie ("termine toutes les phases manquantes"), les Phases 1 à 4 ont
été implémentées en une passe (le panneau à 2 volets couvre naturellement l'intégralité des
catégories d'un coup, contrairement au Quick Start qui a de vraies étapes séquentielles
indépendantes).

### Architecture (Phase 1)

Nouvelle fenêtre `AuraSettingsPanelWindow` (`resources/lib/aura_settings_panel.py` +
`AuraSettingsPanel.xml`) dans `script.akasha.aura` :
- Panneau ancré à droite (`left=420`, largeur 1500/1920), glisse depuis la droite à l'ouverture
  (`WindowOpen` animation), recouvre un voile semi-transparent sur ce qu'il y a derrière.
- Colonne de gauche : liste des 11 catégories. Colonne de droite : actions de la catégorie
  sélectionnée, mise à jour dynamiquement à la sélection (master-detail, pas besoin de valider).
- Remontée logique sur "Retour" : si le focus est dans le détail, revient d'abord à la liste des
  catégories ; sinon ferme le panneau.
- Remplace les 3 entrées séparées "Paramètres Kodi/LibreELEC/Akasha" du menu contextuel
  (`04bda1b4`) par une seule entrée "Paramètres" qui ouvre ce panneau — les entrées d'action
  (Mise en veille/Redémarrer/Arrêt) restent inchangées, conformément à la note d'ajustement en
  tête du cahier `a5a87f03`.

### Bug découvert et corrigé : fenêtres natives invisibles derrière Aura

Aura (`script.akasha.aura`) est elle-même une fenêtre `type="dialog"`, ce qui la fait toujours
s'afficher au-dessus de tout le reste — y compris des fenêtres natives Kodi de type "base window"
(Paramètres, Système, Profils...) qui ne sont pas des dialogues. Résultat : lancer
`ActivateWindow(...)` vers l'une de ces fenêtres natives depuis une action du panneau changeait
bien la fenêtre de base en arrière-plan, mais Aura restait affichée par-dessus, rendant le
changement invisible à l'utilisateur (déjà probablement le cas, non détecté, pour les anciennes
entrées "Paramètres Kodi" du menu contextuel `04bda1b4`). Corrigé en fermant explicitement le
panneau **et** la fenêtre Aura elle-même avant de déclencher l'action de chaque ligne — les
fenêtres/dialogues d'autres addons (LibreELEC Settings, Plex, Jellyfin...) s'empilent
normalement par-dessus sans avoir besoin de cette fermeture, mais la fermeture systématique reste
sûre pour ces cas aussi (leur propre dialogue devient alors la fenêtre du dessus, sans changement
visible). Conséquence acceptée : revenir en arrière depuis un écran natif ramène sur le Kodi natif
plutôt que directement dans Aura — cohérent avec le comportement déjà établi d'Aura (Bouton Retour
depuis Aura révèle déjà le Kodi natif comme filet de sécurité), pas une régression.

### Bug moteur Kodi découvert (hors périmètre de correction) : crash sur `peripheralsettings`

En testant en conditions réelles sur le Pi, `ActivateWindow(peripheralsettings)` (entrée native
Kodi pour configurer manettes/périphériques) fait **planter Kodi** de façon reproductible
(`SIGSEGV` dans `CVariant::CVariant`, cf. `/storage/.kodi/temp/kodi_crashlog_*.log`) — reproduit
deux fois de suite, y compris via un appel JSON-RPC direct sans passer par le code Akasha,
confirmant qu'il s'agit d'un bug du moteur Kodi/LibreELEC sur ce matériel, indépendant de ce
chantier. **Retiré de la catégorie "Manettes & Télécommandes"** (qui ne propose donc que
l'appairage Bluetooth LibreELEC, déjà confirmé sûr) plutôt que d'exposer un point d'entrée qui
plante l'OS. Toutes les autres cibles `ActivateWindow` utilisées dans le panneau
(`settings`, `systemsettings`, `profilesettings`, `skinsettings`, `servicesettings`,
`playersettings`, `interfacesettings`, `filemanager`, `mediasettings`) ont été testées
individuellement en direct sur le Pi et ne provoquent aucun plantage.
**À signaler à Jérémie** : la configuration manette/périphérique native Kodi est actuellement
inutilisable sur ce Raspberry Pi (plante systématiquement), indépendamment de tout ce qui a été
livré dans ce chantier — un ticket LibreELEC/Kodi amont serait probablement justifié si ce point
devient bloquant un jour.

### Contenu des 11 catégories (Phases 2 et 3)

Chaque catégorie propose 1 à 4 actions réelles (pas de placeholder cosmétique), soit vers un écran
natif Kodi/LibreELEC/addon existant, soit vers `script.akasha.settings` pour ce qu'Akasha gère déjà
lui-même :

| Catégorie | Actions |
|---|---|
| Réseau & Connectivité | Wi-Fi/Ethernet/VPN (LibreELEC) · Proxy/bande passante (Kodi) |
| Comptes & Services | Plex · Jellyfin · YouTube Music · Cloud gaming (settings `script.akasha.aura`) |
| Affichage & Son | Résolution/HDR/CEC/audio (Kodi, `systemsettings`) |
| Manettes & Télécommandes | Bluetooth (LibreELEC) — voir bug moteur ci-dessus |
| Bibliothèque & Lecture | Langue/sous-titres par défaut (Kodi) · réglages bibliothèque/lecture (Kodi) |
| Apparence & Interface | Langue interface/région/veille (Kodi) · Habillage skin (Kodi) · Overlay/Mode Ambiant (Akasha) |
| Stockage | Sources et gestionnaire de fichiers (Kodi) |
| Énergie | Veille écran/extinction auto (Kodi) · Délai veille/ventilateur (Akasha) |
| Système & Mises à jour | Nom système/sauvegarde/MAJ LibreELEC · Vérifier MAJ Akasha OS · MAJ extensions (Kodi) |
| Profils & Utilisateurs | Gérer les profils (Kodi, `profilesettings`) |
| Avancé | Tous les paramètres Kodi · Tous les paramètres LibreELEC |

### Polish visuel et tests (Phase 5)

Charte graphique Akasha reprise à l'identique du reste de l'OS (fond `FF10131A`, accent
`FF6C8CFF`, dégradé pilule, coins arrondis via `rounded-solid.png`, cf.
`docs/aura/decisions.md`), pas d'apparence Kodi générique. Validé en direct sur le Pi : ouverture
du panneau depuis le menu contextuel (une seule entrée "Paramètres" désormais), navigation entre
les 11 catégories avec mise à jour du détail, ouverture réussie de LibreELEC Settings/Kodi
Paramètres/Profils avec fermeture propre d'Aura, remontée logique sur Retour, relance d'Aura
propre après une action. Test manette Xbox Wireless/télécommande IR physiques non fait dans cette
session (accès distant uniquement, comme pour les chantiers précédents).
</content>
