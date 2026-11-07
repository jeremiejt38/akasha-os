# PLAN-90bcc434 — Suivi global des exigences Akasha OS

> Cahier des charges **consolidé** : il agrège tout ce qui a été demandé dans les
> trois conversations Devin « Akasha OS » (origine août 2026, reprise parité
> 24 oct, conversation courante depuis le 31 oct) et dans les cahiers des
> charges déposés dans `~/Téléchargements`. Chaque exigence porte un statut.
>
> **Légende** : ⬜ à faire · 🔨 implémenté (code écrit, pas forcément mergé) ·
> 🧪 testé (tests unitaires verts) · ✅ déployé (release installée sur le Pi,
> vérifiée à l'écran ou en live) · ⛔ bloqué (raison externe documentée) ·
> 🚫 abandonné / hors périmètre (raison consignée).
>
> Version de référence du déploiement : **v0.78.5** (2026-11-07). 492 tests verts.

## A. Socle Aura & architecture (conversation 1 — août 2026)

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| A1 | Addon Kodi « le plus fidèle possible à Plex » remplaçant PM4K comme point d'entrée | conv1 | ✅ | `script.akasha.aura` — accueil par défaut depuis v0.18.0 |
| A2 | 3 onglets globaux (Divertissement / Jeux / Apps) + sous-onglets | conv1 | ✅ | modules exclusifs + strips contextuels |
| A3 | Bouton/icône Paramètres en haut à droite | conv1 | ✅ | menu Paramètres contextuel (B8) |
| A4 | Titres d'onglets remplacés par des icônes | conv1 | ✅ | pills/icônes |
| A5 | Sidebar visible à ~5-10 %, ouverture totale au bord gauche, rétractation en sortant | conv1 | ✅ | rail replié + panneau flottant (v0.32→) |
| A6 | Chargement incrémental (page ~30, +15 en approchant la fin) — rangées et bibliothèque | conv1 | ✅ | `paged_list.PagedList` (v0.33.x) |
| A7 | Cache local affiches + métadonnées sur le Pi | conv1 | ✅ | `local_cache` sqlite + `Textures13.db` |
| A8 | Un seul élément en surbrillance à la fois | conv1 | ✅ | layouts conditionnés `HasFocus` |
| A9 | Veille uniquement manuelle ou après inactivité **en mode Ambiant** ; Ambiant uniquement si aucune app au premier plan | conv1 | ✅ | `is_foreground_app_active` (fix 2026-08-19) |
| A10 | `akasha-os-connector` (cache + auth multi-utilisateurs, images tokenisées côté serveur) | conv1 + brief | ✅ | container Unraid `connector.akasha.ing` + `connector_client.py` (v0.27+) |
| A11 | Outil de capture d'écran du Pi | conv1 | ✅ | PixelCamera `:8088` |
| A12 | Utiliser Talos impérativement pour le chantier | conv1 | 🚫 | Talos en maintenance (règle globale) — travail fait par Devin directement |

## B. Divertissement — navigation & structure (cahiers + conversations)

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| B1 | Sidebar bibliothèques dynamique (logo, Accueil, bibliothèques ordonnées, séparateur, watchlist, accès paramètres) | interface-plex Ph1, 780ecf80 Ph2 | ✅ | rail + bibliothèques + « Sur Plex » ; watchlist cloud = limitation (C16) |
| B2 | Onglets Recommandé / Bibliothèque / Collections / Catégories | interface-plex Ph2, 780ecf80 Ph5-6 | ✅ | pill Collections conditionnelle |
| B3 | Hero banner (fanart + clearlogo + méta + synopsis + cast) | interface-plex Ph2.4 | ✅ | champ `UltraBlurColors` bilinéaire |
| B4 | Menu global auto-masqué : swap exclusif barre principale ↔ menu secondaire | interface-plex Ph3, fcdf2235 (conv3) | ✅ | swap exclusif (v0.77.0, #293) |
| B5 | Grille bibliothèque posters + barre d'outils (tri/filtre/genre/compteur/⋯) | 780ecf80 Ph5, f41ce1ad | ✅ | grille 6 col. + pills (v0.42-0.44) |
| B6 | Correctifs : superposition bandeau/sidebar, galerie verticale, rangées vides, catégories en page, menus A/B, bug « Haut » | c33b666e, 9ae452be, f41ce1ad PhB | ✅ | v0.43.x-0.44.x |
| B7 | Regroupement des icônes du menu principal | c7f0636a | ✅ | v0.46.1 |
| B8 | Recherche unifiée + menu Paramètres (Kodi/LibreELEC/Akasha/veille/redémarrer 2 choix/arrêt confirmé) + expansion/collapse modules | 04bda1b4 | ✅ | v0.43.0 |
| B9 | Pagination + total réel immédiat | a3f9c2e1 | ✅ | v0.35.0 (`totalSize`) |
| B10 | Catégories : grille de genres → bibliothèque pré-filtrée | interface-plex Ph2.3 | ✅ | `AuraGenres` (v0.30/31) |
| B11 | Bibliothèques non-vidéo (musique) dans la sidebar + lecture audio | PARITY B16 | ✅ | v0.69.x |
| B12 | Navigation Saisons→Épisodes via le Connector (endpoint metadata children) | fiche Atlas 2026-08-29 | ⛔ | implémenté + tests verts ; validation live bloquée — session Connector expirée, réauthentification Jérémie requise |
| B13 | Bug backend `show_seasons` : a retourné une saison d'un autre show (« dropped 1 foreign seasons ») | HANDOFF TODO #2 | ✅ | audit 2026-11-07 : clés de cache correctement scopées par `rating_key` côté connector ET Aura — pas de défaut de code ; cause probable = données Plex polluées à l'ère DB `malformed` (F14) ; garde `parent_rating_key` conservée |
| B14 | Hub `style=hero` (`home.continue` sur `/hubs/promoted`) : Plex rend des cartes paysage 16:9 avec barre de progression, Aura une rangée posters | plex-parity HANDOFF | ⬜ | conversion à faire — slots paysage ou itemlayout dédié (viewport coulissant complique le binding) |

## C. Parité visuelle Plex (audit continu — 2e7c9375, b4e8f21a, PARITY.md)

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| C1 | Boucle audit→fix→test→release→déploy jusqu'à quasi-identité, Claude en appui | conv2/3 | ✅ | `PARITY.md` quasi entièrement vert (v0.58→v0.73) |
| C2 | Accueil : hero, rangées, pills Pour vous/Tendances/Activité | PARITY | ✅ | captures indexées |
| C3 | Sidebar rail + panneau profil 7 entrées Plex + pile de sheets | PARITY | ✅ | réplique non dimmée `AuraProfileMenu` |
| C4 | Fiche film/série/saison/épisode/personne : actions pill, Plus (pistes, extras, versions, similar), cast, activité avatars | PARITY | ✅ | v0.69.x-0.73.x |
| C5 | OSD Plex complet (queue, chapitres, skip marker, Up Next, tags qualité, timecodes, BIF conditionnelles) | PARITY + conv3 | ✅ | chaîne vérifiée live (Mercredi S2E3) |
| C6 | Recherche Plex (clavier, historique, hub search, rail 7 pills, cartes 2 colonnes) | PARITY B8 | ✅ | v0.69.x-0.73.x |
| C7 | FAST Live TV 238 chaînes + EPG now/next + lecture stable | PARITY L4 | ✅ | proxy SSAI + soft decode + watchdog |
| C8 | Multi-profils Plex Home + pavé PIN | PARITY L3 | ✅ | `AuraWhoWatching`/`AuraPinEntry` |
| C9 | Playlists serveur (pseudo-section sidebar) | PARITY B10 | ✅ | drill-in grille |
| C10 | Timeline reports `/:/timeline` (reprise serveur) | PARITY B3 | ✅ | vérifié `/status/sessions` |
| C11 | Continuité audio/sous-titres par série | PARITY B15 | ✅ | `stream.pref.*` vérifié réel |
| C12 | Filtres dynamiques serveur | PARITY B4 | ✅ | menu ⋯ « Filtres avancés » |
| C13 | Placeholders, focus-ring lissé, chips notes/classification Plex, horloge centrée, badge ✓, barres de progression | conv3 + PARITY | ✅ | v0.73.x-0.76.x |
| C14 | Coins arrondis réellement transparents | conv2 | ✅ | `art_proxy.py` PNG alpha (v0.70) |
| C15 | Activité **amis**, réactions, Ratings & Reviews, Discussions | PARITY L1 | ⛔ | API sociale GraphQL privée Plex |
| C16 | Ma liste / Playlists cloud, watchlist synchronisée | PARITY L2 | ⛔ | metadata.provider.plex.tv non proxyé |
| C17 | Chip âge cliquable → Common Sense Media ; « Add user » | PARITY | ⛔ | fonctions cloud plex.tv |
| C18 | Suffixe « · Akasha » sur lignes méta : garder ou masquer ? | PARITY reste ouvert | ✅ | réglable : `aura.server_suffix` (défaut ON = comportement actuel) dans Paramètres → Apparence |
| C19 | Icône historique (disque vs flèche-horloge) + dégradé/horloge hero | PARITY reste ouvert | ⬜ | cosmétique, en attente référence Plex même item |
| C20 | Cartes « Ajoutés récemment » hybrides (fiche série à mauvais posters) | PARITY vigilance | ⬜ | observé une fois, non reproduit — instrumentation prête à redéployer |
| C21 | Resserrement dynamique des icônes voisines quand une pill du menu principal s'étend | aura decisions | ⬜ | espacement fixe actuel ; effet référence non reproduit |
| C22 | États vides/erreur sur device : revérifier chaque surface en conditions réelles | HANDOFF TODO #3 | ⬜ | recette parité résiduelle |
| C23 | Appuis longs restants à vérifier sur les surfaces parcourues | HANDOFF TODO #3 | ⬜ | recette parité résiduelle |
| C24 | Ghost icon près du hero (non identifié) + confirmer le fix du trou ~90 px titre/méta sans clearlogo | plex-parity HANDOFF | ⬜ | à confirmer à l'écran |

## D. Navigation & animation (conv3 — v0.75→v0.78.5)

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| D1 | Rail A-Z moderne : grossissement lettre, blancheur, animation de défilement | conv3 (95034109) | ✅ | v0.75.0 (#284) + vérité serveur `firstCharacter` |
| D2 | Skeletons fidèles à la géométrie réelle des cartes (poster, titre, année) | conv3 | ✅ | v0.76.x (#287, #290) |
| D3 | Barre progression « vue » : épaisseur/alignement corrigées, puis grossie + scale au focus | conv3 | ✅ | v0.76.2 + v0.78.4 (6 px, zoom suivi) |
| D4 | Scroll horizontal/vertical : jamais de wrap (reste au bord) | conv3 | ✅ | `fixedlist` ×13 XML (v0.78.4) |
| D5 | Hold-Left au bord gauche : sidebar uniquement après relâchement + pression fraîche | conv3 | ✅ | guards `RECO_GUARD_IDS` + timer (v0.78.4) |
| D6 | Préchargement des cartes suivantes en scroll horizontal | conv3 | ✅ | `_prewarm_reco_items` (v0.78.3) |
| D7 | Animation rangée→rangée : plus de void multi-hop, rangée sortante dissoute, hero synchronisé, peek opaque, ~280 ms | conv3 + ANIM.md R1-R5 | ✅ | `AuraFocusSlot` + rebind 2 phases + dissolve +472 (v0.78.5) |
| D8 | Fenêtre sombre résiduelle sous rafale extrême (4 hops) | PLAN-a3f91d2c réserve | ⬜ | transition masquée, pas un void — réglage fin possible |
| D9 | Bug scroll bibliothèque : remontée en haut + crash/redémarrage | conv3 (aeabdcd1) | ✅ | v0.75.2 (#282) + v0.76.0 (#300) |
| D10 | Zoom 104 % de la carte focusée | ANIM.md | ✅ | extension Aura assumée (Plex = ring sans zoom) |
| D11 | Bibliothèque : chargement lent au défilement (Films) | conv3 | ✅ | art-proxy warm + rendu ÷2 (v0.75.x) + préchauffe (v0.78.3) |

## E. Store / Apps / Jeux

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| E1 | `akasha-os-store` : repo + manifest versionné + install depuis Aura | f4e069bb | ✅ | repo + `store_client` + `InstallAddon` |
| E2 | Refonte visuelle façon store TV (Play Store) : fond sombre, pills catégories, cartes | conv3 + f4e069bb | ✅ | v0.74-0.75 (#272, #274) |
| E3 | Cartes paysage arrondies, titre sous l'image, **overview avant install** (métadonnées + description) | conv3 | ✅ | `AuraStore` landscape + sheet overview (#274) |
| E4 | Logos officiels + élargissement du catalogue (~100 propositions) | conv3 | ✅ | `tools/apps_seed.py`, `fetch_icons.py` ; ADN/Crunchyroll 403 documenté |
| E5 | Page « Mes apps installées » : cartes icônes, badges épinglé/source, strip d'actions | conv3 | ✅ | `AuraApp` (v0.74+) |
| E6 | Onglet Jeux : sous-onglets pills, posters arrondis, dédup raccourcis, états vides | conv3 | ✅ | v0.74+ |
| E7 | Installs kodi-repo réellement fonctionnels (+ modal info) | constat session | ✅ | v0.75.1 (#276) ; segfault `AddonInformation` documenté |
| E8 | Choix cloud gaming du Quick Start consommé par le module Jeux | quickstart decisions | ⬜ | préférence sauvegardée, non câblée |
| E9 | Grille posters Steam/Sunshine réelle | PARITY store | ⬜ | services non configurés sur le Pi — état « non configuré » propre |
| E10 | « Mes Apps » : filtre strict « installées via le Store » | aura decisions | ✅ | réglable : `apps.store_only` (défaut OFF = inventaire complet préservé) dans Paramètres → Apparence |
| E11 | Recherche unifiée : couvrir aussi le catalogue Steam/Sunshine | aura decisions | ⬜ | périmètre actuel = contenu Plex seul |
| E12 | Exécution auto `script`/`external-app` du manifest Store | aura decisions | 🚫 | volontairement non automatisé (sécurité) ; fiche info uniquement |
| E13 | Connectivité Pi → NZXT/Sunshine : `192.168.1.100` = « No route to host », Sunshine OK via VPN `10.20.0.4` | fiche Atlas v0.26.1 | ⬜ | diagnostic 2026-11-07 : Pi en `192.168.3.x` — NZXT LAN **et** VPN `10.20.0.4` tous deux injoignables ; Plex passe par `plex.akasha.ing`. Reste : hôte Sunshine configurable + repli (L5) |

## F. Paramètres, assistant, système d'exploitation

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| F1 | Paramètres unifiés (11 catégories + filet « Avancé ») | a5a87f03 | ✅ | v0.45.0/0.46.0 — audit par catégorie |
| F2 | Quick Start : wizard 10 étapes, marqueur, relance manuelle, progression persistée | 3aba4284 | ✅ | v0.46.x — suite tests + écran validé |
| F2a | — Étape son : fichier audio de test bundlé | quickstart decisions | ✅ | déjà implémenté : `notify.wav` bundlé Kodi (`resource.uisounds.kodi`) joué à l'étape Affichage/son |
| F2b | — Étape réseau : validation avec un vrai réseau | quickstart decisions | ⬜ | à valider en conditions réelles |
| F3 | Akasha OS épuré : services réseau/addons stock inutilisés désactivés | conv3 | ✅ | services coupés v0.78.0/1 ; désactivation des addons stock = impossible en amont (documenté #298) |
| F4 | Ventilateur Argon : pas de déclenchements brefs, seuil repoussé, courbe progressive | conv2/3 | ✅ | anti-chatter : 55 °C soutenu 16 s, hystérésis 5 °C, run min 60 s, 100 % ≥70 °C (v0.73.x) |
| F5 | Governor : réactif sans ramp perceptible | conv3 | ✅ | `performance` permanent — divergence justifiée (ondemand = latence au 1er input) |
| F6 | Sauvegarde SD : rien perdu si la carte meurt | conv2 | ✅ | `backup.timer` quotidien 05:30 + off-site (journal) |
| F7 | Audit firmware/drivers + état SD | conv2 | ✅ | journal « pi firmware audit, sd health check » |
| F8 | Unraid exclu des IP bannies | conv2 | ✅ | allowlists CrowdSec lan-rfc1918 + unraid |
| F9 | Audio/vidéo jamais audible hors lecture (menus, chargements) | conv2 | ✅ | watchdog : lecteur sans fenêtre 12005 stoppé ~2 s |
| F10 | HDMI-CEC neutralisé | demande session | ✅ | flag `CEC_DISABLED` (v0.49.5) |
| F11 | Back à la racine = sortie/confirmation façon Plex ? | HANDOFF TODO | ✅ | option `aura.back_root_confirm` (défaut OFF = 2 niveaux Plex-like actuel) ; ON = dialogue « Quitter Akasha Aura ? » |
| F12 | Mémoire textures sur sessions longues | HANDOFF TODO | ✅ | rapport 2026-11-07 : kodi_mem stable ~1160 MB sur 16,6 h réelles — pas de fuite |
| F13 | Rapport perf-analyzer après heures d'usage réel | HANDOFF TODO | ✅ | 5976 échantillons 2026-11-06→07 : 0 anomalie, 0 erreur kodi.log, load ~0,5, temp ~46 °C |
| F14 | DB Plex `malformed` sur le serveur | HANDOFF constat | ⛔ | REINDEX/dump-restore = fenêtre maintenance prod à valider |
| F15 | Ménage : stash `wip-fix-aura-interruptions`, ~20 branches stale | HANDOFF TODO | ✅ | 166 branches distantes + 8 locales supprimées (toutes mergées via PR, patches exportés) ; stash déjà vide ; conservées : `feature/voice-commands` (en pause), `docs/handoff-0694` (jamais mergée) |
| F16 | `HEAD /api/plex/image` → 405 (nettoyage) | roadmap note | ✅ | résolu — HEAD supporté sans re-télécharger l'image (fiche connector) |
| F17 | Compteur « 771 » section / taille hub non honorée | roadmap note | ✅ | pagination `X-Plex-Container-Start` (v0.33) |
| F18 | Validation physique manette Xbox Wireless + télécommande IR + mapping Home/Menu de la télécommande BT en conditions réelles | decisions.md + fiche Atlas | ⬜ | matériel requis, jamais testé (accès distant seul) |
| F19 | Déclenchement réel « Mise en veille » / « Arrêt système » | decisions.md | ⬜ | code en place, jamais exécuté en test réel par Jérémie |
| F20 | Addon Jellyfin installé mais désactivé (token perdu lors d'un wipe) | audit-2026-10 | ⬜ | une connexion interactive depuis l'UI, puis réactivation |
| F21 | PM4K conservé comme échappatoire développeur | audit-2026-10 | ✅ | Guide ▸ Options développeurs ▸ « Lancer PM4K » |
| F22 | Panneau « Comptes » centralisé : état connecté/non connecté par service + bouton Configurer → écran natif de l'addon | settings decisions (point ouvert) | ✅ | ligne « Connector Akasha OS » ajoutée (Connecté/Non configuré + Configurer → réglages natifs) ; Plex/Steam/Sunshine déjà routés |
| F23 | Filet de déploiement sans Ethernet : watchdog Wi-Fi de secours | v0.18.1 + audit-2026-10 | ✅ | `wifi-watchdog` réécrit network-agnostic (profil Favorite connman), activé, test contrôlé validé |
| F24 | `ActivateWindow(peripheralsettings)` → SIGSEGV moteur Kodi (upstream) | settings decisions | ⛔ | bug Kodi/LibreELEC confirmé hors code Akasha ; entrée retirée de Manettes & Télécommandes |
| F25 | Fragilité Pi↔Unraid/Plex via NAT USB-Ethernet du laptop (`10.99.0.1/24`) : « No route to host » vers `192.168.100.133` quand l'adaptateur perd son lien | audit-2026-10 | ⬜ | diagnostic 2026-11-07 : non bloquant — Aura/Connector passent par Cloudflare (`*.akasha.ing`), pas de dépendance au LAN `192.168.100.x` depuis le Pi `192.168.3.x` |
| F26 | Épingler le Wi-Fi 5 GHz Freebox sur un canal non-DFS (36-48) | journal migration Freebox | ⬜ | action manuelle dans `mafreebox.freebox.fr` — réduit les décrochages Wi-Fi du Pi |

## G. Télécommande & commandes vocales

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| G1 | Télécommande Bluetooth (Fire TV) appairée, boutons fonctionnels | dd440e2e | ✅ | BLE HID, event6/7 |
| G2 | App switcher visuel (double Home) | dd440e2e | ✅ | `AuraSwitcher.xml` |
| G3 | Batterie + destination volume dans Paramètres + alerte batterie <15 % | dd440e2e §4 | ✅ | Manettes & Télécommandes + `BatteryAlertTracker` (notification seuil configurable) |
| G4 | Bouton assistant vocal (flux micro) | dd440e2e §2 | ⛔ | protocole Alexa propriétaire (btmon vérifié) |
| G5 | « Retrouver ma télécommande » (buzzer) | dd440e2e §3 | ⛔ | uniquement Alexa Voice Remote Pro + cloud |
| G6 | Socle `script.akasha.voice` : 60+ commandes FR/EN → builtins Kodi | c8c8548a | ✅ | mergé, 15 tests, CI matrix |
| G7 | Intégration STT réelle + commandes matérielles | c8c8548a | ⛔ | en pause (décision matérielle — fiche Atlas) |
| G8 | Durcissement télécommande : double-appui panneau paramètres, long-Home→OSD, filtrage appuis parasites | remote decisions | ✅ | v0.6x — récepteur IR GPIO23 désactivé |
| G9 | Boutons services streaming (Netflix/Prime/Amazon) → no-op, keycodes non confirmés | remote decisions « reste à faire » | ⬜ | à vérifier avec Jérémie — ce modèle n'a peut-être pas de boutons dédiés |
| G10 | Blaster IR dédié sur GPIO (LIRC) pour contrôle IR TV + volume IR | remote decisions | 🚫 | piste documentée, non retenue dans le périmètre actuel |
| G11 | Fallback LED de la télécommande comme retour vocal (plan §3) | remote decisions | ⛔ | dépend de G4/G7 (bloqués — chantier vocal en pause) |

## H. Mode Ambiant & veille

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| H1 | Diaporama/horloge/météo anti-marquage + transfert veille CEC | spec ambient v0.12 | ✅ | `script.akasha.ambient` + service (bug screensaver Kodi contourné) |
| H2 | Pack photos plein écran pré-downscalé | ambient roadmap | ✅ | 13 photos (v0.17+) |
| H3 | Crédit photo, fonds non-16:9, appariement portrait, luminosité nocturne | HANDOFF reculés | ⬜ | reportés volontairement |
| H4 | Synchronisation multi-écrans | ambient roadmap | 🚫 | hors périmètre mono-appareil |
| H5 | Effet Ken Burns (zoom/pan lents) sur images fixes | ambient roadmap « après v0.20.x » | ✅ | v0.58.0 — 2 slots `image` + `ambient.kb{slot}`, 4 variantes, `PhotoCycler` sans répétition dos-à-dos |
| H6 | Activation programmée par plage horaire (thème jour/nuit) | ambient roadmap | ⬜ | non planifié |
| H7 | Détection de présence (capteur/caméra, traitement local uniquement) | ambient roadmap | ⬜ | non planifié — matériel requis |
| H8 | Sources de contenu réseau (NAS, cloud personnel) | ambient roadmap | ⬜ | non planifié — dossier local seul aujourd'hui |
| H9 | Modules complémentaires : musique, calendrier, actualités, domotique | ambient roadmap | ⬜ | non planifié |
| H10 | Mode confidentialité « Ambiant public » (masquage photos personnelles/calendrier) | ambient roadmap | ⬜ | non planifié |
| H11 | Génération procédurale de fonds (particules, gradients) | ambient roadmap | ⬜ | non planifié |
| H12 | Limitation mode vidéo : masque horloge/météo | ambient decisions | ✅ | résolu — pack photos par défaut, vidéo = choix manuel |
| H13 | Géolocalisation automatique pour la météo | ambient decisions | ⬜ | reportée (complexité + confidentialité) — ville/coords manuelles dans les réglages |

## I. Plateforme & satellites

| # | Exigence | Source | Statut | Preuve / note |
|---|----------|--------|--------|----------------|
| I1 | Monitoring du pipeline média (Seerr → Radarr/Sonarr → Prowlarr → download → import → Plex) | 7f3a9c2e | 🚫 | **double emploi avec Sentarr** (V1+V2 déployées en staging : Plex + *arr + downloaders + timelines) ; un volet lecture-seule dans Aura resterait un chantier à part si voulu |
| I2 | Port multi-plateforme (CoreELEC & autres devices) | akasha-os-plan | ⛔ | `akasha-os-coreelec` créé vide, projet archivé (ariane) |
| I3 | Émulateur Android TV Plex pour comparaison | 2e7c9375 | ✅ | AVD `.Akasha` + `scripts/emu.sh` + screenrecord |
| I4 | Boucle de travail avec Claude (`claude-bridge`) | conv2/3 | ✅ | utilisée (design void, audits parité) |
| I5 | Outil `rea` dans /opt (aide reverse-engineering) | conv2 | ✅ | installé et utilisé à l'époque ; retiré depuis (outil ponctuel) |
| I6 | Modale de partage Akasha (site akasha.ing) | 459c8226/be6214fe | 🚫 | projet `akasha-website`, hors périmètre akasha-os |

## Synthèse

- **✅ Déployé** : l'essentiel du cahier — socle Aura, Divertissement complet,
  parité Plex quasi totale, Store/Apps/Jeux refondus, paramètres, Quick Start,
  navigation/animation v0.78.5.
- **⬜ À faire** (36 items) : reculés Ambiant (H3)
  + extensions non planifiées (H6-H11, H13), hub hero paysage (B14),
  bug `show_seasons` (B13), routage Sunshine/NAT (E13, F25, F26),
  E8-E11, F2a/F2b, F11-F13, F15, F18-F20, F22, G9, résidu anim D8,
  recettes parité résiduelles (C20-C24), arbitrages C18/C19/C21.
- **⛔ Bloqués documentés** (11) : APIs cloud Plex privées (C15-C17), vocal/buzzer
  télécommande (G4-G5), STT (G7), CoreELEC (I2), DB Plex (F14),
  réauth Connector (B12), crash Kodi upstream (F24), LED retour vocal (G11).
- **🚫 Hors périmètre** (6) : Talos (maintenance), multi-écrans (H4), exécution
  auto de scripts du Store (E12), modale site web (I6), blaster IR GPIO (G10),
  pipeline média → Sentarr (I1).

### Prochaines priorités suggérées

1. F11 + F13 (petits, vérifiables) puis D8 (réglage fin de la transition).
2. H3 (pack Ambiant — items précis et indépendants).
3. I1 pipeline média (seul vrai chantier fonctionnel jamais commencé).
4. Arbitrages à trancher par Jérémie : C18 (« · Akasha »), E10 (filtre
   Store strict), F11 (Back racine).
