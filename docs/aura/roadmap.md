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
- **Rangée "Sorties récentes" ajoutée et validée (v0.29.0)** : 3ème rangée dans "Pour vous",
  premiere section vidéo trouvée, triée par date de sortie (`sort=originallyAvailableAt:desc`).
  Tuiles réduites (170x250) pour que les 3 rangées tiennent sur l'écran. Validé par PixelCamera
  (Minions, Toy Story 5... bien affichés, triés par date). Note : le compteur affiche la taille
  totale de la section (771) et non un sous-ensemble limité — comportement Plex déjà connu
  ailleurs dans le projet, `X-Plex-Container-Size` en query string n'est pas honoré par
  `/library/sections/{key}/all` sur ce serveur Plex (vérifié en direct, pas un bug introduit par le
  connector). Cohérent avec l'affichage déjà existant du compteur de la grille Divertissement.
- **Alignement sur la référence Plex fournie par l'utilisateur (2026-08-18, v0.30.0 → v0.31.3)** :
  - Barre du haut : 4 boutons **Recommandé / Bibliothèque / Catégories / Paramètres** (élargis à
    255px après un premier essai trop étroit qui tronquait les libellés).
  - **Nouvelle vue Catégories** (`AuraGenres.xml`/`aura_genres.py`) : grille de genres (`panel`,
    vraie grille avec retour à la ligne, 30 catégories affichées pour Dessins Animées), sélection
    d'un genre → ouvre Bibliothèque pré-filtrée sur ce genre + cette section
    (`AuraLibraryWindow.initial_section`/`initial_genre`).
  - Libellés 2 lignes (titre + `S{saison} - E{episode}` ou année) dans la grille Divertissement et
    les rangées "Recommandé", via `divert_source.item_subtitle()` (pur, testé).
  - Bibliothèque (`aura_library.py`) câblée sur le connector (recherche/tri/genre) avec repli Plex
    direct, complétant l'intégration sur les 3 vues (Divertissement, Recommandé, Bibliothèque).
  - **3 bugs réels trouvés et corrigés en conditions réelles sur le Pi** :
    1. `section_genres` lisait le champ `tag` au lieu de `title` dans la réponse Plex — bug latent
       depuis les tout premiers milestones (v0.19.0/v0.21.1), jamais remarqué car le filtre Genre
       de Bibliothèque n'avait jamais été testé avec un genre réellement sélectionné jusqu'à la
       nouvelle vue Catégories qui l'a rendu évident (0 catégorie affichée alors que la section en
       a 30, confirmé par un appel API direct).
    2. `connector_client.section_items()` (Aura) n'avait jamais été mis à jour pour transmettre
       `genre`/`search` au connector, malgré leur ajout côté serveur — plantage immédiat au premier
       usage réel du filtre Genre via Catégories.
    3. Les valeurs de `sort`/`genre`/`search` n'étaient pas URL-encodées dans les query strings du
       connector.
  - Validé de bout en bout : Catégories → sélection "Action" → Bibliothèque affiche
    "264 resultat(s) (Action)" avec la vraie liste filtrée.

- **Sidebar rétractable pour Divertissement, alignée sur la référence Plex fournie par
  l'utilisateur (2026-08-18, v0.32.0/v0.32.1)** : remplace les 9 boutons horizontaux (déjà à leur
  limite de troncature) par une sidebar verticale — repliée par défaut (~100px, icônes seules),
  se déplie entièrement (420px, icône + libellé) quand elle prend le focus
  (`Control.HasFocus(3310)` + animation `slide`), se rétracte automatiquement dès que le focus
  repart vers le contenu. "Accueil" (icône maison) en premier (ouvre "Recommandé"), une entrée par
  bibliothèque Plex ensuite (icône film ou TV selon `type`). Icônes générées via PIL
  (`icon-home.png`/`icon-film.png`/`icon-tv.png`).
  - **Bug de navigation trouvé et corrigé en conditions réelles** : le `onright` de la sidebar
    pointait vers un `<label>` (non focalisable en Kodi), ce qui faisait sauter la navigation
    "Droite" jusqu'à l'onglet Jeux au lieu d'atteindre la grille de posters. Corrigé pour pointer
    vers le panel de posters (focalisable).
  - Validé par PixelCamera : repli par défaut, dépli complet au focus (icônes+libellés lisibles,
    type film/TV correctement associé à chaque bibliothèque), rétraction propre en sortant vers la
    grille.

