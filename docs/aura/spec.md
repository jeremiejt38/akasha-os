# Akasha Aura — Spécification fonctionnelle

## 1. Présentation

Akasha Aura est le nouvel écran d'accueil d'Akasha OS, inspiré des launchers type Fire TV : 3
onglets (**Divertissement**, **Jeux**, **App**), chacun présentant des rangées/tuiles de contenu
prêtes à lancer, en remplacement de l'accueil Kodi natif (skin Arctic Horizon 2).

Origine du besoin : l'addon Plex utilisé jusqu'ici (`script.plexmod`, alias "PM4K") est en réalité
une continuation du client Plex officiel open-source — donc déjà fidèle à l'interface Plex — mais
jugé peu intuitif/fonctionnel dans l'usage réel sur le Raspberry Pi 4. Plutôt que de chercher un
autre addon Kodi (aucun n'offre plus de fidélité à Plex que PM4K par construction), Aura construit
un accueil sur-mesure qui interroge directement l'API Plex, avec un contrôle total sur l'affichage.

## 2. Onglets

### Divertissement

- Rangées horizontales par bibliothèque Plex : "Continuer à regarder" (`/library/onDeck`),
  "Ajoutés récemment" (`/library/recentlyAdded`), "Sortis récemment" (tri par date de sortie), puis
  une rangée par genre (hubs Plex).
- Bouton "Voir toute la bibliothèque" par section → vue liste complète avec recherche, tri (titre,
  date d'ajout, date de sortie, note) et filtres (genre, année, non vus...).
- Lecture : déléguée dans un premier temps au mécanisme le plus fiable identifié en implémentation
  (PM4K ou résolution directe du flux Plex) — voir `decisions.md`.

### Jeux

- Tuiles reprenant la liste déjà curatée dans `skin-patches/shortcuts/games*.DATA.xml` (Steam Link,
  Moonlight, Cloud Gaming Chromium...), lancées via `RunAddon`.

### App

- Liste des addons installés (JSON-RPC `Addons.GetAddons`), avec par tuile : Lancer, Épingler /
  Désépingler (remonte en tête de liste), Désinstaller.
- **Akasha Store** : manifeste JSON curaté des addons/dépôts déjà validés pour Akasha OS,
  installables en un geste depuis Aura ; les addons installés depuis le Store apparaissent ensuite
  automatiquement dans la liste "App".

## 3. Architecture

Deux addons (même schéma que Mode Ambiant, voir `docs/ambient-mode/`) :

- **`script.akasha.aura`** : la fenêtre elle-même (`xbmcgui.WindowXMLDialog`, skin
  `resources/skins/Default/1080i/Aura.xml`), ouverte via `RunScript`. Modules Python purs et
  testables dans `resources/lib/` (`config.py`, puis `plex_client.py`, `addons_inventory.py`,
  `store_manifest.py` aux jalons suivants) séparés de l'orchestration Kodi
  (`aura_window.py`, dépendante de `xbmc*`, non testable hors runtime Kodi).
- **`service.akasha.aura`** : service démarré au boot (`xbmc.service`, `start="startup"`) qui
  attend la fin du splash/intro puis ouvre Aura automatiquement, pour qu'il devienne l'accueil
  effectif sans modifier `Home.xml` du skin Arctic Horizon 2 (fragile aux mises à jour de skin).
- Keymap `kodi/userdata/keymaps/akasha-aura.xml` : redirige l'action `Home` vers Aura, pour qu'il
  reste le point d'entrée permanent même après une navigation profonde dans Kodi natif.

Voir `decisions.md` pour le détail des choix techniques et alternatives écartées, et `roadmap.md`
pour le découpage en jalons livrables.

## 4. Configuration

- URL du serveur Plex + `X-Plex-Token` dans les réglages de l'addon
  (`userdata/addon_data/script.akasha.aura/settings.xml` sur le device) — jamais commités dans le
  repo, cohérent avec la pratique déjà en place pour les autres tokens Akasha (`checkup-akasha.env`
  côté Unraid).

## 5. Hors périmètre (v0.1.x, jalon socle)

Rangées Plex réelles, bibliothèque complète, tuiles Jeux, inventaire App, Akasha Store — chacun
arrive à son propre jalon (voir `roadmap.md`). Le jalon socle livre uniquement la coquille
navigable (3 onglets, contenu placeholder) et le remplacement de l'accueil natif.
