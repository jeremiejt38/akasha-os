# Akasha Aura — Décisions techniques

## PM4K n'est pas remplacé par "un autre addon" — diagnostic initial

Avant ce chantier, l'hypothèse de départ était de trouver un addon Kodi plus fidèle à Plex que
`script.plexmod` ("PM4K"). Vérification faite : PM4K (maintenu par `pannal`, dépôt
`pannal/plex-for-kodi`) est une continuation directe du client Plex officiel open-source pour Kodi
— c'est déjà l'interface Plex authentique, pas une approximation. L'alternative généralement citée,
PlexKodiConnect, fonctionne à l'inverse : elle synchronise Plex dans la base Kodi native pour
afficher une interface **Kodi** (avec un skin quelconque), pas l'interface Plex. Aucun addon
existant ne peut donc être "plus fidèle à Plex" que PM4K par construction — d'où le choix de
construire un accueil maison (Aura) plutôt que de chercher encore un autre addon.

## Source de données : API Plex directe, pas PM4K ni PlexKodiConnect

**Choix** : `plex_client.py` interroge directement le Plex Media Server (`X-Plex-Token`) pour les
rangées, la recherche, le tri et les filtres.

**Alternatives écartées** :
- S'appuyer sur ce que PM4K expose déjà : moins de travail, mais aucun contrôle sur l'agencement
  des rangées/l'apparence, ce qui contredit l'objectif "reproduire fidèlement l'accueil Plex/Fire
  TV".
- PlexKodiConnect + Kodi natif : change complètement l'interface (Kodi, pas Plex), à l'opposé de
  l'objectif de fidélité visuelle.

**Raison retenue** : un accueil qui se comporte comme l'app Plex/Fire TV a besoin des mêmes données
que l'app Plex/Fire TV consomme, donc les mêmes endpoints (`/library/onDeck`,
`/library/recentlyAdded`, hubs par genre, recherche de section) plutôt qu'une couche
d'interprétation intermédiaire.

## Remplacement de l'accueil : service de démarrage + keymap, pas de patch de `Home.xml`

**Choix** : `service.akasha.aura` (service `xbmc.service`, `start="startup"`) attend la fin de
l'intro (`service.akasha.splash`) puis ouvre `RunScript(script.akasha.aura)`. Un keymap
(`akasha-aura.xml`) redirige en plus l'action `Home` vers Aura pour qu'il reste le point d'entrée
même après une navigation profonde dans Kodi natif.

**Alternative écartée** : patcher directement le `Home.xml` du skin Arctic Horizon 2 via
`skin-patches/*.py` (même mécanisme que `patch_startup_logo.py`, `patch_contextmenu_title.py`,
etc.).

**Raison** : `skin-patches/*.py` modifie des fichiers XML du skin par regex — fragile et risqué
pour un composant aussi central que l'écran d'accueil (voir `docs/talos-strategy.md`, qui exclut
déjà ce type de patch des tâches déléguables). Aura en fenêtre `WindowXMLDialog` par-dessus,
exactement comme `script.akasha.ambient` et `script.akasha.guide`, est un patron déjà validé en
production sur ce projet, indépendant des mises à jour du skin. La fenêtre Home native de Kodi
reste intacte en dessous, accessible via Back — filet de sécurité en cas de blocage d'Aura, plutôt
qu'un remplacement à sens unique.

## Navigation de la coquille : `radiobutton` + propriété de fenêtre, patron `AkashaGuidePreset`

**Choix** : les 3 onglets sont des contrôles `radiobutton` (ids `2001`-`2003`), la navigation
gauche/droite entre eux change une propriété `Window.Property(AuraActiveTab)` qui contrôle la
visibilité des groupes de contenu — même mécanisme que les presets de `Guide.xml`
(`AkashaGuidePreset`) et le mode ambiant (presets de position anti-marquage).

**Raison** : patron déjà validé en production (fiable, pas de dépendance à un contrôle Kodi plus
complexe comme `tabcontrol`, dont le comportement dans les dialogues plein écran custom est moins
prévisible sur Kodi 21/Arctic Horizon 2).

## Intégration `akasha-os-connector` : pas de patch de `Home.xml`/skin natif (jalon 6)

**Contexte** : le cahier des charges "interface-plex-akasha" fourni par l'utilisateur décrit une
refonte en modifiant directement le skin natif (`Home.xml` control 9000, `MyVideoNav.xml`,
`DialogVideoInfo.xml`). Ceci contredit la décision déjà prise ci-dessus ("Remplacement de
l'accueil") d'éviter les patchs de skin par regex pour un composant central.

**Choix confirmé par l'utilisateur (2026-08-18)** : adapter le cahier des charges à l'architecture
Aura existante plutôt que l'inverse. Les concepts du CDC (sidebar par bibliothèque, onglets
Recommandations/Bibliothèque/Genres, fiche détail) se traduisent en éléments internes à
`Aura.xml`/`aura_window.py` (sous-onglets, groupes de contrôles, `Window.Property`) plutôt qu'en
modifications de `Home.xml` ou `MyVideoNav.xml`.

