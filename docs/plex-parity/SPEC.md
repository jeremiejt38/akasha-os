# SPEC — Reproduction Plex Android TV dans Aura (onglet Divertissement)

Spécification vivante, alimentée par l'observation de la référence (Plex v2026.20.0
sur émulateur Google TV API 36, 1920x1080, profil `.Akasha`, serveur `Akasha`).

## Portée validée avec Jérémie (2026-10-22)

- Parité Plex **uniquement dans l'onglet Divertissement** d'Aura.
- Les onglets Jeux/App, la barre du haut et la coquille Aura restent intacts.
- Référence = l'appli Plex réelle dans l'émulateur, jamais la mémoire.

## Note "camera" (écart au cahier, acté 2026-10-22)

Le cahier prévoyait un téléphone Pixel filmant la TV. L'outil a été remplacé
amont par PixelCamera v2 : `kodi-send TakeScreenshot` sur le Pi exposé en HTTP
(`:8088/frame.jpg`). Conséquence : `akasha-camera/` et `akasha-direct/` proviennent
de la même source numérique — pas de calibration optique ni de rectification.
La validation "réalité physique" devient "réalité du rendu Kodi à 1080p".

## Harnais

- `scripts/emu.sh` : captures + touches D-pad + uiautomator + screenrecord sur `emulator-5554`.
- `scripts/pi.sh` : capture via `http://192.168.3.77:8088/frame.jpg`, navigation via
  `kodi-send` en SSH sur `root@192.168.3.77`.
- `scripts/compare.py` : diff pixel + image de diff amplifiée.

---

## Thème global (mesuré)

| Élément | Valeur mesurée | Source |
|---------|---------------|--------|
| Fond sidebar/rail | `#0F0F0F` | sidebar/expanded_focus_001 |
| Pill focus sidebar | `#E9E9E9` (blanc), texte noir | sidebar/expanded_focus_001 |
| Clavier recherche (touche) | `#212121` | recherche/search_open_003 |
| Panneau recherche | `#262626` | recherche/search_open_003 |
| Barre bas lecteur | `#050404` quasi-noir | lecteur/osd_down_002 |
| Accent Plex (progress) | orange `#E5A00D`-like (barre de progression des posters) | accueil/first_load_001 |
| Focus carte (rangée) | bord blanc arrondi ~8px, épaisseur ~4-6px | accueil/first_load_001 |

## Accueil — "For You" (mesures exactes, XML + PNG)

- **Barre du haut** : onglets `For You`(pill sombre sélectionné) `Trending` `Activity`
  — y=40..88 (48px haut). Horloge en haut à droite `[1708,50]-[1807,78]` (99x28).
- **Hero** : backdrop plein écran assombri à gauche, gradient depuis `#0F272A`-ish.
  - Titre/logo : `[127,240]` hauteur 48px (grand titre ou logo image)
  - Ligne méta : `[127,302]` h=24px — `S18 • E6`, date, durée `21m`, badge note `10`
  - Synopsis : `[127,352]-[947,416]` 820x64 (3 lignes max, tronqué)
  - Cast : `[127,428]` h=28 — noms séparés par virgules
- **Rangées** :
  - Titre de rangée : `[127,504]-[*,552]` 48px + `· Akasha` (serveur)
  - Cartes posters : **240x360**, pas horizontal **272px** (gap 32px), y=568..928
  - Rangée suivante : titre à y=976
  - Barre de progression orange en bas du poster pour les "Continue Watching"
- **Rail gauche** (replié) : icônes ~x=50 — avatar, loupe, maison, hamburger

## Sidebar dépliée (mesures)

- Overlay sombre `#0F0F0F`, largeur items **320px** (x=66..386)
- Profil en haut : `.Akasha` + chevron, 72px haut
- Items : **64px** de haut, texte à x=130 (icône 24px à x~90)
- Ordre : Profil · My Lists · Search · Home · [Libraries] Films, Séries TV,
  Dessins Animées, Cartoons, Documentaires, Spectacles, Animés, Docu-Séries,
  Emissions TV, Playlists, More · [On Plex] Live TV, Discover, …
