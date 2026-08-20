# Akasha Quick Start — Décisions techniques

## Plan 3aba4284 — Phase 1 : socle technique de l'assistant

Nouvel addon `script.akasha.quickstart`, structure calquée sur les addons `script.akasha.*`
légers déjà en place (`script.akasha.guide` : `default.py` racine + `resources/skins/Default/`),
avec un `resources/lib/` pour la logique testable sans dépendance `xbmc*`
(`quickstart_state.py`, testé via `python3 -m unittest`).

- **Détection premier démarrage** : fichier marqueur
  `/storage/.config/akasha-os/quickstart-completed` (même convention que le reste d'Akasha OS —
  VERSION, update-status.json). Posé **uniquement** par `QuickStartWindow._finish()`, appelé
  uniquement depuis le bouton "Terminer" de la dernière étape (Récapitulatif) — une sortie
  anticipée (Back + confirmation) ne pose jamais le marqueur, conformément à la section 1 du
  cahier.
- **Déclenchement au démarrage** : `service.akasha.aura/service.py` (le lanceur déjà existant qui
  ouvre Aura au boot) vérifie ce marqueur avant de choisir quoi lancer : absent → 
  `RunScript(script.akasha.quickstart)`, présent → `RunScript(script.akasha.aura)` comme avant.
  Le chemin du marqueur est dupliqué en constante dans `service.py` plutôt qu'importé depuis
  l'addon quickstart (import cross-addon fragile pour une seule constante de chemin).
- **Relance manuelle** : nouvelle entrée dans le menu `script.akasha.settings` ("Assistant de
  configuration" → "Relancer l'assistant de premier demarrage (Quick Start)"), qui lance
  toujours l'assistant **sans condition** (ignore le marqueur) — `default.py` de l'addon
  quickstart lui-même ne connaît d'ailleurs pas le marqueur du tout : c'est uniquement à
  l'appelant (lanceur de boot vs. entrée manuelle) de décider s'il faut vérifier le marqueur
  avant d'invoquer le script, séparation des responsabilités volontaire.
- **Navigation générique** : `QuickStartWindow` gère `self.step` (0-9), `Window.Property(QSStep)`
  pilote la visibilité du groupe de contenu de chaque étape dans `QuickStart.xml` (même
  technique que les onglets contextuels d'Aura). Boutons Précédent/Suivant/Passer génériques,
  visibilité de Passer pilotée par `quickstart_state.is_skippable()` (Bienvenue/Réseau/
  Récapitulatif non skippables, conformément à la section 3). "Suivant" devient "Terminer" sur
  la dernière étape.
- **Sortie anticipée** : `Back` ouvre une confirmation `xbmcgui.Dialog().yesno()` avant de fermer
  — fermer sans confirmer ne pose jamais le marqueur (donc l'assistant se représente au
  prochain démarrage), cohérent avec la section 1.
- **10 étapes** : Phase 1 ne construit que le squelette (titre placeholder par étape) ; le
  contenu réel de chaque étape (scan Wi-Fi, test d'affichage, appairage manette, liaison de
  comptes...) sera ajouté phase par phase (2 à 6 du cahier) sans toucher à cette ossature de
  navigation.

### Validé en direct sur le Pi

- Premier démarrage (marqueur absent, addon neuf) : l'assistant s'affiche bien à la place d'Aura.
- Navigation Suivant/Précédent/Passer sur plusieurs étapes, y compris l'absence du bouton
  "Passer" sur l'étape Réseau (non-skippable).
- Confirmation d'abandon sur `Back` (dégradé de la charte Akasha repris sur le bouton "Oui" du
  dialogue natif, cohérent visuellement).
- "Terminer" sur l'étape Récapitulatif : marqueur posé (`ls` confirmé sur le fichier), puis
  enchaînement automatique vers Akasha Aura.
- Redémarrage complet de Kodi après complétion : Aura s'ouvre directement, plus l'assistant
  (confirmé via le log `Akasha Aura Launcher: opening Akasha Aura`).
- Relance manuelle depuis `Paramètres Akasha` après une complétion déjà faite : l'assistant se
  relance bien depuis "Bienvenue", sans reposer sur l'état du marqueur.

## Phases 2 à 6 : contenu réel de toutes les étapes (suite à demande explicite de Jérémie)

Sur demande explicite ("termine toutes les phases manquantes"), le contenu réel des étapes 2 à 9
a été implémenté en une passe (plutôt que phase par phase séparément), avec pour principe : chaque
action a un effet réel (vrai réglage Kodi modifié via JSON-RPC, vraie connexion réseau via
`connmanctl`, vrai renvoi vers l'écran natif/addon concerné), jamais un simple habillage
cosmétique.

### Nouveau : progression persistée par étape

Le cahier (section 1) exige une "sauvegarde progressive" — une interruption ne doit pas forcer à
tout recommencer. Ajouté `quickstart_state.save_step()`/`get_last_step()` (fichier
`/storage/.config/akasha-os/quickstart-last-step`, même convention que le marqueur de complétion) :
chaque avancée d'étape le met à jour ; une relance automatique (au boot, marqueur "completed"
absent) reprend à la dernière étape sauvegardée au lieu de repartir de Bienvenue. La relance
**manuelle** (`_relaunch_quickstart()` dans `script.akasha.settings`) passe un argument `restart`
à `RunScript` pour forcer un vrai redémarrage depuis Bienvenue à la place — cohérent avec l'intention
d'une reconfiguration complète volontaire.

### Étape 2 — Langue et région

- Langue de l'interface : vraie liste des paquets de langue installés (`Addons.GetAddons` type
  `kodi.resource.language`) + application réelle (`Settings.SetSettingValue locale.language`).
