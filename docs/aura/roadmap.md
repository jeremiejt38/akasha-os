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
- **Bloquant résolu (2026-08-18)** : option 1 retenue par l'utilisateur — le connector expose
  désormais `GET /api/plex/image?path=...` (voir `docs/api.md` du repo connector), qui injecte le
  token admin **côté serveur** et retourne les octets de l'image (validation anti-SSRF : le chemin
  doit commencer par `/library/`, aucun schéma protocolaire explicite accepté). Validé en
  conditions réelles : un vrai poster Plex (713 Ko, JPEG 2000x3000) récupéré via
  `https://connector.akasha.ing/api/plex/image?path=...` avec un token de session, sans jamais
  transmettre le token Plex admin au client.
  - `connector_client.image_url(plex_path)` (Aura) construit l'URL Kodi-compatible, avec le token
    de session attaché en header `Authorization` via la syntaxe d'options d'URL de Kodi
    (`url|Authorization=Bearer%20...`, voir `kodi.wiki/view/HTTP` — supportée nativement par le
    téléchargeur de textures de Kodi pour `ListItem.setArt()`), plutôt qu'en query string.
  - Le connector ne cache pas les images côté serveur (trop volumineuses pour le cache JSON
    existant) — le cache de texture natif de Kodi (`Textures13.db`) prend le relais côté client,
    cohérent avec la note de `decisions.md`/Phase 4 sur la réutilisation des mécanismes natifs.
- **Câblé et validé sur le device réel (2026-08-18, v0.27.0/v0.27.1)** : `_get_connector_client`
  (login via prompt clavier, token de session persisté dans `connector.session_token`, mot de passe
  jamais stocké — même pattern que Steam/Sunshine) ; `_load_divertissement`/
  `_select_divert_section` essaient le connector en premier, replient sur `plex_client.py` si le
  connector n'est pas configuré ou si la session est invalide.
  - **Bug trouvé et corrigé en conditions réelles** : Cloudflare (qui expose
    `connector.akasha.ing`) bloquait le User-Agent par défaut de `urllib` de Python
    (`Python-urllib/3.x`, détecté comme signature de bot, HTTP 403 error 1010) — d'où un repli
    silencieux sur Plex direct au premier essai. Fix : User-Agent explicite dans
    `connector_client.py` (v0.27.1).
  - Validé par PixelCamera + logs Kodi (aucun warning de repli) + logs du conteneur connector sur
    Unraid (`docker logs akasha-os-connector`) confirmant les appels réels `/api/auth/login`,
    `/api/plex/sections`, `/api/plex/sections/{key}/all`, `/api/plex/image` — mêmes posters
    affichés qu'en accès Plex direct, cette fois sans jamais exposer le token Plex admin au Pi.
  - **Point mineur non bloquant relevé** : le téléchargeur de textures de Kodi envoie une requête
    `HEAD` avant chaque `GET /api/plex/image` ; la route ne définit que `GET`, donc chaque `HEAD`
    reçoit `405` (sans impact — Kodi retente en `GET` juste après, qui réussit). À nettoyer un jour
    en ajoutant `@app.head` sur la route image si le volume de requêtes superflues devient notable.
- **"Pour vous" livré et validé sur le device réel (v0.28.0/v0.28.1)** : nouvelle fenêtre
  `AuraRecommendations.xml` (même patron que `AuraLibrary.xml`/`AuraShow.xml`), ouverte via un
  nouveau bouton de la barre du haut (à côté de Bibliothèque/Paramètres). Deux rangées horizontales
  de posters : "Continuer à regarder" (69 éléments constatés) et "Ajoutés récemment" (50 éléments),
  alimentées par le connector avec repli sur Plex direct. Validé par PixelCamera + logs du
  conteneur connector (tous les appels `/api/plex/on-deck`, `/api/plex/recently-added`,
  `/api/plex/image` bien reçus côté serveur).
  - Bug cosmétique trouvé et corrigé en conditions réelles : le libellé "Recommandations" (16
    caractères) était trop long pour le bouton de 230px et déclenchait le défilement de texte
    natif de Kodi (rendu tronqué/illisible sur capture). Raccourci en "Pour vous" (v0.28.1).
  - Pas encore fait : rangées "Sorties récentes"/"Suggestions par genre" par bibliothèque (comme
    `plex_client.entertainment_rows()` le fait déjà côté Plex direct), sous-onglet "Genres" dédié,
    hero banner en haut de la fenêtre. Le socle (connector + repli + rendu des rangées) est en
    place et prêt à les accueillir.

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
