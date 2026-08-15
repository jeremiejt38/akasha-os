# Mode Ambiant — Décisions techniques

## Screensaver addon natif plutôt qu'un service custom

**Choix** : `screensaver.akasha.ambient`, extension `xbmc.ui.screensaver`.

**Alternative écartée** : un service (`service.akasha.ambient`) qui surveillerait lui-même
`xbmc.getGlobalIdleTime()` et ouvrirait une fenêtre custom.

**Raison** : Kodi gère déjà nativement l'inactivité, la temporisation (`screensaver.time`,
déjà utilisé par Akasha Settings), la désactivation sur interaction, et l'exclusion pendant la
lecture vidéo/audio. Réimplémenter cette détection dans un service dupliquerait une fonctionnalité
déjà fournie et fiable. Le patron `xbmcgui.WindowXMLDialog` + `xbmc.Monitor` est le même que celui
déjà utilisé pour `Guide.xml`, donc cohérent avec le reste du code.

## Rotation d'images via le contrôle natif `multiimage`

**Choix** : le fond du Mode Ambiant est un contrôle skin `<control type="multiimage">` pointant
vers le dossier configuré, avec fondu enchaîné et ordre aléatoire natifs.

**Alternative écartée** : une classe `ContentManager` Python qui construirait elle-même la playlist
et appellerait `setImage()` sur un timer.

**Raison** : `multiimage` fait déjà tout ce dont le MVP a besoin (rotation, anti-répétition
immédiate, fondu) sans code Python, ce qui réduit la surface de bug sur un composant visible en
continu. Un `ContentManager` Python reste utile pour la logique testable indépendamment du skin
(validation de dossier, repli sur le contenu de secours) : voir `resources/lib/content_manager.py`.

## Pas de pack de photos par défaut embarqué

**Choix** : si le dossier de contenu est vide, repli sur `akasha-os-splash-screen.png` déjà présent
dans le repo.

**Alternative écartée** : télécharger/embarquer un pack de paysages "libres de droits" par défaut.

**Raison** : embarquer des assets binaires tiers dans le repo sans vérification de licence au cas
par cas serait risqué, et gonflerait le dépôt Git (pas de Git LFS configuré). Le repli sur un asset
déjà possédé par le projet est immédiat, sans risque de licence, et suffit à éviter un écran vide.
Un pack par défaut correctement sourcé est noté dans `roadmap.md` comme amélioration future,
téléchargée à l'installation plutôt que commitée.

## Horloge sans code Python

**Choix** : labels skin utilisant les info-labels natifs `$INFO[System.Time]` / `$INFO[System.Date]`.

**Raison** : Kodi les fournit déjà formatés et localisés ; un module `ClockProvider` séparé n'aurait
aucune valeur ajoutée pour la v0.12.

## Météo Open-Meteo, pas de vraie détection de luminosité matérielle

**Choix** : client HTTP minimal (stdlib `urllib`, pas de dépendance externe) vers Open-Meteo, cache
JSON local, ville configurée manuellement (pas de géolocalisation automatique).

**Raison** : pas de clé API à gérer/protéger, cohérent avec l'esprit "pas de dépendance cloud" de la
spec d'origine. La géolocalisation automatique est reportée (complexité et confidentialité) au
profit d'une ville saisie manuellement, comme le recommande explicitly la spec elle-même
(section 12.2).

## Assombrissement simulé, pas de contrôle de rétroéclairage matériel

**Choix** : calque noir semi-transparent (`colordiffuse` piloté par une propriété de fenêtre).

**Raison** : Akasha OS pilote un Raspberry Pi connecté en HDMI à une TV externe ; il n'existe pas de
rétroéclairage local à contrôler (contrairement à un écran de tablette/laptop). Le seul contrôle
d'énergie réel disponible côté TV est CEC (marche/veille), déjà couvert par `akasha-sleep.py`.

## Anti-marquage par presets de position (réutilise le patron `Guide.xml`)

**Choix** : le bloc horloge/météo bascule entre 4 presets de coin toutes les 10 minutes, via
`Window.Property` + groupes conditionnels dans le skin — même mécanisme que
`AkashaGuidePreset` dans `Guide.xml`.

**Alternative écartée** : décalage pixel-par-pixel dynamique via des valeurs numériques calculées en
Python et injectées dans les coordonnées du skin.

**Raison** : les balises de position (`<left>`, `<top>`) de Kodi n'évaluent pas de manière fiable des
info-labels numériques dynamiques à chaque frame ; un système de presets discrets, déjà utilisé et
validé dans ce projet, est plus robuste et suffisant pour l'objectif anti-marquage.

## Vidéos d'ambiance en boucle : reportées

**Raison** : nécessitent un contrôle `videowindow` dédié, un pipeline de lecture différent du
`multiimage`, et plus de validation sur un Raspberry Pi 4 2 Go (décodage vidéo simultané avec le
reste du système). Reporté à une version ultérieure une fois le socle image validé sur le device.

## Réutilisation de `akasha-sleep.py` pour l'état SLEEP

**Choix** : après `sleep_after_seconds`, appel de
`xbmc.executebuiltin('RunScript(/storage/.kodi/scripts/akasha-sleep.py)')`, puis fermeture de la
fenêtre Ambient.

**Raison** : évite de dupliquer la séquence CEC standby + veille + réveil-sur-interaction déjà
implémentée et validée. Utilisation du builtin `RunScript` plutôt que
`subprocess.Popen([sys.executable, ...])`, suite au bug découvert sur
`script.akasha.guide/default.py` où `sys.executable` ne pointait pas vers un interpréteur Python
utilisable depuis le runtime Kodi embarqué.