- Région/fuseau/format date-heure : bouton dédié vers l'écran Kodi natif (`interfacesettings`,
  `Region` -- Kodi ne propose pas de fuseau horaire séparé du système sur cette distribution ;
  `timedatectl` est présent mais son service D-Bus ne l'est pas sur ce LibreELEC, donc pas de
  vraie API de changement de fuseau accessible sans risque, délégué au natif plutôt qu'improvisé).

### Étape 3 — Connexion réseau (bloquant)

Nouveau module pur `quickstart_network.py` (testé unitairement, sans dépendance xbmc) :
- Détection réelle : présence d'un lien Ethernet (`/sys/class/net/*/carrier`) + **vrai test de
  connectivité internet** (requête HTTP réelle, pas juste "a une IP"), conformément à la section 3.
- Scan/liste Wi-Fi réels via `connmanctl scan wifi` + `connmanctl services` (LibreELEC utilise
  connman, pas les réglages réseau Kodi -- confirmé dans l'audit `a5a87f03`). Format de sortie de
  `connmanctl services` parsé avec une regex sur le suffixe `(ethernet|wifi)_...` plutôt qu'un
  split naïf, pour gérer les noms de réseaux contenant des espaces.
- Connexion réelle via l'agent non-interactif de `connmanctl` (mot de passe transmis sur stdin).
  **Non exécutée en conditions réelles pendant cette session** (le Pi de test a déjà Ethernet, se
  connecter à un vrai réseau Wi-Fi voisin pour tester aurait modifié la configuration réseau réelle
  de l'appareil sans nécessité) -- code écrit et relu avec soin, mais ce chemin spécifique
  (saisie du mot de passe + `connect`) reste à valider en conditions réelles par Jérémie.
- "Suivant" bloqué tant que la connectivité réelle n'est pas confirmée (seule étape non
  skippable avec un blocage actif, conforme à la section 3).

### Étape 4 — Affichage et son

- Résolution : liste réelle des résolutions disponibles (Kodi), application réelle, puis
  confirmation avec "Revenir en arrière" par défaut et fermeture automatique à 10s
  (`xbmcgui.Dialog().yesno(..., autoclose=10000)`) qui revient à la résolution précédente si
  l'utilisateur ne confirme pas -- même filet de sécurité que l'écran natif Kodi.
- Sortie audio : liste réelle des périphériques détectés, application réelle.
- Synchronisation veille TV (CEC) : réutilise le même réglage réel que "Mode extinction : Shutdown
  + CEC" de `script.akasha.settings` (`powermanagement.shutdownstate=0`), via JSON-RPC direct
  plutôt qu'un import cross-addon (non supporté).
- Test de son avec fichier audio dédié : **non implémenté** (aucun asset audio de test n'est
  fourni avec l'addon) -- écart assumé par rapport au cahier, documenté plutôt que simulé.

### Étape 5 — Manette et télécommande

- Test télécommande : réellement interactif, chaque direction pressée (Haut/Bas/Gauche/Droite/OK)
  s'affiche en direct via `onAction()`.
- Appairage manette Bluetooth : renvoie vers l'onglet Bluetooth de `service.libreelec.settings`
  (seul chemin réel pour l'appairage BLE interactif) -- **pas** `ActivateWindow(peripheralsettings)`
  qui fait planter Kodi de façon reproductible sur ce matériel (voir `docs/settings/decisions.md`).

### Étape 6 — Comptes de contenu

Chaque service (Plex/Jellyfin/YouTube Music) ouvre son propre écran de compte natif
(`RunAddon`), skippable individuellement (aucun blocage). Comme pour les écrans Kodi natifs, ferme
l'assistant avant d'ouvrir l'addon (ces écrans ne sont pas garantis d'être des dialogues qui
s'empilent) -- reprend à cette même étape au retour grâce à la progression persistée.

### Étape 7 — Cloud gaming

Choix multiple réel (`xbmcgui.Dialog().multiselect`, présélection conservée si on rouvre le
dialogue) parmi les 6 services du cahier. Le choix est écrit dans un réglage de
`script.akasha.aura` (`quickstart.cloud_gaming_services`) -- **la lecture de ce réglage pour
pré-activer les tuiles du module Jeux n'est pas encore branchée côté `aura_window.py`** (écart
assumé, documenté ici plutôt que fait à moitié : la valeur est bien sauvegardée et réellement
disponible, mais rien ne la consomme encore pour filtrer/pré-cocher les raccourcis Jeux).

### Étape 8 — Préférences énergie

Réutilise les réglages réels déjà utilisés par `script.akasha.settings` (`screensaver.time`,
`powermanagement.shutdowntime`/`shutdownstate`) via JSON-RPC direct -- mêmes valeurs, même effet,
lues et écrites en direct (confirmé en test : les vraies valeurs actuelles du système s'affichent).

### Étape 9 — Profil utilisateur

Aucune méthode JSON-RPC ne crée un profil (`Profiles.*` est en lecture seule :
GetProfiles/GetCurrentProfile/LoadProfile) -- seul l'écran natif Kodi (`profilesettings`,
confirmé sûr dans l'audit `a5a87f03`) permet réellement d'en créer un. Délègue donc à cet écran
(ferme l'assistant d'abord, reprend à cette étape au retour) plutôt que de simuler la création.

### Étape 10 — Récapitulatif

Généré dynamiquement à partir des choix réels faits pendant le parcours (`self.results`), pas un
texte statique -- validé en direct : réseau détecté, télécommande testée, services cloud gaming
choisis apparaissent correctement dans le résumé final.

### Bug de navigation corrigé : "Haut" depuis le pied de page

Les boutons Précédent/Passer/Suivant sont partagés entre toutes les étapes (XML statique), mais
chaque étape a un premier bouton de contenu différent -- impossible d'exprimer ça avec un simple
`<onup>` statique. Un `<onup>` en boucle sur soi-même empêchait toute remontée au clavier/manette
depuis le pied de page vers le contenu de l'étape. Corrigé via un `onAction()` Python qui redirige
explicitement le focus vers le premier contrôle de l'étape courante quand "Haut" est pressé depuis
l'un des 3 boutons de pied de page.

### Validé en direct sur le Pi

Parcours complet Bienvenue → Langue (vrai sélecteur, langue actuelle "fr_fr" bien lue) → Réseau
(vraie détection "Ethernet" affichée) → Affichage/son → Manette/télécommande → Comptes → Cloud
gaming (vrai choix multiple, persistance confirmée en rouvrant le dialogue) → Énergie (vraies
valeurs 30 min affichées) → Profil → Récapitulatif (contenu 100% dynamique et exact) → Terminer
(marqueur de complétion posé, marqueur d'étape supprimé, enchaînement vers Aura confirmé). Aucune
erreur dans les logs Kodi sur l'ensemble du parcours.

### Points ouverts restants

- Connexion Wi-Fi effective (saisie mot de passe + `connmanctl connect`) non exercée en conditions
  réelles (voir étape 3 ci-dessus) -- à valider par Jérémie avec un vrai réseau à portée.
- Le choix de services cloud gaming (étape 7) est sauvegardé mais pas encore consommé par le
  module Jeux d'Aura pour pré-activer/filtrer les tuiles -- prochaine étape naturelle si Jérémie le
  souhaite.
- Pas de fichier audio de test bundlé pour l'étape 4 (test de son).
- Tests manette Xbox Wireless et télécommande IR/CEC physiques non faits (accès distant
  uniquement, comme pour les chantiers précédents).
