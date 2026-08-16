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
système avec un moteur de rendu propre. Une première version s'appuyait sur un addon screensaver
Kodi natif (`xbmc.ui.screensaver`), mais un test réel sur le device a révélé un bug Kodi
long-connu qui tue les screensavers Python ~20 secondes après activation (voir `decisions.md`).
Le Mode Ambiant est donc livré en deux addons :

- **`script.akasha.ambient`** : la fenêtre elle-même (`xbmcgui.WindowXMLDialog`, skin
  `resources/skins/Default/1080i/Ambient.xml`), ouverte via `RunScript`, sur le même modèle que
  `Guide.xml`. Elle se ferme sur n'importe quelle entrée utilisateur ("réveil immédiat", recommandé
  par la spec pour une TV) et gère elle-même la transition vers la veille CEC
  (`akasha-sleep.py`) une fois le délai configuré atteint.
- **`service.akasha.ambient`** : un service qui surveille l'inactivité
  (`xbmc.getGlobalIdleTime()`) et déclenche `script.akasha.ambient` au bout du délai configuré,
  jouant le rôle que jouerait un screensaver natif, sans passer par le mécanisme Kodi concerné par
  le bug. Validé en conditions réelles (déclenchement automatique après le délai configuré, fenêtre
  restée stable plus de 10 minutes) — voir `decisions.md` pour le détail du test.

Voir `decisions.md` pour le détail des choix techniques et leurs alternatives écartées.

## 3. États retenus pour la v0.12

| État de la spec | Portage Kodi |
|---|---|
| `ACTIVE` | Interface Kodi normale ; `script.akasha.ambient` fermé. |
| `COUNTDOWN` | Géré par `service.akasha.ambient` (`xbmc.getGlobalIdleTime()`), poll toutes les 5s. |
| `TRANSITION_IN` | `onInit()` de la fenêtre Ambient : fondu d'entrée (animation skin `WindowOpen`). |
| `AMBIENT_ACTIVE` | Threads d'arrière-plan de la fenêtre : diaporama, horloge, météo, anti-marquage. |
| `DIMMED` | Overlay noir semi-transparent dont l'opacité augmente après `dim_after_seconds`. |
| `SLEEP_PENDING` / `SLEEP` | Après `sleep_after_seconds`, déclenche `akasha-sleep.py` puis ferme la fenêtre. |
| `TRANSITION_OUT` | `onAction()` de la fenêtre Ambient : fermeture sur toute entrée + animation `WindowClose`. |
| `Réveil` | Réveil immédiat (n'importe quelle entrée) + réveil CEC déjà géré par `akasha-sleep.py`. |

## 4. Déclenchement (portée v0.12)

- **Inactivité** : réglage propre `inactivity_timeout_minutes` (`script.akasha.ambient`, défaut 5
  minutes), surveillé par `service.akasha.ambient` — fonctionnel et testé (déclenchement automatique
  confirmé après le délai configuré, en conditions réelles sans interaction).
- **Manuel** : nouvelle entrée dans le menu Akasha Guide ("Mode Ambiant") qui appelle
  `RunScript(script.akasha.ambient)` — fonctionnel et testé.
- Reportés à une version ultérieure : activation programmée par plage horaire, déclenchements liés
  à des événements applicatifs (fin de film, appel...), détection de présence (caméra/capteur).

## 5. Cas de non-activation

Géré nativement par Kodi (`screensaver.disableforaudio`, pas d'activation pendant la lecture vidéo
sauf `usedimonpause`). Pas de logique additionnelle nécessaire en v0.12.

## 6. Contenu affiché (portée v0.12.1)

- **Images et vidéos locales**. Le module `content_manager.resolve_media()` détecte
  automatiquement le type de contenu du dossier configuré :
  - **Photos** : affichage par le contrôle natif Kodi `multiimage` (rotation, fondu, aléatoire).
  - **Vidéos** : lecture en boucle via `xbmc.Player().play(..., windowed=True)` dans un contrôle
    `videowindow` plein écran. Si le dossier contient au moins une vidéo, le Mode Ambiant bascule
    automatiquement en mode vidéo.
- **Pack de paysages par défaut** : lors du premier déploiement, `install.sh` télécharge un petit
  pack d'images de la Terre (public domain, NASA EPIC) dans `/storage/ambient/photos` si le dossier
  est vide. Ce pack n'est pas commité dans le dépôt.
- Dossier par défaut : `/storage/ambient/photos`, configurable depuis les réglages de l'addon (label
  "Dossier de contenu (photos ou videos)").
- **Contenu de secours** : si le dossier est vide et le téléchargement a échoué, repli sur un dossier
  dédié livré avec l'addon (`resources/media/fallback/`, contenant une copie de `splash.png`) —
  jamais d'écran vide. Le contrôle `multiimage` de Kodi exige un dossier, pas un fichier isolé.

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

- Activer/désactiver le Mode Ambiant (réglage `ambient.enabled`, lu par `service.akasha.ambient`).
- Délai d'inactivité avant activation automatique (minutes).
- Dossier de contenu (photos).
- Délai avant assombrissement (minutes).
- Délai avant veille complète (minutes).
- Ville pour la météo.
- Afficher/masquer la météo.

## 10. Hors périmètre v0.12

Actualités, musique, calendrier, détection de présence, sources cloud, génération procédurale,
synchronisation multi-écrans, vidéos d'ambiance, thèmes programmés par horaire, mode confidentialité
public. Voir `roadmap.md` pour leur emplacement dans les versions suivantes.
