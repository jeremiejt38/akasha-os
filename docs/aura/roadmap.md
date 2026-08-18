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

## Jalon 6 (en cours) — intégration `akasha-os-connector` (cache + auth multi-utilisateurs)

Suite au cahier des charges "interface-plex-akasha" (voir `atlas/projects/akasha-os.md`), adapté à
l'architecture Aura existante (WindowXMLDialog, pas de patch de `Home.xml` — voir `decisions.md`).

- **Livré** : `connector_client.py` (module pur, testé, même style que `plex_client.py`) —
  `login`/`is_authenticated`/`on_deck`/`recently_added`/`sections`/`section_items`/
  `section_genres`/`metadata_children`, parlant à l'API REST d'`akasha-os-connector`
  (`docs/api.md` du repo connector). Réglages `connector.server_url`/`connector.username` ajoutés à
  `settings.xml`.
- **Bloquant identifié avant d'aller plus loin** : le connector renvoie actuellement le **JSON Plex
  brut** (passthrough en cache), qui contient des chemins d'image relatifs
  (`/library/metadata/123/thumb/1`) nécessitant le token Plex admin pour être résolus en URL
  affichable (`plex_client._video_dict` fait ce travail avec `self.token`). Or le but même du
  connector est que les clients akasha-os n'aient **jamais** ce token admin. Câbler
  `connector_client` directement dans `aura_window.py` sans résoudre ce point casserait
  silencieusement l'affichage des posters/fanarts en production.
- **Ce qu'il faut trancher avant d'intégrer réellement le connector dans l'UI Aura** (décision
  d'architecture, pas déléguée à Talos) :
  1. Le connector expose un endpoint proxy d'images (ex. `GET /api/plex/image?path=...`) qui
     injecte le token admin côté serveur et sert les octets de l'image — le client n'a jamais le
     token. C'est l'option la plus propre pour l'objectif multi-utilisateurs, mais demande un
     endpoint supplémentaire + tests + cache d'images.
  2. Le connector réécrit lui-même les champs `thumb`/`art` dans les réponses JSON pour pointer
     vers son propre domaine (`connector.akasha.ing/images/...`), plus transparent côté client.
  3. Repli temporaire : ne pas encore utiliser le connector pour les données Divertissement
     (garder l'appel direct à `plex_client.py`, déjà en production et fiable), et limiter l'usage
     du connector à l'authentification multi-utilisateurs pour l'instant (le connector reste
     fonctionnel et testé de bout en bout côté serveur, prêt à être branché une fois ce point
     tranché).
- **Non commencé** : sous-onglets "Recommandations" (hero banner + rangées Continuer à
  regarder/Ajoutés récemment/Suggestions) et "Genres" au sein de Divertissement, flux de login
  (prompt clavier + bouton profil dans la sidebar), tout ce qui dépend du point ci-dessus.

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