- **Chargement incrémental (lazy loading) + cache local sur le Pi, livré et validé (2026-08-18,
  v0.33.1/v0.33.2)** : demande explicite de l'utilisateur pour éviter de charger des centaines
  d'éléments d'un coup.
  - `paged_list.PagedList` (pur, testé) : charge une première page (30 éléments par défaut), puis
    charge la page suivante uniquement quand la sélection de l'utilisateur approche à moins de 15
    éléments de la fin du contenu déjà chargé — reproduit exactement le comportement demandé
    ("si l'utilisateur avance au 15ème sur 30 chargés, on charge les 15 suivants").
  - `local_cache.LocalCache` (pur, testé) : cache TTL sqlite sous le dossier de profil de l'addon,
    pour que revisiter une rangée/section dans la fenêtre de TTL soit instantané. Les affiches
    restent gérées par le cache de texture natif de Kodi (`Textures13.db`), déjà persistant entre
    sessions — pas de duplication de cache d'images côté addon.
  - Câblé dans les 3 vues qui chargent des données Plex : `aura_recommendations.py` (3 rangées),
    `aura_window.py` (grille Divertissement), `aura_library.py` (liste Bibliothèque, y compris
    recherche/genre).
  - Connector (`akasha-os-connector` v0.4.0) : ajout du paramètre `offset` (`X-Plex-Container-Start`)
    sur `on-deck`/`recently-added`/`section_items`, indispensable à la pagination. Découverte
    utile en testant : Plex ignore `X-Plex-Container-Size` seul sur `/library/sections/{key}/all`
    (renvoie toute la bibliothèque) mais respecte la pagination dès que `X-Plex-Container-Start`
    est aussi fourni — corrige au passage le compteur "771 éléments" cosmétique du jalon précédent.
  - **2 bugs trouvés et corrigés en conditions réelles sur le Pi** :
    1. Le focus initial de la fenêtre "Recommandations" restait sur le bouton "Retour"
       (`<defaultcontrol>`) plutôt que sur la première rangée, empêchant Gauche/Droite d'atteindre
       les rangées et donc le déclenchement du chargement incrémental. Corrigé en focalisant
       explicitement la première rangée non vide une fois les rangées peuplées.
    2. Chaque liste/grille Kodi affiche sa position sélectionnée avec le style "focus" (bordure
       colorée) même quand elle n'a pas réellement le focus de la fenêtre (comportement natif
       Kodi : la sélection est "mémorisée" par conteneur) — ce qui donnait l'impression que
       plusieurs éléments étaient sélectionnés en même temps (chaque rangée + le bouton Retour).
       Corrigé en conditionnant les éléments de surbrillance (bordure, fond, barre d'accent) à
       `Control.HasFocus(id)` dans `Recommandations`, la grille Divertissement, la sidebar, le
       panel Jeux et la grille Catégories.
  - Validé sur le Pi réel : chargement initial limité à 30 éléments par rangée (logs du connector
    confirmant un seul appel `GET /api/plex/on-deck?limit=30&offset=30` après navigation, comptage
    passant de 30 à 60), et un seul élément mis en surbrillance à la fois.

- **Bibliothèque en grille d'affiches, alignée sur la référence Plex (2026-08-18, v0.34.0)** :
  remplace la liste texte par une vraie grille d'affiches qui s'enroule automatiquement (`panel`),
  même style de tuile que Divertissement/Recommandé (affiche + titre + année en 2 lignes),
  déclenchement du chargement incrémental sur Bas ET Droite (grille qui s'enroule, la fin du
  chargé peut être atteinte dans les deux sens). Validé par PixelCamera : grille de 30 affiches
  réelles (101 Dalmatiens, Aladdin, Alvin et les Chipmunks...) correctement rendues avec titre et
  année, correspondant fidèlement à la capture de référence fournie par l'utilisateur.

- **Total réel affiché immédiatement — plan a3f9c2e1 (2026-08-18, v0.35.0)** : demande explicite de
  l'utilisateur (fichier `a3f9c2e1-plan-pagination-akasha-os.md`) pour éviter que l'interface
  n'affiche que le nombre d'éléments chargés au lieu du total réel. Plex renvoie déjà `totalSize`
  (repli sur `size`) dans le `MediaContainer` de **chaque** réponse paginée, sans coût réseau
  supplémentaire — pas besoin d'une requête de comptage séparée comme envisagé dans le plan :
  `PagedList` (générique, réutilisé par les 3 vues) capture ce total dès la première page et
  l'affiche immédiatement, même si seuls 30 éléments sont physiquement chargés.
  - 2 jobs Talos tentés pour les parties pures/testables (tests `PagedList.total`, méthodes
    `plex_client._with_total`) — les deux ont échoué (un job a cassé un helper de test existant en
    sandbox, l'autre a expiré en boucle SEARCH/REPLACE) ; implémenté manuellement conformément à la
    politique de reprise après 3 échecs. Détail dans `docs/talos-reports.md`.
  - Validé sur le Pi réel : Bibliothèque affiche "771 resultat(s)" dès l'ouverture (Dessins
    Animées), alors que seuls 30 éléments sont chargés en mémoire à cet instant.

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
