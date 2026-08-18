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
