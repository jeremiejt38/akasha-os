# Akasha Aura — Roadmap

## v0.18.0 (ce chantier, jalon 1 — socle)

1. **Squelette addon** : `script.akasha.aura` (`addon.xml`, `default.py`, `settings.xml`), fenêtre
   `Aura.xml` avec 3 onglets navigables (radiobuttons + `Window.Property(AuraActiveTab)`), contenu
   placeholder par onglet.
2. **Module pur testable** : `config.py` (normalisation URL serveur Plex, validation config,
   construction des headers `X-Plex-Token`, résolution de l'onglet par défaut) — testé avec
   `python3 -m unittest`, sans dépendance `xbmc*`.
3. **Lancement au démarrage** : `service.akasha.aura` (service `xbmc.service`, `start="startup"`),
   attend la fin de l'intro puis ouvre Aura automatiquement.
4. **Bascule accueil** : keymap `akasha-aura.xml` redirige l'action `Home` vers Aura.
5. **Déploiement** : `install.sh` installe les deux nouveaux addons, copie le keymap, les enregistre
   activés dans la base Kodi.
6. **Tests** : unitaires (`config.py`) + validation réelle sur le Pi (PixelCamera + `kodi-send`) :
   démarrage → Aura s'ouvre automatiquement après l'intro, navigation gauche/droite entre les 3
   onglets, Back révèle l'accueil natif Kodi en dessous (filet de sécurité), bouton Home rouvre Aura
   depuis n'importe quel écran natif.
7. **Release** : commits Conventional Commits, Release Please → `0.18.0`.

## Prochains jalons (non livrés dans ce chantier)

1. **Divertissement — rangées Plex** : `plex_client.py` (testé unitairement avec des réponses HTTP
   mockées) pour "Continuer à regarder", "Ajoutés récemment", "Sortis récemment", rangées par genre.
   Détermination du mécanisme de lecture d'un item (délégation PM4K vs résolution directe du flux).
2. **Divertissement — bibliothèque complète** : vue liste complète par section avec recherche, tri
   et filtres.
3. **Jeux** : grille de tuiles à partir des shortcuts existants (`skin-patches/shortcuts/games*.xml`).
4. **App — inventaire** : `addons_inventory.py` (parsing `Addons.GetAddons`, persistance des
   addons épinglés), tuiles avec Lancer / Épingler / Désépingler / Désinstaller (délégation fenêtre
   native, voir `decisions.md`).
5. **Akasha Store** : `store_manifest.py` (manifeste JSON versionné des addons/dépôts déjà validés
   pour Akasha OS), installation depuis Aura (`InstallAddon` + ajout de dépôt si nécessaire).
6. **Validation finale** : une fois les 3 onglets réellement fonctionnels et validés en conditions
   réelles sur plusieurs sessions d'usage normal, considérer le chantier Aura terminé (déjà l'accueil
   par défaut depuis le jalon 1, donc pas de "bascule" supplémentaire à ce stade — seulement une
   confirmation que l'expérience est jugée satisfaisante par l'utilisateur).

## Notes de suivi

- Chaque jalon correspond à un ou plusieurs commits atomiques (`feat:`/`fix:`/`test:`), sur `main`
  par défaut (toléré par KSP pour un travail itératif en session), suivant `docs/PROJECT_WORKFLOW.md`.
- Talos est sollicité pour les modules purs (`config.py`, puis `plex_client.py`,
  `addons_inventory.py`, `store_manifest.py`) avec relecture systématique ; le reste (fenêtre XML,
  service Kodi, intégration keymap/install.sh) est écrit directement, conformément à
  `docs/talos-strategy.md`.
- Chantier volumineux et multi-session : livrer et valider chaque jalon sur le device réel avant de
  passer au suivant, plutôt que d'accumuler du code non testé (voir `AGENTS.md`, section release +
  redeploy après chaque patch).
