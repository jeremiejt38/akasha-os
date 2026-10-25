# PARITY — Suivi de parité Plex TV vs Aura/Divertissement

Statuts : ✅ identique · 🟡 différence mineure · 🔴 différence majeure · ⬜ non fait

| Écran / élément | État | Référence | Akasha | Statut | Action | Preuves |
|-----------------|------|-----------|--------|--------|--------|---------|
| Accueil — hero | Livré | `accueil/`, `films_recommended_007` | Fanart + clearlogo, méta, chip âge compact, synopsis 2 lignes + `...`, cast | ✅ | — | `captures/accueil` |
| Accueil — rangées posters | Livré | `accueil/` | Pitch ~272, posters 240×360, ring détaché + zoom, barres de progression fines, badge ✓ "vu" | ✅ | — | captures |
| Accueil — onglets Pour vous / Tendances / Activité | Livré | `films_tabs_focus_002` | Pills lisibles, actif = outline, focus = pill blanche ; Tendances via `discover.provider.plex.tv/hubs/promoted` | ✅ | — | captures |
| Accueil — Activité (flux social) | Partiel | Feed d'activité des amis | Onglet « Activité » livré avec l'historique personnel (`/status/sessions/history/all`) ; les entrées amis restent indisponibles | ⬜ | API sociale GraphQL privée Plex non exposée ; limitation documentée | — |
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
| Appui long → options | Livré | Plex TV | Feuille d'options native dont les entrées dépendent du type d'élément : film/épisode → Regarder/Reprendre, Recommencer (si offset), Ouvrir, **Retirer de Continuer à regarder** (si offset), Marquer vu/non vu, Noter, Ajouter à ma liste, Infos fichier ; série/saison → Ouvrir + actions sociales ; collection → Ouvrir ; éléments de navigation (sidebar, genres) → appui long = clic. `context_sheet.py` partagé : même feuille sur les cartes filmographie (`AuraPerson`), titres similaires (`AuraRelated`), épisodes de la fiche et résultats de recherche ; lecture directe depuis une sous-fenêtre remonte le drapeau playback à la fenêtre parente | ✅ | — | audit |
| Navigation sidebar ↔ contenu | Livré | `sidebar/` | `Right` depuis la sidebar routé dynamiquement vers la surface visible de chaque vue (rangées Reco, grille 3230, cartes Catégories 6010) ; `Left` au bord gauche du contenu ouvre la sidebar ; Back à deux niveaux façon Plex : depuis le contenu → focus rail, depuis la nav → sortie | ✅ | — | audit |
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
| B1 | **Up Next** — autoplay épisode suivant avec compte à rebours Plex | Carte post-lecture `AuraUpNext.xml` (backdrop épisode, miniature, `S# - E# · série`, compte à rebours 15 s, Lire maintenant/Annuler) pilotée par le superviseur de `default.py` : détection de fin naturelle par polling position (≤3 s), lecture unitaire + file d'épisodes sérialisée dans `AuraUpNextQueue`. Durée/focus/Back paramétrés dans `up_next.py` — **à vérifier à l'écran** | implémenté, réglages à confirmer | **P1** |
| B2 | **Skip Intro / Skip Credits** — chip « Passer l'intro » pendant les marqueurs | `includeMarkers=1` → `Marker` windows persistés (`AuraPlaybackMarkers`, fetch par `item_markers` à chaque play + à chaque épisode Up Next) ; la supervision `default.py` publie `AuraActiveMarker` et spawn `RunScript(...,skipmarker)` → `AuraSkipMarker.xml` (pill bas-droite, focus, `seekTime(end)`, auto-fermeture fin de marqueur, Back = dismiss sans respawn) | implémenté, **à vérifier à l'écran** | **P1** |
| B3 | **`/:/timeline` reports** — progression envoyée au serveur pendant la lecture | `TimelineReporter` (daemon dans la supervision `default.py`) : `GET /:/timeline` toutes les 10 s (`state=playing`/`paused`, ratingKey résolu via le contexte de lecture persisté), rapport final `state=stopped`, suspendu pendant un switch qualité. **À vérifier : la reprise multi-appareils s'affiche-t-elle sur un autre client** | implémenté, **à vérifier en réel** | **P1** |
| B4 | **Filtres dynamiques serveur** | `/library/sections/{id}/filters` + `/library/sections/{id}/{filter}` → entrée « Filtres avancés… » du menu ⋯ : picker catégorie → picker valeur (booléens → Oui/Non), dict `_divert_filters` fusionné dans les params `/all`, marqué ✓ dans la liste, visible dans le compteur, reset avec les autres filtres. Plex-only (pas d'endpoint `/filters` côté connecteur) | implémenté, **à vérifier à l'écran** | P2 |
| ~~B5~~ | ~~**« Retirer de Continuer à regarder »** (appui long)~~ **LIVRÉ** | `PUT /actions/removeFromContinueWatching?ratingKey=` — entrée ajoutée à la feuille d'options pour tout item avec `viewOffset`, carte retirée de la rangée localement | ✅ endpoint confirmé (plexapi) + implémenté | — |
| B6 | **« You watched » / Activity feed propre** | `watch_history()` → `/status/sessions/history/all` (sort `viewedAt:desc`) normalisé + `viewed_at` ; troisième pill « Activité » (3072) du strip Accueil → rangée « Votre activité » synthétisée en hub ; ligne « Vous l'avez regardé le … » (7207) sur la fiche sous la rangée d'actions. Les entrées amis restent 🔴 cloud | implémenté, **à vérifier à l'écran** | P2 |
| B7 | **« More Like This »** sur les fiches | `/library/metadata/{id}/related` → hubs aplatis/dédoublonnés (`related_items`) ; entrée « Titres similaires » du panneau Plus → `AuraRelated.xml` (hero poster + rangée posters via `AuraPersonWindow`), clic → fiche. Page fixe : rangée dédiée impossible (pas de scroll Kodi), le panneau est le compromis | implémenté, **à vérifier à l'écran** | P2 |
| B8 | **Recherche enrichie** | Historique persisté (`search.recent`, 8 entrées) + entrée « Effacer l'historique » en fin de liste ; personnes (`search_people`) + **genres** (match client-side sur `section_genres`, carte → bibliothèque pré-filtrée) fusionnés dans « Tout » ; zone vide remplie de suggestions (`discover_hubs`, 12 items). `/hubs/search` non utilisé : compteurs sans items | implémenté, **à vérifier à l'écran** | P2 |
| B9 | **Extras / bandes-annonces** | `item_extras` → bouton « Bande-annonce »/« Bonus » dans la rangée d'actions de la fiche (`AuraDetailExtras`), lecture des parts extras | implémenté, **à vérifier à l'écran** | P3 |
| B10 | **Playlists locales serveur** | `playlists()`/`playlist_items_with_total` (`/playlists`, `playlistType=video`) ; pseudo-section « Playlists » ajoutée en fin de sidebar quand non vide (Plex direct uniquement, pas de proxy connecteur) ; clic → drill-in dans la grille comme les collections, items en fiches | implémenté, **à vérifier à l'écran** (serveur sans playlist pour l'instant) | P3 |
| B11 | **« Go to Show »** depuis une fiche épisode | Entrée « Aller à la série » (7208, icône tv) du panneau Plus, visible uniquement sur les épisodes → `metadata_item(grandparent_rating_key)` → fiche série en mode `show` empilée (Back revient à l'épisode) | implémenté, **à vérifier à l'écran** | P3 |
| B12 | **Sélecteur de version** (fichiers multi-part) | `versions[]` normalisé (`label` « 1080p HEVC — fichier », `part_key`) ; entrée « Lire la version… » (7209) du panneau Plus quand >1 Media → `Dialog().select` → `_start_playback` avec le part choisi. Navigation Up/Down du panneau gérée en code (entrées conditionnelles invisibles) | implémenté, **à vérifier à l'écran** | P3 |
| B13 | **UltraBlurColors** — teinte du fond de fiche | `UltraBlurColors` normalisé (`blur_colors`) → la couche de dim de la fiche (7002) est teintée via `setColorDiffuse('73'+topLeft)`, repli `7310131A` neutre | implémenté, **à vérifier à l'écran** | P3 |
| B14 | **Chapitres** | Cercle dédié dans l'OSD (`osdmenu,chapters`, visible si `Player.ChapterCount > 1`) → liste titre + timecode, chapitre courant sélectionné, `seekTime` au choix. Les marqueurs sur la seekbar et les marqueurs Plex intro/credits (autre mécanisme) restent à faire | implémenté, **à vérifier à l'écran** | P4 |
| B15 | **Continuité audio/sous-titres par série** | `AuraPlaybackItem` propage l'item courant (mise à jour à chaque avancée Up Next) ; JSON-RPC `Player.GetProperties` capture les pistes actives toutes les 10 s dans la boucle de supervision ; sélection persistée par `grandparent_rating_key` (repli `rating_key`) en setting addon `stream.pref.*` aux transitions d'épisode et en fin de session ; ré-application au démarrage par matching langue+nom (les index varient entre fichiers), sous-titres désactivés respectés | implémenté, **à vérifier à l'écran** | P4 |
| B16 | **Bibliothèques non-vidéo (Musique)** dans la sidebar | `library_sections()` (movie/show/artist) alimente la sidebar (icône `icon-music.png`) ; les onglets Recommandé/Collections/Catégories restent (Plex expose hubs/collections/genres pour la musique) ; clic artiste/album → drill-in `metadata_children` façon collections (grille albums → pistes), clic piste → lecture audio directe en arrière-plan ; résultats de recherche musicaux routés pareil | implémenté, **à vérifier à l'écran** | P4 |
| B17 | **Écran d'erreur serveur** propre | Brique d'état centrée réutilisable (`DivertState` : `offline`/`error`/`empty`/`config`) — icône + titre + message + bouton d'action contextuel (Réessayer / Effacer les filtres / Retour / Paramètres), sidebar conservée. Les rangées partiellement en échec gardent leur label inline ; l'écran global n'apparaît que si tout a échoué | implémenté, **à vérifier à l'écran** | P4 |

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

- ~~**Clavier recherche** : touches `_`, `←`, `X` en texte brut~~ → icônes `key-space`/`key-backspace`/`key-clear` (+ variants dark) overlay ; reste : touches plus petites.
- **Recherche** : pas de rail, pas de rangée « Popular Searches » dédiée (suggestions `discover_hubs` dans la grille à la place).
- **Accueil** : ~~rangée coupée net à x≈1823~~ → fade `scrim-row-right.png` sur les 5 rangées + la grille bibliothèque (à vérifier à l'écran) ; trou ~90 px entre titre et méta quand pas de clearlogo, icône « maison » fantôme près du titre (à investiguer).
- **Hero** : suit le focus (vérifié) — mais seed au premier item de la première rangée, pas un carrousel vedette comme Plex.



- **Flux « Activité » (entrées amis)** : feed social (GraphQL privé) → l'onglet montre l'historique personnel serveur (B6) ; les entrées amis ne peuvent pas être reproduites.
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