- Focus : pill blanc plein sur l'item

## Bibliothèque — onglets (mesures)

- Onglets : `Recommended` `Browse` `Collections` `Categories` — y=40..88
- **Recommended** = hero + rangées (même pattern que l'accueil)
- **Browse** = grille :
  - Pills filtres : `All`/`Movies`/`by Title`/`N Items`/`Clear`/`⋮` — y=132..180 (48px)
  - Grille : cartes **240x360** + titre (32px) + année (24px), pitch x=283px,
    première rangée y=204
  - Badge `Watched` (✓) coin haut-droit du poster : 40x40
  - Rail alphabétique A-Z à droite (x≈1500+)
- **Categories** = grille de cartes genre colorées (4/rangée, ~310x190, artwork
  estompé + nom centré) → clic = Browse filtré sur ce genre
- **Collections** = idem grille de collections

## Fiche film (mesures)

- Titre : `[128,232]` h=56
- Méta : `[128,302]` h=24 — année, durée, genres, badge âge
- Badges notes : y=340..380 (40px pill) — `age 14+`, IMDb `6.0`, RT `37%`, aud `50%`, TMDB `6.5`
- Synopsis : `[128,404]-[956,500]` 828x96 (3 lignes)
- `Directed by X` : y=512, h=28
- Boutons action : y=564..628 (64px h) — `Watch` (139px, pill accent), puis
  icônes rondes 64x64 : watchlist, vu, check, ⋯, `Rate & Review`
- `Activity by …` : y=652, avatars ronds
- Badges média (droite) : `4K HDR10 (HEVC Main 10)` `French (AAC 5.1)`
  `French Forced (SRT)` — y=674..706, texte 24-32px
- Cast & Crew : cercles **240x240** + nom+role 2 lignes, y=828..1068
- Puis : Ratings & Reviews (cartes), Discussions

## Fiche série

- Même structure + rangée **"N Seasons"** (posters 240x360 avec ✓ si saison vue)
- Onglets en haut : `Show`, `Season 1`..`Season N`
- Bouton principal = `Resume S6 E7 • 24m left`
- Épisodes : cartes paysages (thumb 16:9) avec titre + durée + synopsis court

## Recherche (mesures)

- Clavier à l'écran : grille 6 col (a-f / g-l / m-r / s-x / y z 1 2 3 4 / 5-0)
  + rangée espace/⌫/effacer — touches `#212121`
- Icônes micro + filtre en haut ; header « You can search titles, people, genres… »
- Historique sous le clavier (chips), grille "Popular Searches" à droite
- Résultats en direct : pills filtre `All/Movies/TV/Music/Live TV/Cast & Crew/Services`,
  suggestions à gauche, cartes résultats (poster+titre+année+type+serveur) à droite

## Lecteur (OSD)

- Haut-gauche : titre épisode/film + ligne `S1 • E1 • série • 43 minutes • HD`
- Haut-droite : horloge
- Bas : barre de progression (orange), temps écoulé / restant, bouton play,
  icônes sous-titres + réglages en bas à droite, chevron-vers-le-bas pour plus

## États particuliers

- Vide : `No Results` / `Your library is empty` + bouton Back (navigation/more_screen)
- Profil : menu Switch Profile / Profile / Notifications / Friends / Services /
  Server / Settings (parametres/sidebar_top_004)

## Navigation D-pad (observé)

- Rail replié : gauche depuis le 1er item → rail s'ouvre en overlay
- Dans la sidebar : haut/bas circule entre les items, droite = contenu
- BACK : remonte d'un niveau (depuis sidebar ouverte → grille ; depuis fiche → liste)
- Le focus carte = bord blanc + léger zoom, le fond hero change par item focus
