# Mode Ambiant — Roadmap

## v0.12 (ce chantier)

1. **Socle addon** : `screensaver.akasha.ambient` (addon.xml, default.py, settings.xml), enregistré
   dans `install.sh`, sélectionnable comme screensaver Kodi.
2. **Modules purs testables** : `config.py`, `content_manager.py`, `weather_client.py`, `energy.py`
   (aucune dépendance `xbmc*`, testés avec `python3 -m unittest` sans Kodi).
3. **Rendu skin** : `Ambient.xml` — fond `multiimage`, horloge (info-labels natifs), météo
   (propriétés de fenêtre), overlay d'assombrissement, 4 presets de position anti-marquage.
4. **Orchestration** : `ambient_window.py` — boucle `onInit`, minuteries assombrissement/veille,
   rotation des presets, rafraîchissement météo en tâche de fond, sortie propre sur
   `onScreensaverDeactivated`.
5. **Intégration Akasha Settings** : entrée de menu "Mode Ambiant" (accès rapide aux réglages,
   activation/désactivation).
6. **Intégration Akasha Guide** : entrée "Mode Ambiant" pour activation manuelle immédiate.
7. **Déploiement** : `install.sh` copie l'addon, crée `/storage/ambient/photos`, active le
   screensaver par défaut sans écraser un choix déjà personnalisé par l'utilisateur.
8. **Tests** : unitaires (modules purs) + validation réelle sur le Pi (PixelCamera + `kodi-send`) :
   activation manuelle, rotation, horloge, météo, assombrissement, veille, réveil.
9. **Release** : commits Conventional Commits, Release Please → v0.12.0.

## v0.14.x/v0.17.x (ce chantier)

1. **Pack de paysages par défaut** : téléchargement depuis Wikimedia Commons (vidéos librement
   licenciées, scènes fixes : vagues, cascades, rivières) via `kodi/scripts/ambient-download-videos.py`
   et re-encodage H.264/AAC `.mp4` par `scripts/prepare-ambient-videos.py` pour la compatibilité du
   Raspberry Pi 4. Pack initialement NASA EPIC, remplacé par des vidéos de paysages à la demande.
2. **Support des vidéos d'ambiance en boucle** : `content_manager.resolve_media()` détecte les
   vidéos, `AmbientWindow` démarre un `xbmc.Player` en plein écran (`windowed=False`) puis ferme
   immédiatement le `WindowXML` pour ne pas cacher la vidéo. Un thread `isPlaying()` ferme le Mode
   Ambiant sur `Back`/`Stop`. Keymap `akasha-ambient.xml` renforce `Back`/`Escape`/`B` -> `Stop` en
   `FullscreenVideo`. L'horloge/météo ne s'affiche pas pendant une vidéo.
3. **Correction `multiimage` aspectratio** : `crop` n'est pas une valeur valide pour Kodi ; passage
   à `scale` pour conserver le ratio et remplir l'écran.
4. **Tests unitaires** : `list_videos`, `resolve_media`, fallback vidéo/image.
5. **Release + déploiement** : commits Conventional Commits, Release Please, validation sur le Pi
   (PixelCamera + `kodi-send`).

## v0.20.x (ce chantier)

1. **Retour à un pack de photos par défaut** : le pack vidéo par défaut (`prepare-ambient-videos.py`
   / `ambient-download-videos.py`, appelés depuis `scripts/apply.sh`/`install.sh`) masquait l'horloge
   et la météo (limitation connue du mode vidéo, voir `decisions.md`) — l'expérience perçue était
   "juste une vidéo qui tourne", pas l'écran de veille horloge/météo/photos demandé. `install.sh`
   déploie désormais par défaut un pack de photos de paysages (Wikimedia Commons "Featured
   pictures", licence libre, format paysage), pré-redimensionné à 1920x1080 max par
   `scripts/prepare-ambient-photos.py` (build host, `ffmpeg`) pour rester léger à décoder sur le Pi,
   avec repli sur un téléchargement brut (`kodi/scripts/ambient-download-photos.py`) si le pack
   pré-redimensionné est absent. Le pack vidéo par défaut installé par une version antérieure est
   supprimé. Le mode vidéo reste disponible mais devient un choix manuel de l'utilisateur (déposer
   ses propres `.mp4` dans le dossier de contenu) plutôt que le comportement par défaut.
2. **Tous les réglages dans Akasha Settings** : `script.akasha.settings` expose désormais chaque
   réglage du Mode Ambiant directement dans son menu (délai d'activation, dossier de contenu, délai
   d'assombrissement, délai de veille, météo activée/désactivée, ville, coordonnées) au lieu de
   renvoyer vers l'écran de réglages natif de l'addon (`Addon.OpenSettings`). Les valeurs restent
   stockées dans les réglages de `script.akasha.ambient` (source de vérité unique) ; Akasha Settings
   les lit/écrit via `xbmcaddon.Addon('script.akasha.ambient')`.

## Après v0.20.x (non planifié dans ce chantier)

- Effet Ken Burns (zoom/pan lents) sur les images fixes, si le rendu `multiimage` seul s'avère trop
  statique à l'usage.
- Activation programmée par plage horaire (thème jour/nuit).
- Détection de présence (capteur/caméra), désactivée par défaut, traitement local uniquement.
- Sources de contenu réseau (NAS, cloud personnel) au-delà du dossier local simple.
- Modules complémentaires : musique, calendrier, actualités, domotique.
- Mode confidentialité "Ambiant public" (masquage photos personnelles/calendrier).
- Génération procédurale de fonds (particules, gradients) pour varier le contenu de secours.
- Synchronisation multi-écrans (hors périmètre tant qu'Akasha OS reste mono-appareil par foyer).

## Notes de suivi

- Chaque étape ci-dessus correspond à un ou plusieurs commits atomiques (`feat:`/`fix:`/`test:`),
  suivant `docs/PROJECT_WORKFLOW.md`. Pas de branche dédiée unique pour tout le chantier : travail
  direct sur `main` par commits atomiques, comme pour les patchs précédents (toléré par KSP pour un
  travail itératif en session, cf. section "Accumulation de commits avant release").
- Talos est sollicité pour les modules purs (`content_manager.py`, `weather_client.py`, `energy.py`)
  avec relecture systématique ; le reste (addon Kodi, skin XML, intégration) est écrit directement.
