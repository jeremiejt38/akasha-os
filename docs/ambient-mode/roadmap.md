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

## Après v0.12 (non planifié dans ce chantier)

- **Investiguer pourquoi `xbmc.getGlobalIdleTime()` reste bloqué à 0** sur le Raspberry Pi actuel
  (vérifié après reboot complet, sans interaction). Pistes à explorer : pilote HID de la manette
  Xbox sans fil (rapports "heartbeat" périodiques via le récepteur USB), configuration CEC, ou un
  service tiers qui interroge Kodi en continu. Tant que ce n'est pas résolu, seule l'activation
  manuelle du Mode Ambiant fonctionne (voir `decisions.md`).
- Pack de paysages par défaut correctement sourcé (licence vérifiée), téléchargé à l'installation
  plutôt que commité dans le repo.
- Vidéos d'ambiance en boucle (`videowindow`), une fois le socle image validé en conditions réelles.
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
