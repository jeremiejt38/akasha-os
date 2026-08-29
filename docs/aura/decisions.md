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

## Plan ajusté f41ce1ad — Phase A (barre d'outils Bibliothèque), Phase B (bug "Haut" résolu), Phase C/D

### Phase A — barre d'outils complète sur la grille Bibliothèque contextuelle

Contrôles ajoutés (`3210`-`3218`, deux rangées sous les onglets contextuels) : type (info,
non interactif — une section Plex a toujours un seul type fixe, rien à choisir réellement),
filtre rapide (Tout/Non vus/Vus), tri (réutilise les mêmes 4 options que `AuraLibraryWindow`),
genre (dialogue natif, vraies catégories de la bibliothèque active), recherche (clavier natif),
compteur, et 4 actions rapides (Lire/Aléatoire/Liste/`...`).

- **Bug de cache réel trouvé et corrigé** (`aura_window.py` et, même défaut préexistant,
  `aura_library.py`) : la clé de cache ne conservait le tri (`sort`) que lorsqu'aucun genre/
  recherche n'était actif — changer le tri pendant qu'un filtre genre était actif renvoyait
  silencieusement la page mise en cache de l'ancien tri (aucune erreur, juste aucun effet
  visible). Corrigé en incluant systématiquement `sort` (et `unwatched`) dans la clé de cache,
  quel que soit le mode actif. Validé en direct : Genre="Comédie" + Trier="Titre" combinés
  correctement (43 éléments, ordre alphabétique).
- **Lecture/Playlist** : la résolution de lecture n'étant pas encore décidée pour Divertissement
  (déjà noté plus haut dans ce fichier), Lire/Aléatoire/Liste réutilisent le même placeholder
  (notification du titre) que le clic sur un item individuel — pas de comportement trompeur.
