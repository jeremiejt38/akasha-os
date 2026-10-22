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
| Sidebar — profil / Ma liste / Playlists | Limitation | Menu compte plex.tv, My Lists, Playlists | Item présent, clic → notification explicite | ⬜ | Fonctions cloud plex.tv non proxifiées par le connecteur privé | — |
| Sidebar — section « On Plex » | Limitation | Contenus cloud Plex (Discover, Music…) | Absente | ⬜ | Sections cloud Plex hors connecteur privé | — |
| Bibliothèque — onglets | Livré | `films_tabs_focus_002` | Recommandé / Bibliothèque / Collections / Catégories + ⋯ | ✅ | — | captures |
| Bibliothèque — grille Browse | Livré | `films_browse_focus_003` | 6 colonnes 240×360, titre+année, pills de filtres, rail A-Z, badge ✓ | ✅ | — | captures |
| Bibliothèque — Collections | Livré | endpoint `/library/collections` | Rangée collections + drill-down | ✅ | — | captures |
| Fiche film — hero | Livré | `fiche/film_detail_top_001` | Clearlogo/titre, méta, chips providers (IMDb/RT/TMDB + icônes), synopsis `...`, réalisateur | ✅ | — | `detail_v6.png` |
| Fiche film — actions | Livré | `fiche/film_detail_top_001` | Pill `▶ Reprendre · … restantes` à largeur dynamique + 4 cercles glyphes (watchlist, noter, vu, ⋯) ; noter → dialog 1-10 → `PUT /:/rate` | ✅ | — | captures |
| Fiche film — badges média | Livré | `fiche/film_detail_top_001` | Pills séparées vidéo / audio 🔊 / sous-titres ▭, alignées à droite | 🟡 | Dépend des champs `video/audio/subtitle_label` remplis par item | captures |
| Fiche — ligne « Activity by you… » | Non implémentable | Avatars + activité des amis | Absente | ⬜ | API sociale privée ; limitation documentée | — |
| Fiche — portraits du cast | Livré (partiel) | Photos réelles | Cercles propres + fallback silhouette `actor-fallback.png` quand `thumb=NONE` | 🟡 | Beaucoup d'acteurs n'ont pas de thumb côté serveur | captures |
| Fiche série — saisons | Livré | `fiche/show_detail_top_005` | Strip Série / Saison N, rangée posters de saisons, liste épisodes landscape par saison | ✅ | — | captures |
| Fiche épisode | Livré | — | Méta `S1 • E1 · date · durée`, synopsis, cast, Resume | ✅ | — | captures |
| Fiche — cercle restart ↻ | Livré | `fiche/show_detail_top_005` | Visible si l'item à lire a un offset de reprise ; `play(start_over=True)` | ✅ | — | `detail_v7.png` |
| Fiche — chip âge | Livré | `fiche/film_detail_top_001` | Format `age N+` / `Tous publics` (mapping PG-13/TV-MA/…) | ✅ | — | `detail_v7.png` |
| Fiche — scroll bas de page | Limitation | `fiche/film_scroll_2_003`, `film_scroll_3_004` | Page fixe (Cast & Crew = dernière section) | ⬜ | Sections « Ratings & Reviews » et « Discussions » = API sociale privée Plex ; pas de scroll fenêtre Kodi | — |
| Lecture | Livré | Plex player | Lecture réelle via `part_key`, reprise (viewOffset) | ✅ | — | captures |
| Recherche | Livré | `recherche/` | Grille clavier a-z + suggestions live, cartes résultats 2 colonnes | ✅ | — | captures |
| OSD vidéo | Livré | `osd/` | Minimaliste : titre, méta, horloge, seek fine, cercles subs/settings | ✅ | — | captures |
| Focus carte sélectionnée quand focus ailleurs | Livré | `films_tabs_focus_002` | Ring discret via `ListItem.IsSelected` | ✅ | — | captures |

## Limitations connues (non contournables sans API privée Plex)

- **Flux « Activité »** : feed social (GraphQL privé) → empty state explicite.
- **Ligne « Activity by you… » sur les fiches** : même raison.
- **Watchlist** : synchronisation compte Plex en ligne — notification « Watchlist indisponible » en attendant le connector.
- **Portraits d'acteurs** : le serveur renvoie souvent `thumb=NONE` → fallback `actor-fallback.png`.
- **Backdrop** : couleur de fondu légèrement différente (scrim proche mais pas pixel-perfect).
