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

### Points ouverts pour les phases suivantes

- Le contenu réel des étapes 2 à 9 (voir plan, phases 2 à 6) n'est pas encore implémenté — chaque
  étape n'affiche qu'un titre.
- L'étape Réseau devra réutiliser l'écran "Connexions" de `service.libreelec.settings` (liste
  Wi-Fi + connexion), pas le réimplémenter — voir `docs/settings/decisions.md` (audit plan
  `a5a87f03`) qui a confirmé que c'est là, et pas dans les réglages réseau Kodi natifs, que vit le
  vrai statut de connectivité.
- L'étape Manette/Télécommande devra réutiliser l'onglet "Bluetooth" du même addon LibreELEC
  Settings pour l'appairage, et `input.controllerconfig` (réglages Kodi natifs) pour le mapping.