- **Filtre rapide "Non vus"/"Vus"** : le paramètre `unwatched` est bien envoyé (`plex_client.py`
  et `connector_client.py` étendus, testé unitairement), et fonctionne en direct pour l'accès
  Plex direct. **Non confirmé fonctionnel via le connecteur** en conditions réelles (le compteur
  ne change pas) — `akasha-os-connector` (repo privé séparé) ne comprend probablement pas encore
  ce paramètre côté backend ; à corriger dans une session future sur ce repo. Pas un blocage pour
  cette session (comportement dégradé silencieux, pas d'erreur, cohérent avec "le contenu
  réellement filtrable dépend de ce que la source expose").
- HDR/DOVI/Sans correspondance/Doublons du filtre rapide original : toujours hors périmètre, ni
  Plex ni le connecteur ne les exposent simplement.
- Job Talos tenté pour l'extension pure des clients (`unwatched`) : encore une fois déclaré
  "done"/validé sans avoir modifié aucun fichier (`git diff` vide) — implémenté manuellement,
  jobs résolus (`talos_resolve`) avec la raison. Deuxième occurrence de ce problème, voir
  `journal.md`/note process ci-dessous.

### Phase B — bug de navigation "Haut" : résolu (effet de bord de la restructuration Phase A)

Diagnostic précis effectué (comme demandé) avec un label de debug temporaire affichant
`System.CurrentControlID` directement dans le skin. Confirmation que le focus réel de Kodi
(`getFocusId()` côté script correspond exactement à `System.CurrentControlID` côté skin — pas de
désynchronisation entre les deux) : le focus était bien sur `3230` (grille) avant "Haut", et sur
`2001` (barre d'onglets) après — le saut sautait bien `3100` malgré son `<onup>` explicite.

Avec la nouvelle rangée d'actions (`3215` "Lire") positionnée directement au-dessus de la grille
(remplaçant l'ancien voisin `3100`, décalé plus à droite), le même `<onup>` explicite fonctionne
maintenant de façon fiable et reproductible (revalidé à plusieurs reprises : grille → Lire →
Filtre → onglet principal, chaque saut confirmé par le label de debug). Cause probable
(non confirmée à 100 % mais cohérente avec toutes les observations) : la résolution native de
Kodi pour "Haut" sur cette liste horizontale semble favoriser géométriquement la cible la plus
proche/alignée plutôt que de suivre l'`onup` déclaré à la lettre quand la cible explicite est
excentrée — `3100` était décalé loin à droite du premier item de la grille, `3215` est
directement au-dessus. Pas de régression introduite : testé à nouveau après un redémarrage Kodi
propre pour écarter un simple hasard de timing.

### Phase C — polish visuel

Deux bugs de troncature de texte trouvés et corrigés en conditions réelles (pas en théorie) :
les glyphes Unicode (▶, ⇄, ⋮) choisis pour les boutons d'action rapide ne s'affichent pas du tout
avec la police du skin (rendu vide) — remplacés par du texte simple ("Lire", "Aleatoire",
"Liste", "..."). Plusieurs libellés (Filtre, Trier, Rechercher) étaient tronqués dans une seule
rangée trop dense — restructuré en deux rangées (dropdowns / compteur+actions) avec des largeurs
revues à la hausse. Aucun chevauchement trouvé avec le header/onglets de la Phase 3 en 1080p.
Pas de comparaison pixel-par-pixel avec les captures Plex originales (non disponibles dans cette
session au-delà de la description textuelle du cahier des charges).

### Phase D — recette

Parcours bout en bout validé sur le Pi réel avec PixelCamera + `kodi-send`/JSON-RPC : Accueil →
sidebar → bibliothèque (Animés) → Recommandé (scopé) → Bibliothèque (tri, genre combinés,
recherche ouverte, filtre rapide, actions rapides) → retour Accueil (état restauré après un cycle
Back-vers-Kodi-natif puis réouverture d'Aura) → Paramètres (déjà validé, non cassé). **Non fait** :
test manette Xbox Wireless physique (aucun matériel disponible dans cette session à distance) ;
test sur une bibliothèque "Films" à plusieurs milliers d'éléments spécifiquement pour la
performance de la grille+barre d'outils (testé sur "Animés", 85 éléments, réactif ; le
comportement à plusieurs milliers reste à valider par l'utilisateur en usage réel).

### Point de vigilance process (deuxième occurrence)

Un deuxième job Talos s'est déclaré "done"/validé sans avoir modifié aucun fichier réel (même
symptôme que lors du chantier précédent). Les deux fois, la validation elle-même passait
trivialement puisqu'elle ne faisait que ré-exécuter la suite de tests existante sur du code
inchangé. Vérifier systématiquement `git diff --stat` après chaque job Talos avant de le
considérer comme terminé, quel que soit le statut renvoyé par `talos_status`.

## Plan 04bda1b4 — Menu principal global (v0.42.1+) : pilules, recherche unifiée, menu Parametres

Chantier séparé du contenu interne de Divertissement : porte sur la barre globale en haut d'écran
(Divertissement/Jeux/App + recherche + heure/date + engrenage), calquée sur le comportement du menu
d'accueil natif Kodi/Arctic Horizon 2 (capture de référence fournie).

### Phase 1 — Pilule expansion/collapse + focus par défaut

- Barre restructurée : module 0 = recherche (icône seule, jamais de pilule), modules 1-3 =
  Divertissement/Jeux/App (icône seule au repos, pilule dégradé bleu→turquoise + icône + libellé
  au focus), puis heure (gras) + date (`System.Date(ddd d mmm)`, format court pour tenir dans
  l'espace dispo) + bouton engrenage rond (icône générée, vraie forme d'engrenage — l'ancien
  `tab-settings.png` réutilisé pour l'onglet Paramètres s'est avéré être une icône de grille, pas
  un engrenage, une fois comparé au rendu réel).
- **Paramètres n'est plus un 4ᵉ onglet** : `config.TABS` réduit à 3 entrées, `TAB_BUTTON_IDS` à
  `(2001, 2002, 2003)`, l'ancien contenu "Parametres Akasha/Kodi" (boutons 2100/2101) supprimé —
  remplacé par le menu contextuel de la Phase 3. Le setting `tab.default` (qui proposait
  "Divertissement|Jeux|App|Parametres") est retiré : l'onglet actif n'est plus mémorisé entre les
  visites, conformément à la section 5 du cahier ("focus par défaut sur Divertissement à chaque
  arrivée sur l'écran", contrairement à l'ancien comportement qui restaurait le dernier onglet).
- Les sous-onglets Jeux (SteamLink/Moonlight/Autres) et App (Mes Apps/Store), auparavant ancrés
  dans la barre du haut à `left=900`, ont dû être déplacés dans la zone de contenu (`top=145`,
  même schéma que les onglets contextuels de Divertissement) : leur ancienne position entrait en
  collision avec les pilules élargies (jusqu'à `left=1200`).
- **Simplification délibérée** : les icônes voisines restent à une position de créneau fixe plutôt
  que de se rapprocher dynamiquement pour combler l'espace laissé par une pilule repliée (le
  "resserrement" des icônes voisines observé dans la référence native aurait demandé des
  animations de glissement conditionnelles par paire de contrôles — faisable en théorie avec
  seulement 3 modules, mais non retenu par manque de temps ; documenté ici plutôt qu'improvisé
  silencieusement).
- **Découverte de fond sur la navigation Kodi** (confirmée avec un label de debug
  `System.CurrentControlID`, à plusieurs reprises, avec redémarrage complet entre chaque essai
  pour écarter un artefact de timing) : un bouton **sans aucun** `<texturefocus>` ni `<label>` ni
  `<texture>` semble être silencieusement "sauté" par la résolution de focus native de Kodi pour
  Gauche/Droite, qui rebondit alors sur le contrôle suivant dans la chaîne `onleft`/`onright` — y
  compris quand le code Python tente de rediriger le focus lui-même juste après (le saut natif se
  produit avant que le script ne voie l'action, donc toute redirection Python s'additionne au saut
  natif au lieu de le remplacer, provoquant un double-saut). Ajouter un `texturefocus` même à peine
  visible (`colordiffuse="20FFFFFF"`) aux 3 boutons de module a suffi à rendre la boucle native
  Gauche/Droite (recherche ↔ module1 ↔ module2 ↔ module3 ↔ engrenage ↔ recherche) parfaitement
  fiable sans aucune logique Python de redirection — la gestion Python restante se limite à
  synchroniser `AuraActiveTab`/le contenu avec le module qui a effectivement le focus, jamais à
  déplacer le focus lui-même. Ceci reconsidère (sans l'invalider, faute de re-test) l'explication
  "géométrique" retenue pour le bug "Haut" du plan précédent (`f41ce1ad`) : la cause réelle pourrait
  être la même absence de `texturefocus` plutôt qu'une résolution géométrique — à garder en tête si
  un bug de navigation similaire réapparaît ailleurs dans le skin.
- Validé en direct : boucle complète Gauche/Droite sans aucun double-saut, focus par défaut sur
  Divertissement à chaque réouverture (y compris après un cycle Back-vers-natif complet), contenu
  synchronisé à chaque changement de module, sidebar/onglets internes de Divertissement inchangés.

### Phase 2 — Recherche unifiée (module 0)

Recherche groupée par catégorie (Films et séries / Jeux / Applications / Paramètres) via
`xbmc.Keyboard()` puis `xbmcgui.Dialog().select()` avec des en-têtes non sélectionnables
(`-- Categorie --`) — pas de fenêtre XML dédiée, cohérent avec l'esprit "pas une simple liste
inerte" du cahier tout en restant dans les mécanismes déjà éprouvés ailleurs dans l'addon.

- **Films/séries** : recherche `search()`/`section_items(search=...)` sur chaque bibliothèque
  Divertissement (pas de endpoint Plex "hub" global câblé dans `plex_client.py`/
  `connector_client.py` aujourd'hui, donc un aller-retour par bibliothèque plutôt qu'un seul appel
  global — acceptable avec le petit nombre de bibliothèques réelles). Sélectionner une série ouvre
  `AuraShowWindow` (voir bug corrigé ci-dessous) ; un film affiche la même notification-placeholder
  que le clic normal sur la grille (la résolution de lecture n'est toujours pas décidée, cf. plus
  haut dans ce fichier).
- **Jeux** : recherche sur `self._games` (raccourcis statiques déjà chargés à l'ouverture), pas sur
  le catalogue Steam/Sunshine complet (éviterait un aller-retour réseau à chaque recherche) —
  limitation de périmètre documentée plutôt qu'un vrai index de jeux complet.
- **Applications** : recherche sur les extensions installées (`Addons.GetAddons`) et sur le
  catalogue du Store (`store_manifest.py`) pour les non-installées ; sélectionner une app installée
  fait `RunAddon`, une app non installée bascule sur l'onglet App → Store.
- **Paramètres** : recherche sur les 6 entrées du menu contextuel de la Phase 3 (partagé via
  `_settings_menu_options()`), donc toute nouvelle entrée ajoutée au menu apparaît aussi dans la
  recherche sans code supplémentaire.
- **Bug réel trouvé et corrigé en testant cette phase** (affecte aussi le clic normal sur une série
  dans la grille Bibliothèque, pas seulement la recherche) : `AuraShowWindow.client` était toujours
  réglé sur `self._plex_client`, qui est `None` dès que le connecteur (`akasha-os-connector`) est
  utilisé à la place d'un accès Plex direct — `connector_client.py` n'implémente pas
  `show_seasons()`/`season_episodes()`. Résultat avant correctif : fenêtre de série qui s'ouvre
  mais reste bloquée sur des libellés vides ("-"), confirmé par
  `AttributeError: 'NoneType' object has no attribute 'show_seasons'` dans le log. Corrigé avec un
  repli propre vers la même notification-placeholder que pour les films quand aucun client Plex
  direct n'est disponible, factorisé dans une nouvelle méthode `_open_show()` réutilisée par les
  deux points d'entrée (grille et recherche). Étendre `connector_client.py` (et le backend
  `akasha-os-connector`, dépôt privé séparé) pour supporter saisons/épisodes reste hors périmètre
  de cette session.
- Validé en direct : recherche "a" → résultats groupés par catégorie corrects, sélection d'une
  série ("Angel Beats !") ouvre désormais `AuraShowWindow` sans planter (avant le correctif, plantait
  silencieusement en arrière-plan avec la fenêtre bloquée sur "-").

### Phase 3 — Menu contextuel Paramètres

Utilise `xbmcgui.Dialog().contextmenu()` (même mécanisme déjà utilisé par
`script.akasha.guide` pour son propre menu rapide) plutôt qu'une fenêtre XML personnalisée — hérite
gratuitement du placement standard du skin et de la fermeture sur sélection/Retour.

- 6 entrées dans l'ordre demandé : Paramètres Kodi (`ActivateWindow(Settings)`), Paramètres
  LibreELEC (`RunAddon(service.libreelec.settings)`, l'addon LibreELEC officiel confirmé installé
  sur l'appareil), Paramètres Akasha (`RunAddon(script.akasha.settings)`), Mise en veille (réutilise
  **exactement** le script `akasha-sleep.py` déjà utilisé par `script.akasha.guide`, pas de
  duplication), Redémarrer (sous-menu à 2 choix), Arrêt du système (confirmation + splash + CEC TV
  off, même séquence que `script.akasha.guide`/`script.akasha.settings`).
- **Redémarrer Akasha** : hypothèse retenue faute de mécanisme de relance applicative séparé du
  système (comme demandé de le documenter en section 8 du cahier si le cas se présentait) —
  `systemctl restart kodi`, exactement le même mécanisme que l'entrée "Redemarrer Akasha" déjà
  existante dans `script.akasha.guide`. Pas de nouveau mécanisme inventé.
- **Arrêt du système** : confirmation simple oui/non ajoutée comme hypothèse par défaut (cahier
  section 4, point 6), cohérent avec les autres actions destructives du même menu.
- Validé en direct : menu ouvert depuis Divertissement et depuis l'onglet App, les 6 entrées dans
  le bon ordre avec le header de branding Akasha déjà en place ailleurs dans le skin ; "Paramètres
  LibreELEC" testé pour de vrai (non destructif, ouvre le véritable écran de configuration
  LibreELEC) ; "Redémarrer" ouvre bien le sous-menu à 2 choix ; "Mise en veille" et "Arrêt du
  système" confirmés comme affichant leur boîte de confirmation respective, **jamais confirmés
  pour de vrai** pendant cette session (risque réel d'éteindre l'appareil du salon sans validation
  explicite de Jérémie, cf. `AGENTS.md`) — à valider par Jérémie lui-même en usage réel.

### Phase 4 — Alignement visuel

Fait au fil des itérations de la Phase 1 plutôt qu'en passe séparée : glyphes Unicode (▶/⇄/⋮)
abandonnés au profit de texte simple après un test réel montrant qu'ils ne s'affichent pas du tout
avec la police du skin (même leçon que sur le chantier `f41ce1ad`) ; icône engrenage regénérée
après avoir remarqué que l'ancienne (`tab-settings.png`) est en réalité une icône de grille ;
dégradé bleu→turquoise calé sur l'accent existant (`FF6C8CFF`) plutôt qu'une nouvelle palette,
conformément à la demande du cahier de réutiliser la charte déjà en place.

### Phase 5 — Recette finale

Parcours réel validé sur le Pi (PixelCamera + `kodi-send`/JSON-RPC) : arrivée sur Divertissement
par défaut → boucle Gauche/Droite complète sans double-saut → recherche groupée → menu Paramètres
(chaque entrée, sans confirmer les actions destructives) → retour propre après un cycle
Back-vers-natif/réouverture.

**Non fait / hypothèses à faire valider par Jérémie** :
- Test manette Xbox Wireless et télécommande IR/CEC physiques : aucun matériel disponible dans
  cette session à distance.
- "Mise en veille" et "Arrêt du système" jamais réellement exécutés pendant les tests (cf.
  ci-dessus) — leur code suit exactement les mêmes mécanismes déjà en production ailleurs dans
  l'OS, mais le déclenchement réel reste à faire par Jérémie.
- Le "resserrement" dynamique des icônes voisines quand une pilule s'étend (comportement visible
  dans la capture de référence native) n'est pas reproduit — espacement fixe à la place, documenté
  en Phase 1.
- La recherche ne couvre pas le catalogue Steam/Sunshine complet ni les épisodes individuellement
  (seulement Films/Séries au niveau bibliothèque, Jeux au niveau raccourcis statiques) — périmètre
  raisonnable pour une première version, à élargir si Jérémie le juge utile après usage réel.

### Correctif de fidélité visuelle (suite à retour direct de Jérémie)

Le premier rendu de la Phase 1/3 (pilule et bouton engrenage générés à la main) ne correspondait
pas d'assez près à l'apparence réelle du menu Arctic Horizon 2. Corrigé en allant lire directement
les fichiers du skin sur le Pi plutôt qu'en réapproximant :

- **Pilule** : `Includes_Objects.xml` (`Object_MenuBar_Item`/`_Object_MenuBar_Item`) donne la
  vraie structure (icône 60px avec un léger inset, texte à `textoffsetx=80`, fond en texture
  9-slice `border=80`). Le fond lui-même n'est pas un asset statique du skin mais généré à
  l'exécution par `script.texturemaker` d'après les couleurs choisies par l'utilisateur — récupéré
  directement depuis
  `/storage/.kodi/userdata/addon_data/script.texturemaker/ArcticHorizon/menumain_h.png` sur
  l'appareil (dégradé bleu `#0095E3` → turquoise `#00BCAA`, forme pilule avec ombre douce intégrée)
  et copié tel quel dans `resources/skins/Default/media/pill-gradient.png`, plutôt que régénéré
  par script. Conséquence acceptée : ne suit plus dynamiquement un changement de couleur d'accent
  Kodi côté utilisateur (comme le reste de la palette Aura, déjà fixe ailleurs).
- **Bouton Paramètres** : `Object_MenuButton` (même fichier) donne la vraie construction —
  ombre douce (`shadows/circle_shadow.png`, décalage -24, `border=54`) + cercle de fond teinté
  (`common/circle.png`, `border=30`) + léger surlignage (même cercle, teinte plus claire) + icône
  centrée. Les deux assets `circle.png`/`circle-shadow.png` copiés directement depuis
  `skin.arctic.horizon.2/media/` (formes géométriques génériques, pas de contenu créatif
  spécifique au skin). L'icône engrenage elle-même reste celle générée par PIL dans cette session
  (le vrai bouton du skin utilise une variable d'icône différente, potentiellement pas un
  engrenage littéral, moins clair pour "Paramètres" que le glyphe dessiné à la main).
- **Menu contextuel du bouton Paramètres** : déjà, avant ce correctif, rendu via
  `xbmcgui.Dialog().contextmenu()`, qui utilise `DialogContextMenu.xml` du skin — déjà patché avec
  le branding "Akasha OS" (logo œil, version) lors d'un chantier précédent, et dont l'item
  sélectionné reprend maintenant le même dégradé bleu→turquoise que les pilules. Positionnement
  centré à l'écran plutôt qu'ancré au bouton engrenage (comme le popup natif de la Home réelle,
  qui utilise un mécanisme différent — `Object_Options_Menu_Popup`, ancré via `right`/`top`
  seulement pour la Home elle-même, non réutilisable tel quel par un addon générique) — écart de
  positionnement accepté, la demande portait sur l'apparence (branding/couleurs), pas la position
  exacte.
- Validé en direct : les 3 pilules (Divertissement/Jeux/App) rendues avec le vrai dégradé et les
  bonnes proportions, bouton engrenage avec ombre+cercle+icône, menu contextuel avec le dégradé
  assorti sur l'item sélectionné.

## Corrections visuelles/fonctionnelles Divertissement (retour direct de Jérémie)

Quatre points corrigés en une passe, tous issus d'un retour direct après usage réel :

- **Coins arrondis (global)** : deux nouveaux assets 9-slice
  (`resources/skins/Default/media/rounded-solid.png`, cercle rempli blanc opaque dans un carré
  transparent, `border=16`) remplace `white.png` pour la quasi-totalité des boutons/cadres de
  focus/tuiles de tout l'addon (`Aura.xml`, `AuraApp.xml`, `AuraStore.xml`, `AuraShow.xml`) —
  colordiffuse continue de fonctionner normalement sur ce nouvel asset. Seuls les fonds plein
  écran/bandeau (qui n'ont pas de "cadre" à proprement parler) restent sur `white.png`. Les
  posters/vignettes eux-mêmes ne sont **pas** arrondis (Kodi n'a pas de mécanisme de masquage de
  texture arbitraire sans un overlay dont la couleur devrait suivre exactement ce qu'il y a
  derrière, focus ou pas — trop fragile pour le temps disponible) ; en pratique l'effet "moderne"
  recherché est déjà bien perceptible via les boutons, pilules, tuiles de catégories et cadres de
  focus autour des posters.
- **Recommandé — limite 100 éléments/ligne** : `paged_list.PagedList` accepte désormais un
  paramètre `max_items` optionnel (`None` par défaut = comportement inchangé partout ailleurs),
  appliqué uniquement aux 3 lignes de Recommandé (`RECO_MAX_ITEMS_PER_ROW = 100`). Bibliothèque
  n'est volontairement pas concernée (c'est le vrai parcours "toute la bibliothèque").
- **Recommandé — format poster** : les vignettes étaient quasi carrées (160x150). Corrigées en
  110x165 (ratio 2:3, un vrai format affiche/poster), proportions de ligne recalculées pour que
  les 3 lignes restent visibles sans scroll (comme avant).
- **Bibliothèque — grille au lieu d'une ligne** : contrôle 3230 passé de `<control type="list"
  orientation="horizontal">` à `<control type="panel">` (grille avec retour à la ligne, défilement
  vertical natif Kodi), hauteur portée à 660px (~2 rangées visibles). Un `<ondown>` explicite
  pointant sur le contrôle lui-même bloquait le défilement interne de Kodi au-delà de la 2e
  rangée (fonctionnait par hasard pour un simple changement de ligne, mais empêchait tout
  défilement au-delà de la zone visible initiale) — retiré, laissant Kodi gérer nativement le
  défilement à l'intérieur du panel.
- **Bibliothèque — chargement progressif** : `page_size`/`prefetch_margin` portés à 50 (au lieu de
  30/15 par défaut), et le déclenchement du chargement de la page suivante
  (`_maybe_load_more_divert`) étendu de Gauche/Droite à Haut/Bas/Gauche/Droite (la grille défile
  surtout verticalement désormais). **Simplification assumée** : il s'agit d'un chargement
  progressif vers l'avant uniquement (chaque page chargée reste en mémoire), pas d'une vraie
  fenêtre glissante avec déchargement des éléments déjà vus en remontant — les contrôles
  liste/panel de Kodi n'ont pas de mécanisme supporté pour retirer des éléments au milieu d'une
  liste déjà peuplée sans casser la position de défilement. Le résultat pratique (pas de
  chargement de la bibliothèque entière d'un coup, page suivante prête avant qu'on l'atteigne)
  correspond au besoin réel exprimé, documenté ici pour éviter toute ambiguïté sur ce qui a été
  implémenté.
- **Bibliothèque — bouton Rechercher retiré** : redondant avec la recherche unifiée du bandeau
  supérieur (module 0, plan `04bda1b4` phase 2). Bouton et gestionnaire (`_divert_open_search`)
  supprimés ; l'état `_divert_search_query` est conservé (toujours utilisé pour les clés de cache
  et la logique de filtre) mais plus aucune UI ne le renseigne pour l'instant.
- **Catégories — traduction française** : les agents Plex (TMDb/TheTVDB) renvoient les genres dans
  la langue de la base source (anglais par défaut), indépendamment de la langue de l'interface
  Akasha. Nouvelle fonction pure `divert_source.translate_genre_fr()` (dictionnaire EN->FR des
  genres standard TMDb/Plex, repli sur le nom original si absent de la table) appliquée
  uniquement à l'affichage — la valeur envoyée à l'API de filtre reste le nom original anglais
  (`_category_genres`), donc le filtrage par genre continue de fonctionner normalement.
- **Catégories — affichage amélioré** : tuiles agrandies (280x100 au lieu de 280x90), alignement
  du texte à gauche avec marge au lieu de centré (plus lisible), liseré coloré à gauche (4px,
  discret hors focus, couleur d'accent pleine au focus) pour un rendu "carte" plus travaillé que
  de simples rectangles pleins, coins arrondis (cf. point global ci-dessus).
- Nettoyage connexe : `aura_library.py`/`AuraLibrary.xml` (fenêtre séparée `AuraLibraryWindow`)
  étaient devenus du code mort depuis que Bibliothèque est rendue en ligne (chantier précédent) —
  plus aucune référence active, supprimés.
- Validé en direct sur le Pi : coins arrondis visibles sur boutons/pilules/tuiles/cadres de focus,
  lignes Recommandé avec vrais posters portrait, Bibliothèque en grille scrollable (défilement
  vertical confirmé bien au-delà des 2 premières rangées, chargement progressif sans erreur),
  bouton Rechercher absent, 33 genres Catégories tous (ou presque) traduits en français.

## Correctif c7f0636a — Regroupement des icônes du menu principal

Écart constaté par rapport à la référence Arctic Horizon 2 : sur Akasha Aura, seule l'icône Jeux
suivait directement la pilule du module focalisé ; l'icône App restait isolée avec un grand espace
vide au milieu, car les 3 modules (Divertissement/Jeux/App) étaient positionnés à des `<left>`
statiques espacés de 380px (assez pour loger la pilule de 340px sans chevaucher le voisin), créant
un vide de ~320px entre deux icônes repliées (56px) quel que soit le module réellement focalisé.

C'était déjà documenté comme une limitation acceptée du chantier `04bda1b4` ("neighbouring icons
stay at their fixed slot position rather than sliding"). Ce correctif revient sur cette
acceptation : implémenté un vrai repositionnement dynamique plutôt que de continuer à vivre avec
l'écart.

- Chaque pilule (groupe) et icône a désormais un id propre (`2101`/`2102` Divertissement,
  `2103`/`2104` Jeux, `2105`/`2106` App) — **attention** : ces ids ont dû être choisis en dehors de
  `2010-2012` (`GAME_BUTTON_IDS`) et `2030-2033` (`APP_TILE_IDS`), déjà utilisés par les tuiles de
  contenu des onglets Jeux/App — un premier essai avec `2011`/`2012`/`2021`/`2022`/`2031`/`2032`
  est entré en collision directe avec ces ids existants et a fait planter l'init d'Aura
  (`AttributeError: 'ControlImage' object has no attribute 'setLabel'`), détecté et corrigé avant
  la validation finale.
- `AuraWindow._layout_top_modules(focused)` recalcule à la main la position de chaque
  bouton/pilule/icône façon flexbox (largeur 340 si focalisé, 56 sinon, espacement fixe de 40px
  entre modules, départ à `x=160`) et les repositionne via `setPosition()` — appelée depuis
  `_update_bar_focused()`, elle-même déjà appelée après chaque action et à l'ouverture, donc pas de
  nouveau point d'accroche à ajouter.
- Validé en direct sur le Pi dans les 3 états (Divertissement/Jeux/App focalisé tour à tour) :
  le groupe reste contigu à chaque fois, sans espace anormal, et bascule proprement à la navigation
  Gauche/Droite.

## Recommandé et Catégories rendus en place (suite à retour direct de Jérémie)

Jérémie a signalé que sélectionner "Recommandé" ou "Catégories" donnait l'impression d'ouvrir une
autre page, contrairement à "Bibliothèque" qui s'affiche à l'emplacement prévu sans rien charger de
séparé. Vérification faite : c'était exactement le cas — `AuraRecommendationsWindow` et
`AuraGenresWindow` étaient encore des `xbmcgui.WindowXMLDialog` séparées, ouvertes via
`doModal()`, un reliquat des chantiers précédents (`780ecf80`/`f41ce1ad`) qui avaient déjà inliné
Bibliothèque dans `Aura.xml` mais pas ces deux-là.

Corrigé en supprimant entièrement `aura_recommendations.py`/`AuraRecommendations.xml` et
`aura_genres.py`/`AuraGenres.xml`, et en portant leur logique directement dans `aura_window.py`,
rendue inline dans `Aura.xml` (même mécanisme que Bibliothèque : un groupe avec `<visible>` sur
`Window.Property(DivertView)`/`DivertLibraryTab`) :

- **Recommandé** : 3 rangées (Continuer à regarder / Ajoutés récemment / Sorties récentes),
  visibles aussi bien pour Accueil (non scopé) que pour l'onglet Recommandé d'une bibliothèque
  précise — logique de fetch/pagination reprise à l'identique, réutilise
  `self._connector_client`/`self._plex_client`/`self._cache` déjà établis par
  `_load_divertissement()` au lieu de se reconnecter indépendamment comme le faisait l'ancienne
  fenêtre séparée.
- **Catégories** : grille de genres inline ; sélectionner un genre bascule maintenant directement
  sur l'onglet Bibliothèque **de la même fenêtre**, filtré sur ce genre (réutilise le mécanisme
  déjà existant du filtre "Genre" de la barre d'outils Bibliothèque), au lieu d'ouvrir une
  troisième fenêtre séparée (`AuraLibraryWindow`) comme avant — même motif de correction, cohérent
  avec la demande.
- Boutons d'onglet `Recommande`/`Categories` : leur `ondown` (qui pointait vers un placeholder mort
  `9000`, faute de contenu inline avant ce correctif) pointe maintenant vers la première rangée/le
  panneau de genres.
- Validé en direct : les trois onglets (Recommandé/Bibliothèque/Catégories) s'affichent maintenant
  tous de la même façon, dans la même fenêtre, sans aucune transition de type "nouvelle page" ;
  sélection d'un genre bascule bien vers Bibliothèque filtrée sans changer de fenêtre.

## Ne jamais prompter le mot de passe du Connector sur un démarrage automatique (2026-08-23)

**Bug trouvé en conditions réelles** : `_load_divertissement()` (appelée depuis `onInit()`, donc à
chaque ouverture d'Aura, y compris après un redémarrage Kodi automatique/sans personne devant
l'écran) appelait `_get_connector_client(prompt_if_missing=True)`. Tant qu'un `connector.session_token`
valide est stocké, ça ne fait rien de bloquant — mais dès que ce token est vide (premier réglage
jamais terminé, ou effacé par le mécanisme existant qui le vide après un `ConnectorAPIError`, par
exemple lors d'une coupure réseau/Unraid), le code tente un nouveau login et ouvre un
`xbmc.Keyboard` **bloquant** demandant le mot de passe — avec personne pour le saisir sur un
redémarrage non supervisé. Observé en production : après une coupure réseau ayant invalidé le
token, chaque redémarrage suivant de Kodi gelait Aura derrière "Mot de passe (Akasha OS Connector)"
jusqu'à ce que quelqu'un appuie manuellement sur Retour — perçu comme "le système est tout buggé".

**Corrigé** : `_load_divertissement()` appelle désormais `_get_connector_client(prompt_if_missing=False)`
— jamais de prompt bloquant sur un démarrage automatique, retombe silencieusement sur l'accès Plex
direct si le token est absent/invalide (comportement de repli déjà existant, inchangé). Une nouvelle
entrée explicite "Se connecter (Connector Akasha OS)" dans le menu contextuel de la roue crantée
(`_reconnect_connector()`) reste le seul point d'entrée qui passe `prompt_if_missing=True` — le seul
moment où un humain est réellement présent devant l'écran pour taper un mot de passe.

## Skeleton loaders pour la Bibliothèque et les rangées Recommandé (plan a3f9c2e1 phase 5, 2026-08-23)

Dernière phase (optionnelle) du plan de pagination `a3f9c2e1` : au lieu que la grille Bibliothèque
(`DIVERT_PANEL_ID`) ou les rangées Recommandé (`RECO_LIST_IDS`) s'arrêtent brutalement une fois les
éléments déjà chargés affichés, un nombre limité de silhouettes grisées ("skeleton loaders")
représente les éléments restants tant que le total réel (déjà connu via `PagedList.total`, fourni
par Plex sans requête supplémentaire) est supérieur à ce qui est chargé.

- `AuraWindow._sync_placeholders(control_id, current_placeholder_count, paged)` : supprime
  d'abord les anciens placeholders en fin de liste (`ControlList.removeItem`), puis en ajoute un
  nombre recalculé — plafonné à `PLACEHOLDER_ITEM_CAP` (50) quel que soit le nombre réel
  d'éléments restants, pour ne pas alourdir un contrôle avec des milliers d'items juste pour
  suggérer "il y en a plus" sur une très grosse bibliothèque. Respecte aussi `paged.max_items`
  (les rangées Recommandé sont plafonnées à 100 éléments, jamais plus, donc jamais plus de
  placeholders que ce plafond ne le permet).
- Chaque placeholder est un `ListItem('')` avec la propriété `IsPlaceholder=1`
  (`_build_placeholder_list_item()`), sans art ni label — le skin (`Aura.xml`, itemlayout des
  contrôles `3230`/`5110`/`5210`/`5310`) affiche à la place deux rectangles arrondis semi-
  transparents (silhouette poster + silhouette titre) via `<visible>` conditionné sur
  `ListItem.Property(IsPlaceholder)`, et masque le poster/label réels pour ces items.
- `_on_divert_item_selected()` était déjà protégé par `0 <= pos < len(self._divert_items)`,
  donc sélectionner un placeholder (au-delà des vrais éléments chargés) ne fait rien plutôt que
  planter — aucun changement nécessaire là.
- Défiler jusqu'à la zone des placeholders déclenche naturellement le chargement de la page
  suivante (le calcul de `PagedList.maybe_load_more()` compare déjà la position sélectionnée au
  nombre de *vrais* éléments chargés, pas à la taille visuelle du contrôle) — les placeholders
  disparaissent alors progressivement à mesure que de vrais éléments les remplacent.

## Akasha OS Store branché sur le vrai catalogue akasha-os-store (plan f4e069bb phases 3-4, 2026-08-23)

Le repo séparé `akasha-os-store` (structure, schéma, CI, 41 manifests) existait déjà avant cette
session (phases 1-2 du plan) — voir ce repo pour son propre historique. Cette section couvre le
branchement côté Aura.

- **`store_client.py`** (nouveau, pur/testable) : récupère `index.json` directement depuis le CDN
  GitHub Raw (`raw.githubusercontent.com/jeremiejt38/akasha-os-store/main/index.json`), avec un
  cache local (`/storage/.config/akasha-os/store-index-cache.json`) TTL 24h + `force_refresh` manuel,
  même patron que `weather_client.py` (Ambient). **Écart assumé par rapport au plan section 4.1**
  ("via akasha-os-connector pour la mise en cache/accélération") : le connector existe pour
  cacher/authentifier les métadonnées *Plex* multi-utilisateurs derrière un seul token admin —
  `index.json` est un JSON public, statique, déjà servi par un CDN, le faire transiter par le
  connector ajouterait un saut réseau et un endpoint hors-sujet sans bénéfice concret. À revoir si
  un besoin réel de cache côté connector apparaît en pratique.
- **`store_registry.py`** (nouveau, pur/testable) : registre local `/storage/.akasha/installed_store_apps.json`,
  clé = id du manifest (`tv.francetv`), valeur = `{version, installed_at, addon_id}`. `addon_id`
  (id Kodi réel, ex. `plugin.video.francetv`) n'est renseigné que pour les types `kodi-repo`/`zip-url`
  — c'est ce qui permet à `aura_app.py` de savoir si un addon installé dans Kodi vient du Store sans
  avoir à retélécharger l'index (`addon_id_to_store_id()`, table inverse construite depuis le
  registre seul).
- **`aura_store.py`** réécrit pour consommer `store_client`/`store_registry` au lieu de l'ancien
  manifest curé embarqué (`store_manifest.py`, conservé pour ses tests/rétrocompatibilité mais plus
  utilisé ici). Dispatch par `install.type`, délibérément prudent (voir la docstring du module pour
  le détail) :
  - `kodi-repo` → `InstallAddon(addon_id)` natif Kodi, identique à l'ancien comportement — marche
    directement pour un addon du dépôt officiel Kodi, échoue proprement (notification native Kodi,
    pas de crash) pour un dépôt tiers pas encore ajouté à cette instance.
  - `zip-url` → téléchargement + vérification sha256, puis même tentative `InstallAddon` best-effort.
    Aucun des 41 manifests actuels n'utilise ce type.
  - `script`/`external-app` → **jamais d'exécution automatique d'un champ du manifest** : affichage
    d'une fiche informative (`textviewer`) uniquement, conforme à la V1 du plan. Choix délibéré de
    sécurité : automatiser "exécuter un script arbitraire venant d'une URL de manifest" sans conception
    ni tests dédiés aurait été irresponsable.
  - Ajouter automatiquement un dépôt Kodi tiers inconnu (au lieu de se contenter d'installer un
    `addon_id` déjà résolu) n'est **volontairement pas automatisé** : Kodi garde délibérément ce geste
    derrière le bouton "Sources inconnues" + son propre gestionnaire de fichiers comme barrière de
    sécurité ; le contourner sans supervision n'est pas dans le périmètre de cette première version.
- **`aura_app.py`** : **question produit ouverte, non tranchée unilatéralement**. Le plan section 5
  demande que "Mes Applications" n'affiche *que* les apps installées via le Store et toujours
  présentes dans l'index — un filtre strict qui masquerait tout addon installé autrement. Comme
  l'onglet "Mes Apps" actuel (Milestone 5, déjà en production) affiche aujourd'hui *tous* les addons
  installés (utile pour la gestion générale), remplacer ce comportement par le filtre strict aurait
  été un vrai changement de UX à trancher avec Jérémie plutôt qu'une décision prise seul, de nuit, sans
  pouvoir vérifier visuellement sur l'appareil réel. Implémenté à la place : chaque addon installé via
  le Store est marqué (badge `[Store]` dans le label, propriété `fromstore` sur le ListItem pour un futur
  habillage skin) sans rien masquer. Le filtre strict lui-même (`store_registry.visible_app_ids()`,
  déjà écrit et testé) est prêt à être branché dès que ce point est tranché. La tuile logo + titre au
  survol (habillage visuel demandé par la phase 4) reste aussi à faire : un changement de skin XML sur
  ce composant nécessite une boucle de vérification visuelle en direct, indisponible cette nuit
  (voir l'incident réseau documenté plus bas).
- **Phase 5** : le catalogue complet de 41 entrées a été parcouru en direct sur le Pi le 2026-08-27
  (41 libellés uniques). Les 34 `external-app` disposent désormais d'un flux installable sous forme
  d'app web Chromium ; les manifests `kodi-repo` restent traités comme des addons Kodi.

## Applications web `external-app` — lancement via Chromium sans exécuter de scripts arbitraires

Le manifest du Store supporte un type `external-app` (applications web qu'on ne veut pas embarquer
en tant qu'addon Kodi). Cette session implémente un mécanisme **sûr et générique** pour les
enregistrer, les afficher et les lancer, en réutilisant le lanceur cloud-gaming existant.

- **Validation stricte des URL** (`store_external.py`, pur/testable) : seuls les schémas `http` et
  `https` avec un hôte sont acceptés pour `source_url` et `deep_link`. Tout autre schéma
  (`javascript:`, `file:`, `data:`, chemin relatif, etc.) est rejeté avant stockage ou lancement,
  afin de ne jamais exécuter un script arbitraire ou charger une ressource locale sensible.
- **Installation = enregistrement local uniquement** : pour `external-app`, l'installation écrit
  simplement une entrée dans `/storage/.akasha/installed_store_apps.json` via
  `store_registry.record_install()`. Aucun fichier n'est exécuté automatiquement, aucun paquet n'est
  téléchargé. Le bloc `install` original (source_url + deep_link) est conservé dans le registre pour
  le lancement ultérieur, même hors ligne.
- **Affichage dans Aura App** (`aura_app.py`) : les apps `external-app` sont ajoutées sous forme
d'addons synthétiques (`external:<store_app_id>`) **à côté de l'inventaire complet des vrais addons
installés**. Aucun filtrage strict n'est appliqué : l'utilisateur a explicitement demandé de garder
la vue "toutes les applications". Les apps externes portent un badge `[Web]` pour les distinguer.
- **Lancement Chromium** : `store_external.launch_command_args()` réutilise le script
  `/storage/.kodi/scripts/cloud-gaming/launch.sh` existant, donc le watchdog manette (retour à Kodi)
  et le redémarrage de Kodi sont identiques au cloud-gaming. Le processus est détaché via
  `systemd-run`, comme dans `script.cloud.gaming/default.py`, pour survivre à l'arrêt de
  `kodi.service`.
- **Corrections de la chaîne Chromium** : l'argument `URL` était précédemment ignoré (`""` en fin
  de commande), le binaire demandé (`chromium-browser`) n'existait pas dans l'image, `docker run -it`
  échouait sous `systemd-run` sans TTY, le PATH systemd ne contenait pas le client Docker LibreELEC,
  et l'`ENTRYPOINT` de l'image était mal formé. Le lanceur utilise maintenant le chemin Docker absolu,
  fonctionne sans TTY, monte l'entrypoint corrigé et transmet l'URL à `chromium`. Le watchdog utilise
  lui aussi le chemin Docker absolu.
- **Désinstallation** : pour une app `external-app`, le bouton "Désinstaller" supprime
  **uniquement l'entrée du registre** ; il n'y a aucun vrai addon Kodi à retirer. Pour les types
  `kodi-repo`/`zip-url`, le comportement existant (fenêtre `AddonInformation` native + suppression
  du registre) est conservé.
- **Différenciation dans le Store** (`aura_store.py`) : le Store n'ayant qu'un simple clic sur la
  liste, un menu contextuel natif est utilisé pour `external-app` : **Installer / Voir les détails**
  quand non installé, **Lancer / Voir les détails / Désinstaller** quand installé. C'est la
  distinction la plus cohérente possible avec les contrôles existants.
- **Tests** : `tests/test_store_external.py` couvre la validation d'URL, la construction d'addons
  synthétiques, le filtrage/sortie du registre et le montage de la commande de lancement. En direct
  sur le Pi, Amazon Music a été enregistré via le menu Store, retrouvé dans Mes Applications avec
  le badge `[Web]`, lancé dans le conteneur Chromium, puis le conteneur a été arrêté de façon
  contrôlée avec retour automatique à Kodi. Le registre a ensuite été nettoyé. Les 7 manifests
  `kodi-repo` ont également été vérifiés : leurs 6 addons uniques sont installés et activés
  (YouTube est référencé par deux manifests). SoundCloud 4.1.0 et Catch-up TV & More
  0.2.41+matrix.1 ont été installés pendant le test ; les quatre autres étaient déjà présents et
  n'ont pas été désinstallés. Kodi ne fournissant aucune API publique de désinstallation, les deux
  petits addons de test restent installés plutôt que de contourner la confirmation native.

## Alignement global sur l'accueil Arctic Horizon 2 (2026-08-28)

Nouvelle comparaison effectuée directement avec l'accueil Arctic Horizon 2 installé sur le Pi, à partir d'une capture réelle et de ses fichiers `Home.xml`/`Includes_Objects.xml`. Aura reprend désormais sa composition globale plutôt que seulement ses textures : barre persistante, fond noir uniforme, modules compacts et contigus, icônes 60 px, pilule focalisée de 320 px, typographie plus fine et contenus alignés à 60 px du bord. Le fond de pilule est étiré comme une image 320x80 centrée autour du contrôle plutôt qu'en 9-slice avec `border=80` dans une boîte haute de 60 px : cette ancienne combinaison invalide déformait la texture, la collait au bord supérieur et la décalait par rapport au logo.

La sidebar Divertissement est entièrement masquée hors focus puis glisse au premier plan sur `Left`, supprimant la bande résiduelle visible à l'écran. Les onglets contextuels remontent sous la barre principale, les trois rangées Recommandé utilisent des posters 130x195 plus proches de la densité AH2 et les sous-titres secondaires sont masqués pour éviter une double ligne illisible. Validé visuellement sur le Pi avec de vraies données Plex ; navigation et chargement restent inchangés.
