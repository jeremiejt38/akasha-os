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
| Sidebar — profil | Livré | `parametres/sidebar_top_004` (panneau Switch Profile/Profile/Notifications/Friends/Services/Server/Settings) | Panneau latéral `AuraProfileMenu.xml` (ancré gauche) avec les **7 lignes Plex dans l'ordre** : Changer de profil, Profil, Notifications, Amis, Services, Serveur, Paramètres — icônes dédiées ; les 4 entrées cloud affichent une notification stub, Profil/Serveur/Paramètres gardent leurs actions | ✅ | — | captures |
| Sidebar — Ma liste / Playlists | Limitation | My Lists, Playlists | Items présents, clic → notification explicite | ⬜ | Fonctions cloud plex.tv non proxifiées par le connecteur privé | — |
| Sidebar — section « Sur Plex » | Livré | `sidebar/focus_more_028`, `scroll_down_*` (On Plex : Live TV, Discover) | Divider « Sur Plex » + items « TV en direct » (icône antenne) et « Découvrir » (boussole) sous le rail bibliothèques ; TV en direct → grille des **238 chaînes FAST réelles** (`epg.provider.plex.tv/lineups/plex/channels`, vignettes chaînes officielles, tri alphabétique local, logos en aspect-fit) ; Découvrir → Accueil onglet Tendances (mêmes hubs Discover) ; **lecture live fonctionnelle** : proxy loopback `127.0.0.1` qui sert la variante réécrite (segments SSAI `redirect_url=` décodés) à chaque poll + `inputstream.adaptive` + décodage logiciel forcé (V4L2 wedged sur discontinuités SSAI) | ✅ | — | captures |
| Sidebar — outline bibliothèque active | Livré | `parametres/settings_focus_005` | Pill outline sur la bibliothèque active (propriété `DivertActiveLibrary`) | ✅ | — | captures |
| Bibliothèque — onglets | Livré | `films_tabs_focus_002`, `13-library-films` | Recommandé / Bibliothèque / Catégories + ⋯ ; pill **Collections affichée seulement si la section a des collections** (Films : 4 pills, Séries TV : 3 pills, strip recentré) | ✅ | — | captures |
| Bibliothèque — hero Recommandé | Livré | `13-library-films` | Variante compacte du hero : méta sans genres (`2017   84m`), **pas de ligne cast**, chip rating **plein** (`AuraHeroChipSolid`, même boîte noire que les épisodes) ; le hero Accueil/Tendances garde genres + cast + chip bordé | ✅ | — | captures Pi Films |
| Bibliothèque — grille Browse | Livré | `films_browse_focus_003` | 6 colonnes 240×360, titre+année centrés, pills sombres (`2EFFFFFF`) en flux à gauche (type, par tri, Genre, compteur en pill, ⋯), zoom 108% + ring fin externe `poster-ring-thin.png`, rail A-Z avec cercle `az-ring.png`, badge ✓ + barre de progression ambrée | ✅ | — | `grid_v5.png` |
| Bibliothèque — rail A-Z | Livré | `films_browse_focus_003`, `rail_from_grid_004` | Lettres limitées aux initiales présentes (`/firstCharacter`), comme Plex (A B H J M O P T) ; alphabet statique en repli hors-ligne ; saut via `firstCharacter/{lettre}` (ratingKey frontière) | ✅ | — | captures |
| Bibliothèque — Collections | Livré | endpoint `/library/collections` | Rangée collections + drill-down | ✅ | — | captures |
| Fiche film — hero | Livré | `fiche/film_detail_top_001` | Clearlogo/titre, méta, chips providers (IMDb/RT/TMDB + icônes), synopsis `...`, réalisateur ; items non sortis → méta ambrée `Sortie le N <mois>` à la place de l'année (aussi en hero Accueil) | ✅ | — | `detail_v6.png`, `screenshot00141.png` |
| Fiche film — actions | Livré | `fiche/film_detail_top_001`, `detail-pills/` | Cercles compacts qui s'étendent en **pill blanche labellisée** au focus (Plex : `▶ Regarder` / `↺ Reprendre …`, `Recommencer`, `Ajouter à ma liste`, `Noter`, `Marquer comme (non) vu`, `Plus`) ; icône ↺ sur reprise ; noter → dialog 1-10 → `PUT /:/rate` | ✅ | — | captures |
| Fiche — bouton « Plus » | Livré | `22-detail-overflow`, `more_dialog_008` | Panneau dans l'ordre officiel : **Piste audio** (valeur courante, picker `audioStreamID` sur `/library/parts/<id>`) / Sous-titres (idem `subtitleStreamID`, « Désactivés » = Off) / Ajouter à une liste / Playlist-Collection / **Regarder la bande-annonce** (juste après Playlist, comme `22-detail-overflow`) / Gérer / Infos fichier / Autres façons / Titres similaires ; Infos fichier = vrai dialog données média ; entrées cloud → notification explicite | ✅ | — | captures Pi MobLand (picker audio vérifié end-to-end, persistance serveur) |
| Fiche — bord gauche → sidebar | Livré | — | `Left` depuis l'action la plus à gauche (pill Regarder, strip Série, premier item d'une rangée) ferme la fiche et ouvre la sidebar expansée | ✅ | — | `left_to_sidebar.png` |
| Fiche — clic cast | Livré | `cast_click_009` | Page personne Plex (`AuraPerson`) : photo circulaire, nom, filmographie serveur **groupée en rangées « Films » / « Séries TV »** quand les deux types existent (`person_filmography` → filtre acteur par section) ; clic carte → fiche du titre, Back restaure la rangée | ✅ | — | captures Pi Tom Hardy / Neal McDonough |
| Fiche — chip âge cliquable | Limitation | `longpress_center_002` | Plex mène à Common Sense Media (cloud) ; chip passive côté Aura | ⬜ | API privée non proxyée | — |
| Fiche film — badges média | Livré | `fiche/film_detail_top_001` | Pills séparées vidéo / audio / sous-titres, alignées à droite : format Plex `1080p (HEVC Main)`, `Français (EAC3 5.1)`, sous-titre sélectionné ou `Off`. **Fiches série/saison** : badges lus sur l'épisode que « Regarder » démarrerait (OnDeck sinon 1er épisode non vu — `_playable_item`) ; les records children/OnDeck n'ont pas de `Part.Stream` → hydratation `metadata_item` unique (`_streams_checked`) ; Play démarre le même épisode | ✅ | — | captures Pi MobLand (`4K DV (HEVC main 10)` + `Français (EAC3 5.1)` + `Français Forced (SRT)`) |
| Fiche — ligne « Activity by you… » | Livré | `_audit/cast_click_009` | Ligne « Activité de vous et X » + stack de 3 avatars (compte + jusqu'à 2 autres — disques à initiale colorés déterministes quand pas de photo, comme Plex) ; le bouton de la ligne ouvre le **panneau droit** (« jeremy carlier a regardé » + date + « il y a N »), Left referme — modèle Plex exact. Entrées amis distantes = cloud, documenté | ✅ | — | captures |
| Fiche — portraits du cast | Livré (partiel) | Photos réelles | Cercles propres + fallback silhouette `actor-fallback.png` quand `thumb=NONE` | 🟡 | Beaucoup d'acteurs n'ont pas de thumb côté serveur | captures |
| Fiche série — saisons | Livré | `fiche/show_detail_top_005` | Strip Série / Saison N, rangée posters de saisons, liste épisodes landscape par saison ; **onglets ✓ Plex** (`46-home-2`) : squircle foncé + coche blanche 52 px en haut-droite des saisons entièrement vues, et les épisodes vus affichent le ✓ à la place du badge numéro (cartes non vues gardent le numéro) | ✅ | — | captures Pi MobLand |
| Fiche série — Cast & Crew | Livré | `official-live/27-detail-show` | Rangée circulaire portée sur les modes série et saison : la section inactive est garée hors écran et reprend le slot du bas au focus (même état final que le scroll Plex) ; l'en-tête 7060 bascule « N Saisons » / « Saison N » ↔ « Cast & Crew » ; clic portrait → fiche personne | ✅ | — | captures Pi MobLand |
| Page saison — hero épisode focusé | Livré | `official-live/27-detail-show` | Vue saison = page centrée épisode : le hero suit la carte focusée (titre épisode + logo série, méta `S7 • E16`, date, durée, boîte âge, chips providers, synopsis, « Réalisé par »), repaint instantané au déplacement puis hydratation `metadata_item` débouncée ; colonne Plex `strip → cartes → cercles d'action → Cast & Crew` (cartes sous le hero ~y590, cercles sous les cartes ~y930, pas de titre de section, heading « Cast & Crew » + portraits rognés au bord bas ~y1005/1050, ligne Activité masquée, badges média au niveau réalisateur ~y530) ; actions = épisode focusé (Resume/Restart/libellé `S1 E2 • Nm restantes`, cercle nu au repos) ; pickers audio/sous-titres suivent le hero | ✅ | — | captures Pi MobLand E1/E2, nav cartes→actions→cast→retour, Back → overview |
| Fiche épisode | Livré | — | Méta `S1 • E1 · date · durée`, synopsis, cast, Resume | ✅ | — | captures |
| Fiche — cercle restart ↻ | Livré | `fiche/show_detail_top_005` | Visible si l'item à lire a un offset de reprise ; `play(start_over=True)` | ✅ | — | `detail_v7.png` |
| Fiche — chip âge | Livré | `fiche/film_detail_top_001` | Format `age N+` / `Tous publics` (mapping PG-13/TV-MA/…) | ✅ | — | `detail_v7.png` |
| Fiche — scroll bas de page | Livré | `official-live/23-detail-bottom`, `official-live/24-detail-bottom2` | Machine à sections basée sur `_bottom_sections()` : chaîne `contenu → Cast & Crew → Bandes-annonces et bonus → <hub related>` rendue dans le slot du bas par parking hors écran (même état final que le scroll Plex) ; sections profondes (extras/related) = géométrie « fully-scrolled » Plex (rangée d'actions + activité + pills média parkées, rangée ancrée bas ~y1070, heading juste au-dessus) ; rangée extras = stills paysages 512×288 + légendes centrées, rangée related = posters 240×360 + titre/année centrés + badge ✓ ; clic extra → lecture du clip, clic related → drill-in sur la fiche du titre (modal empilé, Back revient). Reste : « Ratings & Reviews » et « Discussions » = API sociale privée Plex | ✅ | — | captures Pi MobLand (cast→extras→related), drill-in Peaky Blinders + Back |
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
| B1 | **Up Next** — autoplay épisode suivant avec compte à rebours Plex | Carte post-lecture `AuraUpNext.xml` (backdrop épisode, miniature, `S# - E# · série`, compte à rebours 15 s, Lire maintenant/Annuler) pilotée par le superviseur de `default.py` : détection de fin naturelle par polling position (≤3 s), lecture unitaire + file d'épisodes sérialisée dans `AuraUpNextQueue`. Durée/focus/Back paramétrés dans `up_next.py` | **vérifié à l'écran** : enchaînement automatique S1E4→S1E5 confirmé ; carte observée en vrai (en-tête « À suivre », « S1 - E2 · American Horror Story », titre « Intrus », vignette épisode, décompte ambré « Lecture dans N s », « Lire maintenant » focus + « Annuler », fond estompé) ; décompte à zéro → `result=play` auto | ✅ |
| B2 | **Skip Intro / Skip Credits** — chip « Passer l'intro » pendant les marqueurs | `includeMarkers=1` → `Marker` windows persistés (`AuraPlaybackMarkers`, fetch par `item_markers` à chaque play + à chaque épisode Up Next) ; la supervision `default.py` publie `AuraActiveMarker` et spawn `RunScript(...,skipmarker)` → `AuraSkipMarker.xml` (pill bas-droite, focus, `seekTime(end)`, auto-fermeture fin de marqueur, Back = dismiss sans respawn) | **vérifié à l'écran** (v0.69.6) : chip intro affiché dans la fenêtre, Select → seek pile à la fin du marqueur (4:12→5:03) ; chip credits affiché, libellé raccourci « Passer le générique » + pill élargie (400→460, le texte défilait tronqué) | ✅ |
| B3 | **`/:/timeline` reports** — progression envoyée au serveur pendant la lecture | `TimelineReporter` (daemon dans la supervision `default.py`) : `GET /:/timeline` à la transition lecture→play, puis toutes les 10 s (`state=playing`/`paused`, ratingKey résolu via le contexte de lecture persisté), `state=stopped` dès la fin de lecture avec la position fraîche du poll 500 ms, suspendu pendant un switch qualité. Paramètre `session=<uuid>` obligatoire : sans lui Plex répond 200 mais ne persiste pas `viewOffset` ; le serveur n'enregistre l'offset qu'au-dessus de ~2 % de progression | implémenté, **vérifié en réel** (session `akasha-aura` visible dans `/status/sessions` avec offset live, `viewOffset` persisté côté serveur) | **P1** ✅ |
| B4 | **Filtres dynamiques serveur** | `/library/sections/{id}/filters` + `/library/sections/{id}/{filter}` → entrée « Filtres avancés… » du menu ⋯ : picker catégorie → picker valeur (booléens → Oui/Non), dict `_divert_filters` fusionné dans les params `/all`, marqué ✓ dans la liste, visible dans le compteur, reset avec les autres filtres. Plex-only (pas d'endpoint `/filters` côté connecteur) | **vérifié à l'écran** (catégories serveur listées, « Filtrer par Genre » → valeurs, menus désormais sombres via AuraMenu) | P2 |
| ~~B5~~ | ~~**« Retirer de Continuer à regarder »** (appui long)~~ **LIVRÉ** | `PUT /actions/removeFromContinueWatching?ratingKey=` — entrée ajoutée à la feuille d'options pour tout item avec `viewOffset`, carte retirée de la rangée localement | ✅ endpoint confirmé (plexapi) + implémenté | — |
| B6 | **« You watched » / Activity feed propre** | `watch_history()` → `/status/sessions/history/all` (sort `viewedAt:desc`) normalisé + `viewed_at` ; troisième pill « Activité » (3072) du strip Accueil → rangée « Votre activité » synthétisée en hub ; ligne « Vous l'avez regardé le … » (7207) sur la fiche sous la rangée d'actions. Les entrées amis restent 🔴 cloud | **vérifié à l'écran** (v0.69.6) : onglet actif, rangée « Votre activité · Akasha » remplie (Dog, Harry Potter, The Expanse…) | ✅ |
| B7 | **« More Like This »** sur les fiches | `/library/metadata/{id}/related` → hubs titrés (`item_related`) rendus comme **une rangée par hub** en bas de fiche (« Related Shows » puis « More with Lara Pulver », posters + titre/année, clic → drill-in modal) sous Cast & Crew/extras ; l'entrée « Titres similaires » du panneau Plus → `AuraRelated.xml` reste pour la vue dédiée | **vérifié à l'écran** : deux rangées distinctes sur MobLand (Related Shows : Peaky/Sherlock/True Blood… ; More with Lara Pulver : Sherlock/Skins/True Blood), nav bidirectionnelle, clic → fiche, Back → rangée focusée | ✅ |
| B8 | **Recherche enrichie** | Historique persisté (`search.recent`, 8 entrées) + entrée « Effacer l'historique » en fin de liste ; personnes (`search_people`) + **genres** (match client-side sur `section_genres`, carte → bibliothèque pré-filtrée) fusionnés dans « Tout » ; zone vide remplie de suggestions (`discover_hubs`, 12 items). **« Tout » via `/hubs/search`** (`hub_search`, ordre de pertinence Plex : séries → épisodes → films, personnes name-matched en `Directory` dédupliquées par nom avec rôles fusionnés « Acteur, Réalisateur ») — flat-merge contenu/personnes qui peuple les 2 colonnes exactement comme `official-live/30` ; **périmètre = toutes les bibliothèques du serveur** ; les autres pills gardent le scan par section `title=` + repli si le hub échoue | **vérifié à l'écran** : « rooki » → The Rookie + épisodes en 2 colonnes ; « xuuq » → acteurs (Xun Liang, Gus Mercurio) en colonne droite ; historique persisté + « Effacer l'historique », posters Popular Searches | P2 |
| B9 | **Extras / bandes-annonces** | `item_extras` → bouton « Bande-annonce »/« Bonus » dans la rangée d'actions de la fiche (`AuraDetailExtras`), lecture des parts extras | implémenté, **vérifié à l'écran** (menu sombre de sélection quand plusieurs extras, lecture du trailer OK) | ✅ |
| B10 | **Playlists locales serveur** | `playlists()`/`playlist_items_with_total` (`/playlists`, `playlistType=video`) ; pseudo-section « Playlists » ajoutée en fin de sidebar quand non vide (Plex direct uniquement, pas de proxy connecteur) ; clic → drill-in dans la grille comme les collections, items en fiches | **vérifié à l'écran** : entrée sidebar (sans ⋯, pseudo-section) → grille 1 item avec vignette composite → drill-in « Aura Test — 1 élé. » → fiche item complète (playlist de test créée puis supprimée) | P3 |
| B11 | **« Go to Show »** depuis une fiche épisode | Entrée « Aller à la série » (7208, icône tv) du panneau Plus, visible uniquement sur les épisodes → `metadata_item(grandparent_rating_key)` → fiche série en mode `show` empilée (Back revient à l'épisode) | **vérifié à l'écran** (v0.69.9) : entrée visible sur fiche épisode, page série empilée | ✅ |
| B12 | **Sélecteur de version** (fichiers multi-part) | `versions[]` normalisé (`label` « 1080p HEVC — fichier », `part_key`) ; entrée « Lire la version… » (7209) du panneau Plus quand >1 Media → menu sombre `aura_menu` → `_start_playback` avec le part choisi. Navigation Up/Down du panneau gérée en code (entrées conditionnelles invisibles) | implémenté, **vérifié à l'écran** (101 Dalmatiens 2, 2 versions listées, lecture du part MPEG2 choisi) | ✅ |
| B13 | **UltraBlurColors** — teinte du fond de fiche | `UltraBlurColors` normalisé (`blur_colors`) → la couche de dim de la fiche (7002) est teintée via `setColorDiffuse('73'+topLeft)`, repli `7310131A` neutre | **vérifié à l'écran** : `topLeft=541406` serveur → fiche 101 Dalmatiens 2 teintée olive chaud (vs repli gris neutre) | P3 |
| B14 | **Chapitres** | Kodi 21 n'a **pas** de propriété JSON-RPC `chapters` → `item_chapters` lit le `Chapter[]` Plex (tag/index/startTimeOffset/thumb), persisté `AuraPlaybackChapters`, rafraîchi à chaque enchaînement Up Next ; cercle OSD visible si chapitres persistés **ou** `Player.ChapterCount > 1` → liste titre + timecode, chapitre courant en ambre + ✓, `seekTime` au choix | **vérifié à l'écran** : 12 chapitres rendus avec timecodes, surbrillance courante, Chapitre 4 → seek exact 12:09 | ✅ |
| B15 | **Continuité audio/sous-titres par série** | `AuraPlaybackItem` propage l'item courant (mise à jour à chaque avancée Up Next) ; JSON-RPC `Player.GetProperties` capture les pistes actives toutes les 10 s dans la boucle de supervision ; sélection persistée par `grandparent_rating_key` (repli `rating_key`) en setting addon `stream.pref.*` aux transitions d'épisode et en fin de session ; ré-application au démarrage par matching langue+nom (les index varient entre fichiers), sous-titres désactivés respectés | **vérifié en réel** : audio EN + sous-titre EN choisis sur AHS S01E01 → `stream.pref.73529` persisté → S01E02 rejoué avec EN/EN auto-appliqués (fix prop JSON-RPC `subtitleenabled`) | P4 |
| B16 | **Bibliothèques non-vidéo (Musique)** dans la sidebar | `library_sections()` (movie/show/artist) alimente la sidebar (icône `icon-music.png`) ; les onglets Recommandé/Collections/Catégories restent (Plex expose hubs/collections/genres pour la musique) ; clic artiste/album → drill-in `metadata_children` façon collections (grille albums → pistes), clic piste → lecture audio directe en arrière-plan ; résultats de recherche musicaux routés pareil | **vérifié à l'écran** (v0.69.6) : entrée sidebar OK ; section 6 réellement vide côté serveur → état vide propre après fix rangées fantômes + hero périmé | ✅ |
| B17 | **Écran d'erreur serveur** propre | Brique d'état centrée réutilisable (`DivertState` : `offline`/`error`/`empty`/`config`) — icône + titre + message + bouton d'action contextuel (Réessayer / Effacer les filtres / Retour / Paramètres), sidebar conservée. Les rangées partiellement en échec gardent leur label inline ; l'écran global n'apparaît que si tout a échoué | **vérifié à l'écran** (v0.69.6) : affiché en vrai après reboot sans réseau, « Réessayer » recharge l'accueil | ✅ |

### Vraies limitations (cloud / plateforme)

| # | Manque | Raison |
|---|--------|--------|
| L1 | Onglet Activité — entrées **amis**, réactions | GraphQL social privé plex.tv |
| L2 | Watchlist cloud synchronisée | metadata.provider.plex.tv (voir note : `discover.provider` déjà utilisé pour Tendances — limite possiblement côté connecteur, à trancher) |
| ~~L3~~ | ~~Multi-profils Plex Home + PIN, « Switch Profile »~~ | ~~Fonction compte plex.tv~~ → **implémenté** : picker « Qui regarde ? » (`AuraWhoWatching.xml`, membres via `api/v2/home/users`, avatars plex.tv réels, tuile « + Ajouter un utilisateur » en stub) + pavé PIN (`AuraPinEntry.xml`, 4 points, 1-9/0/⌫, touches télécommande acceptées) ; switch via `api/home/users/<id>/switch`, token persisté, rechargement complet ; Back du pavé → picker, mauvais PIN → pavé + ligne erreur ambrée. **Géométrie calée sur `official-live/00a/45`** : avatars 220 px (264 px focus) pitch 300, anneau blanc 304 px, badge cadenas **ambre + glyphe blanc** inversé blanc + ambre au focus, titre 70 px, nom focus 40 px gras / non-focus 24 px gris. **Vérifié à l'écran.** |
| ~~L4~~ | ~~Live TV / chaînes « Sur Plex », Discover cloud~~ | → **livré + lecture vérifiée en réel** : segment rail « Sur Plex » + grille FAST triée alphabétiquement (logos aspect-fit) ; **EPG now/next sur la fiche chaîne** (`/grid`, tous les créneaux `Media[]` normalisés : « EN DIRECT · titre · HH:MM–HH:MM » + synopsis + « À suivre ») ; **lecture live stable** — proxy loopback `127.0.0.1` servant la variante réécrite (beacons SSAI `redirect_url=` décodés, ffmpeg traite `file://` comme statique et ISA refuse les URLs beacon sans extension), `inputstream.adaptive` (fallback `PlayMedia`), **décodage logiciel forcé pendant le live** (le V4L2 bcm2835 fuit ses buffers GPU sur les transitions ad-slate SSAI → timeouts -62, freeze du Pi ; setting restauré après lecture via flag persisté) ; watchdog anti-vidéo-de-fond : tout lecteur vidéo actif sans fenêtre 12005 est arrêté (~2 s) — plus d'audio derrière les menus ni le voile ; supervision : `_player_alive()` tient la négociation ~30 s ; Back plein écran = `Stop` (keymap) → retour fiche/grille ; **chrome pseudo-section collapsé** : strip d'onglets + pills filtre/tri + rail A-Z + « ⋯ » masqués sur livetv (pill « Chaînes » dédiée), playlists garde « ⋯ » allégé (Lire/Aléatoire, sans filtres avancés — pas d'endpoint) ; catégories FAST non implémentables : `genreRatingKeys` opaques, aucun endpoint public de résolution (grille alphabétique fidèle à watch.plex.tv/live-tv) |
| L5 | « More Ways to Watch », Watch Together | Cloud / social |
| L6 | Miniatures de seek (trickplay bif) | Kodi n'a pas de support trickplay |
| L7 | Ratings & Reviews, Discussions | API sociale privée |
| L8 | Recherche vocale | Micro télécommande = protocole BLE propriétaire (voir plan voix `c8c8548a`) |
| L9 | Feuille « Account » complète (vie privée, critiques/discussions, suppression) | Entrées cloud plex.tv — la fiche locale montre Email/Username/Subscriptions réels (`/api/v2/user`), toggle « Connexion automatique » fonctionnel, le reste en stub |

### Écarts visuels restants (revue Claude sur captures)

- ~~**Clavier recherche** : touches `_`, `←`, `X` en texte brut~~ → icônes `key-space`/`key-backspace`/`key-clear` (+ variants dark) overlay ; ~~touches plus petites~~ → **vérifié à l'écran** : touches 64×64 au pitch 72 px dans un bloc x129, rangée bas 3×136 px flush aux bords du bloc, mic/tune au bord droit, icônes horloge (`icon-recent.png`) sur les recherches récentes, rail rétracté focusable à gauche.
- **Recherche** : ~~pas de rangée « Popular Searches » dédiée~~ → en-tête « Recherches populaires » (33584) affiché à la place des pills tant que la requête est vide (suggestions `discover_hubs` en dessous, comme Plex) ; ~~reste le rail gauche~~ → **vérifié à l'écran** : rail rétracté focusable (4 icônes + vraie photo d'avatar Plex via `AuraAvatar` global) sur la page recherche, Left au bord du clavier → focus rail (pill blanche), icône maison/plus → fermeture vers la sidebar étendue ; la loupe/avatar restent sans action (Plex garde la loupe active). **Géométrie calée sur la référence** (revue Claude, captures écran) : zone droite x=686, posters suggestions 240×360 pitch 299 (bord droit ≈1823 comme les cartes), sous-titres « N saison(s) »/date complète/année, cartes résultats 555×282 pitch 300 (personne = photo circulaire 160 px sans ligne serveur, genre = glyphe centré), ligne ambrée = friendlyName du serveur Plex (`/`), pill filtre sélectionné en ambre `E5A00D` même sans focus, récents x129/barre 432 px/icône 30 px, faux états de focus supprimés par layouts conditionnés `Control.HasFocus`. ~~pills à largeur fixe~~ → boutons statiques dimensionnés au texte (`i18n.text_width`), chaînés en onleft/onright ; ~~icône rail « recherche » sans surlignage~~ → cercle actif `FF3A3B3E` derrière la loupe comme Plex. **Alignement client officiel 2026.19.1** (captures `official-live/29-30`) : rail de filtres porté à **7 pills** (Tout/Films/Séries/Musique/TV en direct/Personnes/Services — « Cast & Crew » était erroné, l'officiel affiche « People ») ; la colonne gauche bascule de l'historique (icônes horloge) vers des **suggestions texte nu** (top résultats fusionnés) dès qu'une requête est saisie, un clic ouvre directement le résultat ; cartes épisode à **4 lignes** (titre/nom de série/S5 E1•Episode/serveur) via `ListItem.Property(parent)` ; fond carte `#1F1F1F` neutre (`#2B2B2B` focus) ; liste récents décalée à x=96 (icône x≈120, texte x≈162 comme l'officiel) ; recherches de sections **parallélisées en worker** (générateur de génération + join borné 15 s) — la boucle séquentielle gelait le dialogue ~2 min par frappe sur le chemin lent Pi→plex.akasha.ing (~5 s/section).
- **Accueil** : ~~rangée coupée net à x≈1823~~ → ~~fade `scrim-row-right.png`~~ → **correction audit final** : les captures officielles coupent la dernière carte **net, à pleine luminosité** — le scrim ajouté en v0.69.5 était un faux positif et est **retiré** ; titres de rangée réduits de 48 à 34 px (`font_aura_rowhead`, ~32 px officiel) ; strip onglets resserré (labels en `font_aura_tab` Inter Regular 34 comme l'officiel — boutons sans label propre + 3 overlays d'état, fini le double-draw décalé) ; chip âge hero = **boîte noire pleine** + texte blanc (était un contour translucide) ; ~~trou ~90 px entre titre et méta quand pas de clearlogo~~ → **vérifié résolu** (v0.69.8, Frankenweenie : titre texte ancré à la même baseline que les clearlogos) ; ~~horloge absente en barre rétractée~~ → v0.69.8 : horloge répliquée en haut à droite, centrée sur le strip contextualisé (Plex la conserve toujours) ; ~~format 24 h~~ → **`h:mm` 12 h + méridien AM/PM** comme Plex (`6:53 AM`) : le token `xx` de `System.Time` est ignoré par la locale minimale LibreELEC, le suffixe est un label conditionné sur `Integer.IsGreater(System.Time(hh),11)` — même rendu sur l'accueil (`Aura.xml`) et l'OSD (`VideoOSD`/`DialogSeekBar`) ; vérifié à l'écran (« 1:57 AM »). **Audit r23-24 (mesures au pixel vs `official-live/53/54/55`)** : strip onglets recalibré — police Inter Regular 25 (était 34), conteneur 470×48 (était 648×62), pills ajustées au texte FR +~26 px et gaps 16 ; listes de reco élargies 1696→1793 px pour que la dernière carte saigne jusqu'à x=1920 comme l'officiel ; titres de rangée descendus +11 px (~518 vs ~507) ; suffixe serveur rendu dans un **label dédié** (`font_aura_meta` ~60 % du titre, positionné à droite du titre via `i18n.text_width`) — `_hub_title_fr` retourne désormais `(base, suffix)` ; hero reflowé comme un *flow* Plex : sous-titre en Inter Bold 27 blanc pur, méta+plot+cast dupliqués en deux variantes selon `AuraHeroSubtitle` (sans sous-titre la méta remonte dans le slot du sous-titre ~306, puis plot ~359 et cast ~433 — vérifié `55`), cast **masqué pour les épisodes** (absent de la référence `53`) ; logo/titre re-ancré bas ~275 ; anneau de focus carte : marge -6, contour plein blanc (`FFFFFFFF`).
- **Accueil — round 25 (audit Claude r32, mesures pixel)** : champ de l'accueil **teinté par `UltraBlurColors`** comme Plex — deux voiles (`scrim-tint-left.png`/`scrim-tint-bottom.png`, teintés par `setColorDiffuse` sur `topLeft`/`bottomLeft` dans `_apply_hero_fanart`, synchronisé avec le swap debouncé du fanart) ; palette brute quasi-noire → `_tint_hex` booste saturation ~0.70 / valeur 0.42 uniquement si la source est colorée (s≥0.25, sinon repli sur le coin voisin le plus saturé — évite d'inventer une teinte sur `141314`) — vérifié à l'écran (voile olive sur Corneil & Bernie, teal/violet sur Mercredi) ; **« · Akasha »** : le « · » en tête de label est supprimé par le renderer Kodi → préfixe NBSP `\u00a0` (non trimmé) — point médian désormais visible, suffixe baseline +4 px, écart titre→suffixe 10 px ; hero variante A recalée au pixel (sous-titre 306-320 / méta 360-377 = officiel `53`), variante B (méta +14, cast +9 + gris `99FFFFFF`) = officiel `55` ; rail rétracté : capsule sombre translucide (`cap-r36` `73000000`, x28 y432 w72 h212) + icônes ~15 % plus grosses (avatar 46, loupe 38, maison 26, menu 22) comme l'officiel ; allégations Claude infirmées : la méta Plex **reflowe** bien sans sous-titre (mesure `55` vs `53`), le « cast » film est présent chez Plex.
- **Accueil — round 26b (audit Claude r55/r58, re-mesuré au pixel)** : bloc hero remonté −47 px (logo ancré bas y=228, sous-titre 253-276, méta 306-321, plot 359+ = officiel `53` au pixel) ; le bloc texte **glisse +50 px quand la barre modules est déployée** (`AuraBarFocused`) pour dégager le strip contextuel ; scrim régénéré (haut-droite ~2× plus lumineux, fondu bas conservé) ; rampe de teinte avancée à y~500 pleine largeur ; **deux variantes de chip** : épisode = boîte noire opaque `rounded-solid` sans contour (`53`), film = `meta-rating-box` seul dont le bord clair intégré sert de contour (`55`) — `chip-outline.png` retiré (doublait le bord) ; écart méta→chip 14→24 px, texte chip Inter Regular 19 ; rail : icônes ~21 px aux centres officiels (524/572/620), capsule `border=34` (72 px < 2×38 px provoquait un filet sombre par chevauchement des tranches), avatar découpé en cercle par `_circle_avatar` (PIL dispo dans le runtime Kodi du Pi) avec repli URL+masque ; focus-ring régénéré rayon ~20 px ; suffixe « · Akasha » espacé ~8 px (officiel ~9) ; dates hero accentuées (« août » — `_MONTHS_FR` était volontairement ASCII).
- **Icône « maison » fantôme** : ~~à investiguer~~ → corrigée en v0.69.5 — l'icône de l'item sélectionné dans la `focusedlayout` sidebar (3112) n'avait pas `Control.HasFocus(3310)` et se rendait hors focus.
- **Hero** : suit le focus (vérifié). ~~Plex rend `home.continue` en cartes paysage~~ → **correction audit v0.69.5** : la référence rend Continue Watching en **posters** avec barres de progression — le jumeau paysage est neutralisé (`style='hero'` → shelf dans `_rebind_reco_slots`), et le hub `home.ondeck` est filtré de l'accueil (Plex le fusionne dans Continue Watching ; sa rangée dédiée doublait « Continuer à regarder »).
- **Fiche — chips de notes** : ~~1 pilule unique~~ → v0.69.5 : chips **nues** multi-providers depuis le tableau `Rating[]` serveur (pilule âge + IMDb / RT critique / RT audience / TMDB, icônes + valeurs — 4 chips max + âge).
- **Fiche — pilule d'action vide** : v0.69.5 — `_watch_label()` peut résoudre après `_populate` (lookup épisode suivant) : l'overlay label est re-synchronisé dans `_sync_action_row`, fini la pilule « Regarder » blanche vide.
- **Avatar rail** : ~~disque générique~~ → v0.69.5 : vrai avatar plex.tv (`/api/v2/user`, fond dans un thread, clip circulaire via `cast-mask`), fallback `avatar-plex.png`.
- **Suffixe serveur** : v0.69.5 — « · Akasha » grisé appliqué à **tous** les hubs section-scopés (recentlyadded/released inclus, pas seulement les curated). **Fix résilience** : `server_friendly_name()` ne fige plus un échec transitoire (`hasattr` sur `''`) — retentative à chaque appel tant que le nom est vide ; le coût reste borné (reponse `/` en read-cache 30 s, échecs instantanés sous le breaker offline). Vérifié à l'écran : « Ajoutés récemment dans Animés · Akasha ».
- **Saisons** : ~~« Season 7 » brut~~ → v0.69.5 : cartes saison + en-tête épisodes via i18n « Saison N » (tests de garde ajoutés).
- **Anneau de focus** : ~~équerres~~ → v0.69.5 : `focus-ring.png` régénéré, bordure continue 4 px arrondie (vérifié sur la grille saisons).



- **Flux « Activité » (entrées amis)** : feed social (GraphQL privé) → l'onglet montre l'historique personnel serveur (B6) ; les entrées amis ne peuvent pas être reproduites.
- **Watchlist** : synchronisation compte Plex en ligne — notification « Watchlist indisponible » en attendant le connector.
- ~~**Multi-utilisateurs / PIN (« Who's watching? »)** : fonction compte plex.tv~~ → **livré et vérifié à l'écran** : `aura_switch.py` + `AuraWhoWatching.xml`/`AuraPinEntry.xml` (membres `.Akasha` + `jeremy carlier` avec vrais avatars plex.tv et cadenas, `switch_home_user` → 401 sur mauvais PIN → pavé erreur, Back → picker). « Add user » reste un stub (création = app.plex.tv).
- **Onboarding Plex** (`onboarding/*`) : parcours de première ouverture de l'app Plex elle-même — hors périmètre Aura.
- ~~**Contenus « Sur Plex »** (TV en direct, Découvrir) : sources cloud Plex, notification explicite~~ → **TV en direct livrée** (voir L4) : grille FAST réelle + EPG + lecture stable ; Découvrir reste le relais Tendances (même source de hubs Discover).
- **Écran « Plus »** : Plex liste des sources supplémentaires (souvent vide) ; Aura ouvre « Gérer les bibliothèques » (épinglage) — équivalent fonctionnel ; ~~feuille native grise~~ → **vérifié à l'écran** : `aura_menu.select` (feuille sombre partagée) + `aura_menu.confirm`/`.message` (textbox multiligne + pills Confirmer/Annuler/OK) remplacent tous les `Dialog().select`/`.yesno`/`.ok` visibles (gestion bibliothèques, veille/redémarrage/arrêt, infos fichier, désinstallations Store/App).
- ~~**Portraits d'acteurs** : le serveur renvoie souvent `thumb=NONE` → fallback `actor-fallback.png`~~ → corrigé (v0.69.9) : les hubs ne portent pas les `thumb` des `Role`, la fiche réhydrate `metadata_item` en tâche de fond et la rangée cast affiche les vraies photos (vérifié sur films et épisodes) ; le fallback ne sert que pour les rôles réellement sans photo.
- ~~**Backdrop** : couleur de fondu légèrement différente~~ → **vérifié au pixel** (r60) : le voile Plex est le **champ bilinéaire des 4 coins `UltraBlurColors` bruts** sous un masque fixe (opaque gauche ~45 %/bas, fenêtre diagonale haut-droite) — mesures inversées sur `official-live/17` (même item, même serveur : coin bas-gauche = `bottomLeft`, bas-droite = `bottomRight`, haut-gauche = `topLeft` à ~alpha 1). `field_veil.bake_field_veil()` (module partagé accueil+fiche) écrit le PNG RGBA par palette (`<profile>/fields/field-v3-*.png`, cache plafonné à 24, version du masque dans le nom pour invalider `Textures13.db`) chargé via `AuraFieldVeil`/`AuraDetailVeil` ; `scrim-hero.png` + voiles mono-teinte 5020/5021 + teinte plate 7002 restent le repli sans palette/PIL. **Masque v3 (audit 30/10)** : secteur elliptique centré sur le coin haut-droit `alpha=clamp((sqrt(((u-1)/0.50)^2+(v/0.48)^2)-0.40)/0.62)` — le masque officiel est strictement identique entre accueil (`17`) et fiche (`18`), mesures inversées confirment ouvert dès u~0.80 en haut, refermé à v~0.5 sur le bord droit. **Fiche film/épisode** : même voile 4-coins (contrôle 7004), teinte plate 7002 masquée quand le voile est actif pour que le fanart traverse à pleine luminosité dans la fenêtre. **Géométrie fiche recalée sur `official-live/18`** : titre section y684 (était 766), rangée cast y733 (était 828), pastilles ⌀230 px pitch 280 (était 190/215), noms y~995/rôles ~1030, pills média y588 (était 672). Coins mesurés à l'écran **identiques à l'officiel** ((17,52,53)/(18,39,21)/(161,49,38)). **Masque v10 + vrai bilinéaire (audit 30/10 soir, `official-live/32`)** : le `resize` PIL 2×2→480 ne rendait pas un bilinéaire — il clampait en colonnes pures aux quarts gauche/droit ; le champ est désormais construit pixel-par-pixel (120×68 → 480×270). La fenêtre d'art n'est **pas** elliptique : c'est une saignée faible (~10 % d'art sur u~0.15-0.5, figures estompées) + rampe raide vers exposition pleine à u~0.75 (`0.10·ss((u-0.15)/0.25) + ss((u-0.48)/0.28)`), qui s'éteint vers le bas (`1-ss((v-0.05)/0.70)`). Le champ n'est pas la palette brute : un **creux de luminance** (~0.6-0.75 de la palette sur v~0.05-0.75 derrière la colonne texte + scrim haut renforcé) mesuré sur les pixels de champ propres de `32`/`18` — erreur moyenne ~10 canaux sur 19 points (dont pixels d'art réel). **Géométrie série recalée sur `32`** : la ligne Activité pousse le titre « N Saisons » à `_flow_top+204` (était +120 → 738 vs 738 officiel au pixel) et la rangée à `+264` (788 vs 788) — offsets par mode, films inchangés (+120/+171).
- **Fiche — hydratation complète** : ~~séries sans chips IMDb/RT, « age 10+ » au lieu de 13+, teinte neutre~~ → `metadata_item()` demande `includeRatings=1` ; `contentRatingAge` pilote le chip « age N+ » ; l'hydratation tourne pour tout item fin (séries/saisons incluses, pas seulement les films) et le merge précède tout rendu (teinte UltraBlurColors orange chaude sur The Rookie, comme l'officiel). **Ligne Activité complète** : `watch_history` expose les comptes distincts de la réponse entière — « Activité de vous, jeremy carlier et 2 autres » + 3 avatars empilés, comme Plex (les avatars ronds sont des disques à initiales quand `/accounts` n'a pas de photo — les vraies photos sont cloud-only).
- **Paramètres — taxonomie** : l'officiel liste les réglages applicatifs Plex (Account, Plex Home, Experience, Player Experience, Video & Audio, Subtitles, Advanced, Privacy, About). Aura affiche ses propres réglages OS (modules, réseau, apparence) dans la **même géométrie de sheet** (x437-1233, pill blanche, toggles ambre) — divergence volontaire : renommer nos catégories en labels Plex masquerait des réglages réellement différents ; documenté, pas à « corriger ».
- ~~**Typographie** : Aura utilise `RobotoCondensed` (skin) vs le sans-serif standard de Plex~~ → **corrigé** : patch `patch_aura_fonts.py` idempotent — alias `font_aura_*` recâblés sur `Inter-Unicode-{Regular,Bold}` (copiés dans `skin/fonts/`, `resource://` non résolu dans un fontset non-unicode) ; tailles calibrées sur la référence (mini/tiny/midi ≈ ×0,84 après mesure « Collections » = 116 px exact comme Plex) ; ~~pills onglets trop étroites~~ → boutons élargis au texte + marge (Kodi inset le label de ~48 px via le border du texturefocus : « Tendances »/« Pour vous » ellipsaient) ; rail A-Z = vérité serveur `firstCharacter/{lettre}` (ratingKey frontière) au lieu du titre brut — vérifié écran (« T » → « T'as pas changé »).
- **Format des timecodes OSD** : ~~`hh:mm:ss`~~ → **vérifié à l'écran** : écoulé/restant en `m:ss` non paddé sous 1 h (`0:19` / `-38:58`), `h:mm:ss` au-delà (variantes conditionnelles sur `Player.Duration(h)`) ; méta durée en texte localisé « 39 minutes » / « N h MM min » (33585). Plex affiche la qualité en chip `HD` encadrée → **corrigé** : la méta OSD rend une tag bordée accolée au texte (grouplist horizontale + label `width="auto"`) ; le libellé (`SD`/`HD`/`4K`) est cuit dans des textures `osd-tag-<résolution>.png` résolues via `$INFO[VideoPlayer.VideoResolution,osd-tag-,.png]` — vérifié à l'écran (épisode 480p → « SD »). **Géométrie OSD recalée au pixel sur la référence** (round 19) : titre x73 y73-99, méta y115-134, horloge x1757-1839 y65-81, glyphe pause x80-101 y963-986 (canvas 64×64 de la texture compensé), timecodes en `font_aura_clock` (Inter 32) x151-247/1768-1842, track 12 px y969-980 x222→1722, knob blanc 30 px (`osd-nib.png`), cercles subs/réglages x1711/1785 y870-934, chevron fin x949 y1006, scrims haut/bas — `DialogSeekBar.xml` refait en jumeau passif (masqué pendant `videoosd`) pour ne plus doubler le rendu.
- **Fiche — marge et rail** : ~~contenu à x=105~~ → **vérifié à l'écran** : marge déplacée à x=128 comme Plex, rail latéral en capsule sombre x28-100 y430-648 (avatar 38 px + icônes 17-21 px centrées x64), méta remontée à y302, chips notes à y350, synopsis resserré à 800 px en `font_aura_small` (Inter 24), strip de saisons dans un conteneur translucide dimensionné au nombre d'onglets (pas 150 px, onglet actif = contour fin — jamais de remplissage), titre de section « N Saisons » en `font_aura_main_bold`, posters de saisons 240×360 (pitch 252), glyphes d'action 28 px et cercles d'action ~20 % d'opacité, backdrop assombri (`8C10131A`).
- **Fiche — bloc bas fluide** (round 20, vérifié à l'écran) : Plex remonte tout le bloc inférieur de ~40 px quand la fiche n'a pas de ligne réalisateur (séries) — `_flow_top` = 564 avec réalisateur / 524 sans, appliqué aux actions, à l'activité (T+91), aux badges média (T+108), au titre de section (T+202) et aux rangées (T+264) via `_apply_flow`. Badge de classification contenu accolé à la méta (`7190/7191`, texture `meta-rating-box.png`, position mesurée en PIL ×1,2 — `i18n.text_width`) : `2018 43m Crime, Drame [10]` comme Plex.
- **Fiche — strip onglets** : Kodi dessine l'item sélectionné avec le `focusedlayout` même sans focus → layouts conditionnés `Control.HasFocus(7120)` : sélectionné non-focusé = **contour fin** (Plex), focusé = **pill blanche texte sombre** — vérifié à l'écran (Friends, The Rookie). Cycle de navigation complet validé via `System.CurrentControlID` : actions ↑→ strip, strip ↓→ actions, actions ↓→ rangée (posters/épisodes), rangée ↑→ actions.
- **Fiche — rangée de saisons initiale** : ~~`selectItem(preferred)` au chargement scrollait la rangée (S~2 visible en premier)~~ → **vérifié au pixel sur `official-live/32`** : Plex rend la rangée **flush-left (S1 à x~105)** au chargement et n'applique la saison préférée (On Deck) qu'à l'entrée du focus. `_season_pending` mémorise la position préférée sans `selectItem` initial ; `onFocus(SEASONS_LIST_ID)` l'applique au premier passage dans la rangée — mesuré : premier poster x~105, titre « 8 Saisons » y738, haut des posters y~785 — identique à l'officiel des deux côtés.
- **Fiche — épisodes** : cartes paysage avec resume `InfoTagVideo.setResumePoint` (repli `resumetime`/`totaltime`) → barre orange `IsResumable` **vérifiée** (The Rookie S7E8 ~51 %, A.D. S1E1 ~3 %), badge ✓ « vu » cercle sombre top-right **vérifié** (S7E4-E7), titres tronqués en `…` Unicode (`i18n.ellipsize`, budget 253 px), durée sous le titre, focus auto sur le premier épisode en cours/non vu. Ligne activité `7207` liée à `AuraDetailActivity` (elle n'avait jamais de `<label>` — texte invisible jusqu'ici) avec stack d'avatars (`AuraAvatar` réel en premier).
- **Recherche — horloge et hint** : ~~horloge pill superflue~~ → **supprimée** (la référence Plex n'en a pas sur cet écran) ; ~~hint trop blanc/gras~~ → `font_aura_small` + `C8FFFFFF` (Plex ≈201/191 gris) ; en-tête « Recherches populaires » agrandi en `font_aura_head_bold` (caps ≈24 px comme la référence).
- **`ReloadSkin` pendant une lecture active** : peut faire planter Kodi (SIGSEGV observé en test au teardown du player) — opération dev uniquement, pas un chemin utilisateur.
- **Menu profil (sheet gauche)** : géométrie calée sur `official-live/48-account-menu.png` (sheet x437-835 y34, pitch 76, pill 64 px, icône x+48, texte x+106) ; les 7 entrées officielles avec icônes ; pill blanche focusée ; sheet et rail en **noir pur `#000000`** (le rail étendu officiel est opaque noir — `FF262626` → `FF000000` dans `Aura.xml` + réplique). **Découverte Kodi** : un `WindowXMLDialog` modal assombrit irréductiblement la fenêtre parente — impossible de garder le rail lisible dessous. Solution : `_sidebar_snapshot()` sérialise les items/props du rail (3310) et `AuraProfileMenu.xml` redessine une **réplique non dimmée** dans le dialog (liste 9020, layout cloné avec conditions « expanded » forcées). Deux pièges : un `<control type="list">` ne rend **rien** sans `<focusedlayout>` (les deux layouts sont obligatoires pour l'allocation des vues), et Kodi peint l'item sélectionné avec le `focusedlayout` même quand la liste n'a pas le focus — le focusedlayout de la réplique est donc un clone exact de l'itemlayout. La ligne profil de la réplique porte la pill source `#1A1A1A` (`is_profile`), comme l'officiel. Actions validées à l'écran : Profil → fiche info, Paramètres → panneau settings, Back → rail. **Pile de sheets (`52-back-state`)** : Paramètres/Profil/etc s'ouvrent **par-dessus** le menu — Back depuis un sous-panneau rouvre le menu profil avec le focus restauré sur la ligne qui l'avait ouvert (vérifié à l'écran) ; Back depuis le menu referme vers le rail. Sorties terminales : switch profil réussi (→ accueil du nouveau profil) et lancement de lecture.

## Color channel order — AARRGGBB everywhere (corrected)

**Corrected finding (verified on-device, Kodi 21.3 ARM64 / LibreELEC
12.2.1):** every color pipeline in our addon reads plain `AARRGGBB`:

- Regular image `<texture colordiffuse="FF0000FF">` renders `(0,0,255)`
  blue — standard ARGB — inside and outside `<list>` controls.
- `texturefocus`/`texturenofocus` color attributes are also ARGB
  (`FFFF8C6C` renders salmon `(255,152,123)`).
- `midtexture` on `progress` controls is ARGB too (`FFE5A00D` renders
  the intended amber progress fill).
- `textcolor`/`focusedcolor`/`[COLOR]` tags are ARGB.

The earlier claim that `colordiffuse` is `AABBGGRR` build-wide was a
**false diagnosis** — likely a mix-up with Estuary's native XBT textures
(`button_focus FF00B8F5` is authored golden-amber natively, not
swapped). Its consequence: values that had been pre-swapped
(`FF0DA0E5` intended-as-amber, `FFFF8C6C` intended-as-light-focus)
rendered cyan/salmon until corrected back to their natural ARGB.

**Rule now:** author all colors in `AARRGGBB`. Python-fed
`$INFO`-bound colordiffuse (genre `TileColor`, avatar `_PALETTE`) are
natural ARGB — the `_bgr()` helper is gone from the call sites.

## Settings sheet (official geometry + interactive rail replica)

Measured on `official-live/49-settings.png`: the sheet is a black
rounded panel x437-1233 (w796), y34-1045, corners ~16px; title at
x503 y112-138 (`font_aura_main_bold`, bottom-anchored); white focus
pill x502-1169 (w668, h64), 76px pitch, first row pill y134; values
right-aligned ending ~x1141; OFF toggle = 51x32 track `(40,42,45)` +
knob `(87,91,97)`, ON toggle = amber `E5A00D` track + white knob
(Plex gold). `AuraSettingsPanel.xml` was refactored from the old
full-height split-pane to this sheet; the contextual help pane is
hidden (no right pane in the official sheet). Category order follows
Plex's Account → Player → Video/Audio → Appearance → … → Advanced
progression (`_PLEX_ORDER` in `settings_catalog.py`) — verified on
the Pi after deploy.

The expanded rail stays readable behind the sheet through the same
`_sidebar_snapshot()` + replica-list-9020 mechanism as the profile
menu — and the replica is **interactive**: `Left` moves focus onto it
(white focus pill + dark text variants gated on
`Control.HasFocus(9020)`), `Select` stores `rail_selection`/`rail_pick`,
the dialog closes and `_activate_rail_index(pos)` activates the real
sidebar entry — matching Plex, where the rail stays functional under
modal sheets. Implemented for both `AuraSettingsPanel.xml` and
`AuraProfileMenu.xml`.

## Playback OSD + chapters/queue overlay (official refs 35-43)

- Chip « −10 » (`9112`) : cercle translucide ~60 px coin bas-droit, révélé dès que le focus OSD quitte le bouton lecture (`!Control.HasFocus(9100)`) — même condition que Plex, qui l'affiche après la première entrée directionnelle (`36-43`). `PlayerControl(SmallStepBackward)`, pill blanche + texte sombre au focus.

`skin-patches/plex-osd/VideoOSD.xml` was measured against
`official-live/40-osd-back.png` (clean 1080p frame):

- Circles: **two only** (subtitles + gear — Plex has no chapters
  circle), ~76px diameter at y862, centers x1743/x1820; focused circle
  goes solid white with a dark glyph twin (icon swap on
  `Control.HasFocus`).
- Seek bar x222-1722 (matches official x216-1722 within glyph margin),
  12px amber track + 24px white knob, elapsed x148, remaining ends
  x1842 — all confirmed.
- The thin chevron (y~1006) is the entry to the chapters/queue
  overlay: its onclick now runs `osdqueue` instead of `Action(Back)`.

`AuraOsdQueue.xml` (new window 1204) reproduces Plex's Down-on-OSD
sheet (`41-osd-settings-menu.png`, `39-osd-playqueue.png`):

- "Chapters" heading + horizontal cards 404x227 (16:9), white rounded
  outline on focus, bold chapter name + dimmed timestamp centered
  below, pitch 426 — thumbs come from the Plex BIF index
  (`/library/parts/<partId>/indexes/sd/<startMs>`), wired through
  `store_chapters` (`thumb` field, part id parsed from `part_key`).
- "Play Queue" heading + episode cards 396x223 pitch 417; the
  currently-playing card carries a dark disc + white play glyph
  (`ListItem.Property(playing)`).
- Layout is a bottom-anchored stack that slides -345px when the queue
  list takes focus (conditional reversible `slide` animations driven
  by `Control.HasFocus(1002)`), collapsing to a queue-only layout when
  `Window.Property(haschapters)` is empty.
- Scrim = light veil + bottom gradient + a `F2000000` slab so the
  VideoOSD bar underneath cannot bleed through.
- Selecting a chapter seeks (`Player().seekTime`); selecting a queued
  episode rewrites PROP_ITEM/PROP_QUEUE exactly like the Up Next
  advance, refreshes markers+chapters, and plays the part URL with the
  PROP_SWITCHING guard held until `isPlayingVideo`.

OSD menu fixes in the same pass: the list now lands focus on the
first *actionable* row (headers carry no action and Plex never lets
them take the pill), and header rows in `focusedlayout` keep the
dimmed `66FFFFFF` instead of the invisible `AA10131A` on dark. Panel
background neutralised to `F2161616`.

## Home tab strip — For You / Tendances / Activité

`official-live/54-home-tabs-focus.png` + `55-tab-trending.png` show
Plex's `For You | Trending | Activity` strip. Delivered:

- **Pour vous** — local `/hubs/promoted` rows (verified earlier).
- **Tendances** — `discover.provider.plex.tv/hubs/promoted` (the
  *server* token is accepted — the earlier "401/no token" suspicion
  came from a headerless manual curl, not a scope issue). The 12
  promoted hubs are placeholders (zero inline items) hydrated via
  their provider `key`, fetched in a bounded 6-worker pool — a serial
  chain froze the click handler ~60s. Cards are tagged `cloud` and
  backfilled from `provider_metadata()` (trailers hydrate the parent
  movie through their `/extras/` key): the hero then shows the same
  meta + plot + cast block as `55-tab-trending.png`. Focus lands on
  the first card after a tab click (immediate + deferred focus, like
  `_focus_first_subtab`). If Discover fails or answers empty, the tab
  renders the honest empty state — never a silent copy of Pour vous.
- **Activité** — own watch history (friend feed is Plex's private
  social GraphQL, documented limitation L1). Entries lack
  `grandparentRatingKey`, so the row collapses on the show title —
  one card per series.

Remaining divergences: service badges (prime/tv) on Trending cards
need Plex's availability API -- `metadata.provider.plex.tv/library/metadata/<id>/availabilities` exists but returns an empty container for every item on this account (no streaming services selected), so there is no badge data to render; the cloud
detail page opens hydrated but its local follow-up calls (extras,
history) no-op — no playable file exists locally; the
"Find What To Watch, Anywhere!" promo tile is not reproduced.

Cloud detail pages (verified on Pi, VisionQuest): trailer/clip cards
hydrate into their PARENT record wholesale (type + key), so a cloud
show keeps its season strip ("Série | Saison 1") like `27-detail-show`;
seasons and episodes are fetched through `provider_children()` (the
node's own `/children` key on discover.provider.plex.tv), the hero
follows the focused episode with per-episode provider rating chips,
and the action row is the cloud set — "Ajouter à ma liste" pill +
list/rate/watched/more circles matching `56-tab-activity`.

## Search "Popular Searches" — local-hub fallback

Same cloud wall on the search empty state: Plex feeds
"Recherches populaires" from Discover promoted hubs, which return
empty placeholders on this server/account. `_suggestions()` in
`aura_search.py` now falls back to the server's own
`home_hubs()` (skipping `home.*` resume hubs so the grid suggests
fresh content, not in-flight items), resolving hub continuations
through `hub_items_with_total()` when inline items are missing.
Verified on the Pi: the section now shows the same poster grid as
`official-live/29-search-empty.png` (x686, 240×360, ~299 pitch),
with recent history + "Effacer l'historique" under the keyboard.

## Shell respawn — Back-exit no longer strands on the loading veil

`patch_native_loading.py` permanently covers the native Kodi windows with
the "Chargement..." overlay (documented intent: they are transition
surfaces only). A bare Back-exit therefore left the user on an eternal
loading screen until Home was pressed, and the dying invoker could stall
for minutes in `CPythonInvoker: waiting on thread` while a stray worker
kept the interpreter alive.

`default.py` now supervises the window in an abort-aware loop: the
playback handoff keeps its existing wait-and-restore flow, and a plain
close reopens Aura after a 0.75 s debounce -- the shell is the
destination, matching the "native Home is never a destination" rule.
The invoker no longer tears down per close, which removes the recurring
thread-wait symptom entirely; a stack dump of still-alive threads is
logged at real script exit for the residual unknown worker.
`HomePressMonitor`'s single-press Timer is now daemonized too.
Verified on Pi: five rapid Backs return to a working home each time,
Kodi shutdown stays prompt.