**Point ouvert non résolu** : le CDC suppose une source de métadonnées Kodi native
(`VideoLibrary.*` JSON-RPC, base `MyVideos*.db`) pour le contenu, alors qu'Aura utilise déjà l'API
Plex directe (`plex_client.py`, voir décision "Source de données" ci-dessus). Le connector expose
pour l'instant du JSON Plex brut — voir `roadmap.md` (jalon 6) pour le blocage identifié (URLs
d'image nécessitant le token Plex admin) avant de brancher réellement le connector dans l'UI.

## Désinstallation d'un addon depuis App : délégation à la fenêtre native (jalon 5, à confirmer)

**Constat** : il n'existe pas de méthode JSON-RPC publique de désinstallation d'addon dans Kodi.

**Solution de repli prévue** : ouvrir la fenêtre native `AddonInformation` pour l'addon ciblé
(`ActivateWindow(AddonInformation, <addon-id>, return)`) où l'utilisateur confirme via le bouton
natif "Désinstaller", plutôt que de manipuler directement le système de fichiers des addons
(`rm -rf` sur un dossier d'addon en cours d'exécution potentielle) — à valider en conditions
réelles au jalon 5.

## Réutiliser les sous-fenêtres d'Aura au lieu d'en recréer une à chaque ouverture (2026-08-18)

**Bug trouvé en conditions réelles** : `script.akasha.ambient` s'est mis à échouer en boucle
(`RuntimeError: maximum number of windows reached`, ~1900 occurrences en quelques minutes dans
`kodi.log`) alors qu'aucun changement ne lui avait été apporté. Kodi limite à environ 100 le
nombre d'IDs de fenêtres dynamiques (`xbmcgui.WindowXMLDialog`/`WindowXML`) qu'un addon Python peut
créer au cours d'une même session — chaque construction consomme un slot qui **n'est jamais libéré
avant un redémarrage complet de Kodi**, même une fois la fenêtre fermée et l'objet Python supprimé
(`del`). Or `aura_window.py` (et `aura_genres.py`) instanciaient une **nouvelle** fenêtre
(`AuraRecommendationsWindow`, `AuraLibraryWindow`, `AuraGenresWindow`, `AuraAppWindow`,
`AuraStoreWindow`, `AuraShowWindow`) à **chaque** clic sur "Pour vous"/"Bibliothèque"/"Catégories"/
etc., au lieu de réutiliser une instance existante — un usage normal et répété de ces menus
(attendu au quotidien, pas seulement en test intensif) épuise donc le pool au bout d'un moment, et
c'est alors n'importe quel **autre** addon qui tente d'ouvrir une fenêtre (ici Ambient, via son
déclencheur d'inactivité qui retente toutes les 5s) qui échoue — pas forcément Aura lui-même.

**Corrigé** : `AuraWindow._get_sub_window(key, cls, xml_file)` construit chaque sous-fenêtre une
seule fois (mémorisée dans `self._sub_windows`) et appelle `doModal()` sur l'instance existante
pour toutes les ouvertures suivantes — `onInit()` se ré-exécute à chaque activation (Kodi recharge
le XML du skin à chaque fois, confirmé par les logs `Loading skin file: ..., load type:
LOAD_ON_GUI_INIT` répétés), donc le contenu se rafraîchit normalement sans reconstruire l'objet.
Même traitement dans `aura_genres.py` pour la `AuraLibraryWindow` qu'il ouvre lui-même en interne.
Défense complémentaire dans `script.akasha.ambient/default.py` : si la construction de la fenêtre
échoue malgré tout (`RuntimeError`), log un warning unique et abandonne ce cycle de déclenchement
plutôt que de laisser l'exception se répéter en boucle toutes les 5 secondes.

## Bug distinct trouvé en validant le correctif ci-dessus : le cache local corrompt les tuples `(items, total)`

