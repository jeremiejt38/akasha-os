# Mode Ambiant — Spécification fonctionnelle (Akasha OS v0.12)

> Reformulation de la spécification fournie par le mainteneur, adaptée à l'architecture réelle
> d'Akasha OS (Kodi 21 / LibreELEC sur Raspberry Pi 4, pas de moteur de rendu natif Qt/Vulkan/Rust).
> Le document original (générique, multi-plateforme) reste la référence produit ; ce fichier décrit
> ce qui est **réellement livré en v0.12** et comment.

## 1. Présentation

Le Mode Ambiant transforme l'écran en diaporama/horloge/météo lorsque l'appareil n'est plus utilisé,
comme étape intermédiaire entre l'utilisation normale et la mise en veille CEC déjà en place
(`kodi/scripts/akasha-sleep.py`). Objectifs repris de la spec d'origine : immersif, lent, peu
intrusif, personnalisable, économe, compatible anti-marquage, fonctionnel hors-ligne.

## 2. Choix d'architecture

Akasha OS est un ensemble d'addons Kodi (scripts Python + skins XML) déployés sur LibreELEC, pas un
système avec un moteur de rendu propre. Le Mode Ambiant est donc implémenté comme un **addon
screensaver Kodi natif** (`extension point="xbmc.ui.screensaver"`), et non comme un service
qui réinventerait la détection d'inactivité :

- Kodi gère nativement l'inactivité (`screensaver.time`, déjà exposé dans Akasha Settings) et
  l'activation/désactivation du screensaver — pas besoin d'un `InactivityMonitor` maison.
- Le rendu passe par une fenêtre `xbmcgui.WindowXMLDialog` définie en skin XML
  (`resources/skins/Default/1080i/Ambient.xml`), sur le même modèle que `Guide.xml`.
- Le retour à l'usage normal ("réveil immédiat", recommandé par la spec pour une TV) est géré par
  Kodi lui-même : toute entrée utilisateur ferme le screensaver — l'addon écoute juste
  `xbmc.Monitor.onScreensaverDeactivated()` pour se fermer proprement.
- La mise en veille complète (état `SLEEP` de la spec) réutilise directement
  `akasha-sleep.py` (CEC standby + réveil sur interaction), sans dupliquer cette logique.

Voir `decisions.md` pour le détail des choix techniques et leurs alternatives écartées.

## 3. États retenus pour la v0.12

| État de la spec | Portage Kodi |
|---|---|
| `ACTIVE` | Interface Kodi normale ; hors screensaver. |
| `COUNTDOWN` | Géré par Kodi (`screensaver.time`) — pas de logique addon. |
| `TRANSITION_IN` | `onInit()` de la fenêtre Ambient : fondu d'entrée (animation skin `WindowOpen`). |
| `AMBIENT_ACTIVE` | Boucle principale de la fenêtre : diaporama, horloge, météo, anti-marquage. |
| `DIMMED` | Overlay noir semi-transparent dont l'opacité augmente après `dim_after_seconds`. |
| `SLEEP_PENDING` / `SLEEP` | Après `sleep_after_seconds`, déclenche `akasha-sleep.py` puis ferme la fenêtre. |
| `TRANSITION_OUT` | Géré par Kodi (fermeture du screensaver sur interaction) + animation `WindowClose`. |
| `Réveil` | Natif Kodi (réveil immédiat) + réveil CEC déjà géré par `akasha-sleep.py`. |

## 4. Déclenchement (portée v0.12)

- **Inactivité** : `screensaver.time` (Kodi natif), configurable depuis Akasha Settings (déjà
  existant).
- **Manuel** : nouvelle entrée dans le menu Akasha Guide ("Mode Ambiant") qui appelle
  `ActivateScreensaver`.
- Reportés à une version ultérieure : activation programmée par plage horaire, déclenchements liés
  à des événements applicatifs (fin de film, appel...), détection de présence (caméra/capteur).

## 5. Cas de non-activation

Géré nativement par Kodi (`screensaver.disableforaudio`, pas d'activation pendant la lecture vidéo
sauf `usedimonpause`). Pas de logique additionnelle nécessaire en v0.12.

## 6. Contenu affiché (portée v0.12)

- **Images locales uniquement** pour le MVP (pas de vidéo en boucle ni de sources cloud).
- Rotation et fondu enchaîné gérés par le contrôle natif Kodi `multiimage` (aléatoire, anti-répétition
  native, pas de logique Python nécessaire pour la rotation elle-même).
- Dossier par défaut : `/storage/ambient/photos`, configurable depuis les réglages de l'addon.
- **Contenu de secours** : si le dossier est vide, repli sur `akasha-os-splash-screen.png` (déjà
  présent dans le repo, licence propre) — jamais d'écran vide, sans avoir à embarquer un pack
  externe de photos dont la licence devrait être vérifiée. Un pack de paysages par défaut est noté
  comme amélioration future dans `roadmap.md`.
- Vidéos d'ambiance en boucle : reportées (nécessitent un contrôle `videowindow` dédié et plus de
  validation sur le Pi 4 2 Go ; voir `decisions.md`).

## 7. Horloge et météo

- **Horloge** : labels liés aux info-labels natifs Kodi `$INFO[System.Time]` / `$INFO[System.Date]`
  — aucun code Python requis.
- **Météo** : client [Open-Meteo](https://open-meteo.com/) (gratuit, sans clé API), ville configurée
  manuellement, cache JSON local (`/storage/.config/akasha-os/ambient-weather-cache.json`),
  rafraîchi toutes les 60 minutes, dernière valeur connue réutilisée hors-ligne.

## 8. Énergie et anti-marquage (portée v0.12)

- **Assombrissement progressif** simulé par un calque noir semi-transparent (pas de contrôle du
  rétroéclairage matériel : la sortie est HDMI vers une TV externe, Akasha OS ne peut pas piloter sa
  luminosité physique).
- **Anti-marquage** : le bloc horloge/météo change de coin (haut-gauche, haut-droit, bas-gauche,
  bas-droit) toutes les 10 minutes, sur le même mécanisme de presets que `Guide.xml`
  (`Window.Property`).
- **Veille complète** après `sleep_after_seconds` : délègue à `akasha-sleep.py`.

## 9. Réglages exposés (v0.12)

Dans les réglages natifs de l'addon (`Addon.OpenSettings(screensaver.akasha.ambient)`, accessible
aussi depuis Akasha Settings) :

- Activer/désactiver le Mode Ambiant (bascule `screensaver.mode`).
- Dossier de contenu (photos).
- Délai avant assombrissement (minutes).
- Délai avant veille complète (minutes).
- Ville pour la météo.
- Afficher/masquer la météo.

## 10. Hors périmètre v0.12

Actualités, musique, calendrier, détection de présence, sources cloud, génération procédurale,
synchronisation multi-écrans, vidéos d'ambiance, thèmes programmés par horaire, mode confidentialité
public. Voir `roadmap.md` pour leur emplacement dans les versions suivantes.
