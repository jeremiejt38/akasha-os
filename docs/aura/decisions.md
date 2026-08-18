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