En revalidant sur le device réel après le correctif de réutilisation des fenêtres, la Bibliothèque
s'est mise à afficher "2 resultat(s)" au lieu du vrai total, avec en log `Akasha Aura Library:
render error: list indices must be integers or slices, not str`.

**Cause** : `local_cache.LocalCache.set()` sérialise les valeurs en JSON, qui ne distingue pas les
tuples des listes — `(items, total)` redevient `[items, total]` après un aller-retour JSON. Or
`PagedList._load_next_page()` teste `isinstance(result, tuple)` pour savoir si `fetch_page` a
fourni un total : au premier appel (cache miss), le tuple réel passe ce test correctement : mais
dès le second appel sur la même page (cache hit, dans la fenêtre de TTL), le résultat mis en cache
redevient une liste `[items, total]`, qui échoue le test `isinstance(..., tuple)` et se retrouve
traitée comme LA page elle-même — `self.items.extend([items_list, total_int])` ajoute alors deux
entrées à `self.items` : la liste d'items entière comme un seul élément, et l'entier `total` comme
second élément. D'où `len(self.items) == 2` ("2 resultat(s)") et l'erreur d'indexation dès qu'un
appelant essaie de faire `item['title']` sur ces deux pseudo-éléments.

**Corrigé** : `local_cache.get_or_set_page(cache, key, ttl, compute_fn)` — variante de
`get_or_set` qui stocke/restitue toujours explicitement `{'items': ..., 'total': ...}` (une forme
JSON-safe) et reconstruit systématiquement un vrai tuple `(items, total)` à la lecture, que ce
soit un cache hit ou miss. Utilisé à la place de `get_or_set` dans les 3 points d'appel concernés
(`aura_recommendations.py` ×3, `aura_window.py`, `aura_library.py`). Tests de régression ajoutés
dans `test_local_cache.py` (aller-retour cache hit avec tuple, cas sans total).

**Piège au déploiement** : le cache local SQLite persiste sur le disque du Pi entre les
redéploiements — les entrées déjà écrites avant ce correctif restent au format corrompu
(`[items, total]` brut) jusqu'à expiration de leur TTL (jusqu'à 300s). Le fichier
`page_cache.db` (`addon_data/script.akasha.aura/`) a dû être supprimé manuellement pour valider
immédiatement plutôt que d'attendre l'expiration.

**Validé sur le Pi réel** (v0.35.2, cache purgé) : deux ouvertures consécutives de Bibliothèque
(cache miss puis cache hit) affichent toutes les deux "771 resultat(s)" correctement, aucune
erreur dans les logs, plus de "maximum number of windows reached" après un cycle de test répété
(6× Bibliothèque/Catégories/Recommandé) grâce au correctif de réutilisation des fenêtres.

## Checkup complet (2026-08-19) : 5 bugs supplémentaires trouvés et corrigés

En auditant systématiquement le projet (logs Kodi, tests, revue de code) après les correctifs
ci-dessus :

1. **`<defaultcontrol>` pointant vers une liste vide au premier chargement** (`AuraLibrary.xml`,
   `AuraGenres.xml`, `AuraShow.xml`, `AuraApp.xml`, `AuraStore.xml`) : Kodi tente de focaliser le
   `defaultcontrol` avant même que `onInit()` ait peuplé la liste, produisant
   `Control XXXX in window YYYY has been asked to focus, but it can't` en log (cosmétique, sans
   impact fonctionnel grâce au `setFocus()` explicite déjà en place). Corrigé en alignant le
   `defaultcontrol` sur le bouton "Retour" de chaque fenêtre (même pattern que
   `AuraRecommendations.xml`), avec ajout du `setFocus()` manquant dans `aura_genres.py`.
2. **Fuite d'état dans `AuraLibraryWindow` réutilisée** : `self.query`/`self.filter_genre`/
   `self.sort` n'étaient jamais réinitialisés dans `onInit()`, donc une recherche ou un filtre
   laissé actif restait collé à la prochaine ouverture de "Bibliothèque" depuis la barre du haut.
3. **Site manqué du bug de réutilisation de fenêtres** : `aura_app.py` (bouton "Store") recréait
   encore une `AuraStoreWindow` à chaque clic au lieu de réutiliser l'instance mise en cache.
4. **Bug le plus impactant en usage réel** : le raccourci clavier/télécommande "Home"
   (`kodi/userdata/keymaps/akasha-aura.xml`, liaison `<global>`) déclenche
   `RunScript(script.akasha.aura)` à **chaque appui**, sans aucune garde contre un double lancement
   — la touche la plus pressée d'une télécommande salon aurait épuisé le pool de fenêtres bien plus
   vite que tout le reste. Corrigé avec un verrou basé sur le PID (`/tmp/akasha-aura.lock`,
   `os.kill(pid, 0)` pour vérifier la vivacité du process précédent) dans `default.py`. Même
   traitement pour l'entrée manuelle "Mode Ambiant" du menu Guide (`script.akasha.ambient`), qui
   contourne le verrou déjà existant du service de déclenchement par inactivité.
