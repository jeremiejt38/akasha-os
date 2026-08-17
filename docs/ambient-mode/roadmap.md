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

## Après v0.17.x (non planifié dans ce chantier)

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
