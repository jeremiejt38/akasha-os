# PARITY — Suivi de parité Plex TV vs Aura/Divertissement

Statuts : ✅ identique · 🟡 différence mineure · 🔴 différence majeure · ⬜ non fait

| Écran / élément | État | Référence | Akasha | Statut | Action | Preuves |
|-----------------|------|-----------|--------|--------|--------|---------|
| Accueil — hero | Livré | `accueil/`, `films_recommended_007` | Fanart + clearlogo, méta, chip âge compact, synopsis 2 lignes + `...`, cast | ✅ | — | `captures/accueil` |
| Accueil — rangées posters | Livré | `accueil/` | Pitch ~272, posters 240×360, ring détaché + zoom, barres de progression fines, badge ✓ "vu" | ✅ | — | captures |
| Accueil — onglets Pour vous / Tendances / Activité | Livré | `films_tabs_focus_002` | Pills lisibles, actif = outline, focus = pill blanche ; Tendances via `discover.provider.plex.tv/hubs/promoted` | ✅ | — | captures |
| Accueil — Activité (flux social) | Non implémentable | Feed d'activité des amis | Empty state « Aucune activité d'amis à afficher » | ⬜ | API sociale GraphQL privée Plex non exposée ; limitation documentée | — |
| Sidebar rail replié | Livré | `sidebar/expanded_focus_001`, `parametres/profile_menu_003` | Pilule flottante, avatar en tête, icônes distinctes | ✅ | — | captures |
| Sidebar rail expansé | Livré | `sidebar/expanded_focus_001` | Panneau flottant arrondi + dim écran ; profil (avatar + « Akasha » + ›), Ma liste, Recherche, Accueil, header « Bibliothèques » + ligne, bibliothèques, Playlists, Plus ; focus = pill blanche | ✅ | — | captures |
| Sidebar — profil / Ma liste / Playlists | Limitation | Menu compte plex.tv, My Lists, Playlists | Items présents, clic → notification explicite | ⬜ | Fonctions cloud plex.tv non proxifiées par le connecteur privé | — |
| Sidebar — section « Sur Plex » | Limitation | `sidebar/focus_more_028` (On Plex : Live TV, Discover) | Header + items présents, clic → notification | ⬜ | Contenus cloud Plex hors connecteur privé | — |
| Sidebar — outline bibliothèque active | Livré | `parametres/settings_focus_005` | Pill outline sur la bibliothèque active (propriété `DivertActiveLibrary`) | ✅ | — | captures |
| Bibliothèque — onglets | Livré | `films_tabs_focus_002` | Recommandé / Bibliothèque / Collections / Catégories + ⋯ | ✅ | — | captures |
| Bibliothèque — grille Browse | Livré | `films_browse_focus_003` | 6 colonnes 240×360, titre+année centrés, pills sombres (`2EFFFFFF`) en flux à gauche (type, par tri, Genre, compteur en pill, ⋯), zoom 108% + ring fin externe `poster-ring-thin.png`, rail A-Z avec cercle `az-ring.png`, badge ✓ + barre de progression ambrée | ✅ | — | `grid_v5.png` |
| Bibliothèque — rail A-Z | Livré | `films_browse_focus_003` | Saut fonctionnel : lettre lue via `Container(3250).Position` (items statiques sans `<onclick>`), recherche dans les items chargés puis fetch par chunks de 500 via `PagedList` | ✅ | — | captures |
| Bibliothèque — Collections | Livré | endpoint `/library/collections` | Rangée collections + drill-down | ✅ | — | captures |
| Fiche film — hero | Livré | `fiche/film_detail_top_001` | Clearlogo/titre, méta, chips providers (IMDb/RT/TMDB + icônes), synopsis `...`, réalisateur | ✅ | — | `detail_v6.png` |
| Fiche film — actions | Livré | `fiche/film_detail_top_001`, `detail-pills/` | Cercles compacts qui s'étendent en **pill blanche labellisée** au focus (Plex : `▶ Regarder` / `↺ Reprendre …`, `Recommencer`, `Ajouter à ma liste`, `Noter`, `Marquer comme (non) vu`, `Plus`) ; icône ↺ sur reprise ; noter → dialog 1-10 → `PUT /:/rate` | ✅ | — | captures |
| Fiche — bouton « Plus » | Livré | `more_dialog_008` | Menu « Sous-titres / Ajouter à une liste / Playlist / Gérer / Infos fichier / Autres façons » ; Infos fichier = vrai dialog données média ; entrées cloud → notification explicite | ✅ | — | `more_menu.png` |
| Fiche — bord gauche → sidebar | Livré | — | `Left` depuis l'action la plus à gauche (pill Regarder, strip Série, premier item d'une rangée) ferme la fiche et ouvre la sidebar expansée | ✅ | — | `left_to_sidebar.png` |
| Fiche — clic cast | Limitation | `cast_click_009` | Plex ouvre la filmographie (social/cloud) ; Aura → notification explicite | ⬜ | API privée non proxyée | — |
| Fiche — chip âge cliquable | Limitation | `longpress_center_002` | Plex mène à Common Sense Media (cloud) ; chip passive côté Aura | ⬜ | API privée non proxyée | — |
| Fiche film — badges média | Livré | `fiche/film_detail_top_001` | Pills séparées vidéo / audio 🔊 / sous-titres ▭, alignées à droite | 🟡 | Dépend des champs `video/audio/subtitle_label` remplis par item | captures |
| Fiche — ligne « Activity by you… » | Non implémentable | Avatars + activité des amis | Absente | ⬜ | API sociale privée ; limitation documentée | — |
| Fiche — portraits du cast | Livré (partiel) | Photos réelles | Cercles propres + fallback silhouette `actor-fallback.png` quand `thumb=NONE` | 🟡 | Beaucoup d'acteurs n'ont pas de thumb côté serveur | captures |
| Fiche série — saisons | Livré | `fiche/show_detail_top_005` | Strip Série / Saison N, rangée posters de saisons, liste épisodes landscape par saison | ✅ | — | captures |
| Fiche épisode | Livré | — | Méta `S1 • E1 · date · durée`, synopsis, cast, Resume | ✅ | — | captures |
| Fiche — cercle restart ↻ | Livré | `fiche/show_detail_top_005` | Visible si l'item à lire a un offset de reprise ; `play(start_over=True)` | ✅ | — | `detail_v7.png` |
| Fiche — chip âge | Livré | `fiche/film_detail_top_001` | Format `age N+` / `Tous publics` (mapping PG-13/TV-MA/…) | ✅ | — | `detail_v7.png` |
| Fiche — scroll bas de page | Limitation | `fiche/film_scroll_2_003`, `film_scroll_3_004` | Page fixe (Cast & Crew = dernière section) | ⬜ | Sections « Ratings & Reviews » et « Discussions » = API sociale privée Plex ; pas de scroll fenêtre Kodi | — |
| Lecture | Livré | Plex player | Lecture réelle via `part_key`, reprise (viewOffset) ; les fenêtres modales Aura se ferment avant `Player.play()` puis se rouvrent sur la fiche après fin/stop — comme Plex | ✅ | — | captures |
| Appui long → options | Livré | Plex TV | Feuille d'options native dont les entrées dépendent du type d'élément : film/épisode → Regarder/Reprendre, Recommencer (si offset), Ouvrir, Marquer vu/non vu, Noter, Ajouter à ma liste, Infos fichier ; série/saison → Ouvrir + actions sociales ; collection → Ouvrir ; éléments de navigation (sidebar, genres) → appui long = clic | ✅ | — | audit |
| Navigation sidebar ↔ contenu | Livré | `sidebar/` | `Right` depuis la sidebar routé dynamiquement vers la surface visible de chaque vue (rangées Reco, grille 3230, cartes Catégories 6010) ; `Left` au bord gauche du contenu ouvre la sidebar | ✅ | — | audit |
| Recherche | Livré | `recherche/` | Grille clavier a-z + suggestions live, cartes résultats 2 colonnes | ✅ | — | captures |
| OSD vidéo | Livré | `osd/` | Minimaliste : titre, méta, horloge, seek fine avec **remplissage ambre** (`FFE5A00D`, trio left/mid/right textures), curseur blanc, temps écoulé/restant, cercles subs/settings, chevron de sortie. `DialogSeekBar.xml` passif patché en plus (sinon l'overlay Arctic se superposait : double barre + double timecode) | ✅ | — | `osd_v5.png` |
| Focus carte sélectionnée quand focus ailleurs | Livré | `films_tabs_focus_002` | Ring discret via `ListItem.IsSelected` | ✅ | — | captures |

## Backlog de parité — manques restants (audit Devin × Claude, 2026-10-22)

Audit croisé code Aura + 100 captures de référence + dumps UI Plex + revue externe Claude
(conversation `[DCb] Audit parité Plex TV vs Aura`). Chaque ligne est vérifiée sur le serveur
de production quand l'endpoint est disponible ; `⚠️` = à confirmer avant implémentation.

### Implémentable via l'API serveur locale (priorité usage salon)

| # | Manque | Endpoint / mécanisme | Vérifié | Prio |
|---|--------|----------------------|---------|------|
| B1 | **Up Next** — autoplay épisode suivant avec compte à rebours Plex | Callbacks `Player` de Kodi à la fin d'épisode + fenêtre overlay compte à rebours + `next episode` via `/library/metadata/{show}/children` | mécanisme | **P1** |
| B2 | **Skip Intro / Skip Credits** — bouton OSD pendant les marqueurs | `includeMarkers=1` sur la métadonnée → `Marker type='intro'/'credits'` (start/endTimeOffset) ; bouton OSD + `Player.seekTime` | ✅ marker `credits` confirmé sur épisode réel | **P1** |
| B3 | **`/:/timeline` reports** — progression envoyée au serveur pendant la lecture | `GET /:/timeline?ratingKey=…&time=…&state=playing` périodique ; améliore la fraîcheur de « Continuer à regarder » et le resume multi-appareils | endpoint documenté ⚠️ | **P1** |
| B4 | **Filtres dynamiques serveur** | `/library/sections/{id}/filters` → 15 filtres (genre, year, contentRating, studio, resolution…) ; un dialog générique les couvre tous. Aura : seulement Tout/Non vus/Vus + genre + tri | ✅ 15 filtres confirmés | P2 |
| B5 | **« Retirer de Continuer à regarder »** (appui long) | `PUT /actions/removeFromContinueWatching?ratingKey=` (ou `/:/unscrobble` en fallback) | ⚠️ endpoint à confirmer | P2 |
| B6 | **« You watched » / Activity feed propre** | `/status/sessions/history/all` → entrées propres du serveur (les entrées amis restent 🔴 cloud) ; ligne d'activité sur fiche + contenu réel dans l'onglet Activité | ✅ fonctionnel | P2 |
| B7 | **« More Like This »** sur les fiches | `/library/metadata/{id}/related` → hubs | ✅ hub retourné | P2 |
| B8 | **Recherche enrichie** | historique persisté + bouton « Effacer l'historique », résultats personnes/genres via `/hubs/search`, état vide avec suggestions | `/hubs/search` ⚠️ | P2 |
| B9 | **Extras / bandes-annonces** | `/library/metadata/{id}/extras` → trailer/making-of jouables (dégrade à vide si absent) | ✅ endpoint, 0 extra sur item testé | P3 |
| B10 | **Playlists locales serveur** | `/playlists` est server-local (pas cloud !) ; la sidebar peut les lister/lire | ✅ endpoint OK (vide actuellement) | P3 |
| B11 | **« Go to Show / Season »** depuis une fiche épisode | `grandparent_rating_key` déjà disponible | mécanisme | P3 |
| B12 | **Sélecteur de version** (fichiers multi-part) | plusieurs `Media`/`Part` par item → choix dans le menu Plus | mécanisme | P3 |
| B13 | **UltraBlurColors** — teinte du fond de fiche | champ `ultraBlurColors` de la métadonnée → fond coloré comme Plex au lieu du scrim générique | ⚠️ champ à confirmer | P3 |
| B14 | **Chapitres** | `Player.Chapters` Kodi / chapitres dans la métadonnée Plex → liste dans OSD ou fiche | mécanisme | P4 |
| B15 | **Continuité audio/sous-titres par série** | Plex mémorise les pistes choisies ; équivalent : mémoriser par `grandparent_rating_key` en profil addon | mécanisme local | P4 |
| B16 | **Bibliothèques non-vidéo (Musique)** dans la sidebar | section `type=artist` confirmée (id 6) ; actuellement dans le launcher, absent du rail Plex | ✅ section présente | P4 |
| B17 | **Écran d'erreur serveur** propre | Plex affiche « server unreachable » + retry ; Aura montre « erreur de chargement » par ligne | mécanisme | P4 |

### Vraies limitations (cloud / plateforme)

| # | Manque | Raison |
|---|--------|--------|
| L1 | Onglet Activité — entrées **amis**, réactions | GraphQL social privé plex.tv |
| L2 | Watchlist cloud synchronisée | metadata.provider.plex.tv (voir note : `discover.provider` déjà utilisé pour Tendances — limite possiblement côté connecteur, à trancher) |
| L3 | Multi-profils Plex Home + PIN, « Switch Profile » | Fonction compte plex.tv ; Aura mono-utilisateur |
| L4 | Live TV / chaînes « Sur Plex », Discover cloud | Contenus cloud |
| L5 | « More Ways to Watch », Watch Together | Cloud / social |
| L6 | Miniatures de seek (trickplay bif) | Kodi n'a pas de support trickplay |
| L7 | Ratings & Reviews, Discussions | API sociale privée |
| L8 | Recherche vocale | Micro télécommande = protocole BLE propriétaire (voir plan voix `c8c8548a`) |

### Écarts visuels restants (revue Claude sur captures)

- **Clavier recherche** : touches `_`, `←`, `X` en texte brut vs icônes chez Plex ; touches plus petites.
- **Recherche** : pas de rail, pas d'historique visible, pas de rangée « Popular Searches », zone droite vide avant saisie.
- **Accueil** : rangée coupée net à x≈1823 (dernier poster rogné vs fade Plex), trou ~90 px entre titre et méta quand pas de clearlogo, icône « maison » fantôme près du titre (à investiguer).
- **Hero** : suit le focus (vérifié) — mais seed au premier item de la première rangée, pas un carrousel vedette comme Plex.



- **Flux « Activité »** : feed social (GraphQL privé) → empty state explicite.
- **Ligne « Activity by you… » sur les fiches** : même raison.
- **Watchlist** : synchronisation compte Plex en ligne — notification « Watchlist indisponible » en attendant le connector.
- **Multi-utilisateurs / PIN (« Who's watching? »)** : fonction compte plex.tv — `profil/*` ; hors périmètre du connecteur privé.
- **Onboarding Plex** (`onboarding/*`) : parcours de première ouverture de l'app Plex elle-même — hors périmètre Aura.
- **Contenus « Sur Plex »** (TV en direct, Découvrir) : sources cloud Plex, notification explicite en attendant un proxy éventuel.
- **Écran « Plus »** : Plex liste des sources supplémentaires (souvent vide) ; Aura ouvre « Gérer les bibliothèques » (épinglage) — équivalent fonctionnel.
- **Portraits d'acteurs** : le serveur renvoie souvent `thumb=NONE` → fallback `actor-fallback.png`.
- **Backdrop** : couleur de fondu légèrement différente (scrim proche mais pas pixel-perfect).
- **Typographie** : Aura utilise `RobotoCondensed` (skin) vs le sans-serif standard de Plex — écart mineur, un changement de police casserait les métriques de toute la skin.
- **Format des timecodes OSD** : `hh:mm:ss` via infolabels Kodi (`Player.Time`) vs `h:mm` chez Plex — pas de formatage disponible côté skin.
- **`ReloadSkin` pendant une lecture active** : peut faire planter Kodi (SIGSEGV observé en test au teardown du player) — opération dev uniquement, pas un chemin utilisateur.