5. **Cache local sans auto-réparation** : `LocalCache.get()`/`set()` propageaient une
   `sqlite3.OperationalError` ("no such table: cache") si le fichier sqlite se retrouvait sans sa
   table (trouvé en conditions réelles après une suppression manuelle du fichier de cache pendant
   qu'Aura tournait), cassant tout le chargement de Divertissement. Corrigé pour recréer le schéma
   et traiter l'erreur comme un cache miss plutôt que de la laisser remonter.
6. **CI sans tests** : seuls "Build Akasha OS Image" et "Release Please" tournaient en CI — les
   nombreuses suites de tests unitaires du projet n'étaient jamais exécutées automatiquement.
   Ajout de `.github/workflows/test.yml` (matrice sur `script.akasha.aura`/`script.akasha.ambient`).
7. **Régression subtile introduite par le correctif de réutilisation de fenêtres** :
   `AuraWindow` étant désormais une instance unique pour toute la session Kodi, `onInit()` — et
   donc `_load_divertissement()` — ne s'exécute plus qu'une seule fois. Un échec transitoire au
   tout premier chargement (coupure réseau, connector momentanément injoignable — observé en
   conditions réelles pendant ce checkup) laissait la sidebar vide pour le reste de la session,
   sans aucun moyen de réessayer. Corrigé : `_show_tab()` retente `_load_divertissement()` si
   l'utilisateur (re)sélectionne l'onglet Divertissement et que la sidebar est toujours vide.

102/102 tests unitaires passent après ces 7 correctifs. Validé sur le Pi réel (v0.35.5 puis
correctif final non encore déployé au moment de la rédaction).

## Refonte Divertissement (plan 780ecf80) : sidebar permanente + onglets contextuels par bibliothèque

Suite au cahier des charges fourni (`780ecf80-cahier-des-charges-divertissement-akasha-os.md`) et à
la décision explicite de l'utilisateur ("option A [refonte complète] mais on oublie Collection") :
la sidebar (`3300`/`3310`) est désormais **toujours visible** en Divertissement (plus gérée par un
sous-onglet global) ; les onglets Recommandé/Bibliothèque/Catégories (`3050`/`3100`/`3060`), déjà
existants, sont déplacés sous un header (titre `3400` + sous-titre `3401` + bouton "..." `3402`) qui
n'apparaît que quand une bibliothèque est sélectionnée dans la sidebar (`Window.Property(DivertView)
== "library"`, sinon `"home"`). Nouveau state machine dans `aura_window.py` :
`_activate_home()`/`_activate_library()`/`_select_library_tab()` remplacent l'ancien
`_select_divert_subtab()`. `aura_recommendations.py` et `aura_genres.py` acceptent désormais un
scope optionnel (`.section`/`.initial_section`) pour refléter la bibliothèque sélectionnée au lieu
de toujours retomber sur la première section vidéo trouvée. Pas d'endpoint Plex dédié pour un
"on-deck" scopé à une bibliothèque : `on-deck` est over-fetché puis filtré côté client par
`section_id` (`divert_source.filter_by_section`, nouveau champ `section_id` sur les items parsés,
depuis `librarySectionID`). Collections explicitement écarté par l'utilisateur — seulement
Recommandé/Bibliothèque/Catégories.

**Bug de course Kodi trouvé et laissé documenté (non bloquant)** : depuis la grille "Bibliotheque"
(`3230`), appuyer sur Haut atterrit sur la barre d'onglets principale (`2001`) au lieu du bouton
d'onglet "Bibliotheque" (`3100`), malgré `<onup>3100</onup>` déclaré sur la liste et malgré `3100`
confirmé visible/focalisable au même instant (vérifié en direct avec un label de debug
`System.CurrentControlID` + `Control.IsVisible(3100)`). Ni l'interception explicite côté Python
(`focused == DIVERT_PANEL_ID`), ni la duplication de la condition `<visible>` sur chaque contrôle
individuel (au lieu du groupe parent seul) n'ont changé ce comportement — tout indique que la
navigation native de Kodi résout "Haut" géométriquement pour cette liste horizontale plutôt que de
respecter l'`onup` explicite. Pas d'impasse (2001 reste un état parfaitement navigable), donc non
bloquant pour cette release ; laissé en `super().onAction()` natif avec ce commentaire, plutôt que
du code mort qui prétendrait le corriger. À reprendre si une piste plus solide émerge (ex. tester
un `<panel>` au lieu d'un `<list>`, ou repositionner `3100` pour qu'il soit géométriquement le plus
proche candidat).

Validé en conditions réelles sur le Pi (v0.40.1+) : Accueil (rangées globales), Films → Recommandé
(scopé), Films → Bibliothèque (grille + navigation Gauche/Droite/Bas), Films → Catégories (33
vraies catégories Plex de la bibliothèque Films, pas celles de la première section par défaut),
bouton Paramètres inchangé (`ActivateWindow(Settings)`).
