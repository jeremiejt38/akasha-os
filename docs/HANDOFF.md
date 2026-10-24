# HANDOFF — Reprise de session (akasha-os)

> Passation pour une nouvelle session Devin, au `2026-10-24` (tag
> `akasha-os-v0.59.0`). Complète `docs/plex-parity/HANDOFF.md` (focus parité
> Plex, détails outils/pièges) et `docs/plex-parity/PARITY.md` (audit
> d'écrans + backlog).

## État du projet

Distribution LibreELEC/Kodi custom pour Raspberry Pi 4 en mode appliance
salon : l'addon `script.akasha.aura` remplace l'interface Kodi par une UI
type Plex Android TV (modules Divertissement / Jeux / App).

- **Version livrée** : `0.59.0` (tags `akasha-os-vX.Y.Z`, Release Please).
- **Version réellement sur le Pi** : `0.54.2` — le Pi est **éteint depuis
  ~2 jours** et 7 versions attendent le déploiement (v0.54.3 → v0.59.0).
- Fonctionne : lecture Plex (reprise, notes, watched), fiches détail
  films/séries/épisodes/personnes, recherche, bibliothèque A-Z, Store +
  apps externes, OSD minimaliste Plex, menu Paramètres unifié façon
  Android TV, Mode Ambiant (diaporama Ken Burns + horloge/météo + veille
  CEC), télécommande service (volume CEC, bouton Power),
  `analyser-de-performances` (collecteur perf + rapport), overlay de
  chargement sur les menus natifs Kodi.
- Statut de travail : `active` (source canonique : ariane, voir `ARIANE.md`).
- Tests : ~410 unitaires verts (aura 265, ambient 67, perfanalyzer 20,
  remote 28, quickstart 22, cloud.gaming 8), CI par addon dans
  `.github/workflows/test.yml`.

## Décisions prises

- **Pas de screensaver Kodi natif** : le watchdog CPythonInvoker tue les
  screensavers Python ~20 s → Ambiant = `WindowXML` + service idle
  (`service.akasha.ambient`).
- **Instance de fenêtre unique/réutilisée** : chaque `WindowXML` construit
  consomme définitivement un ID dynamique (~100/session) → windows cachées
  via `_get_sub_window()` (Aura) et instance unique (Ambient).
- **Menus natifs = écran de chargement permanent** plutôt que chasser
  chaque flash (handoff vidéo inclus).
- **Ken Burns par 2 slots `image` alternés** au lieu de `multiimage` :
  l'animation `Visible` repart à zéro par photo, aucune dérive de timer.
- **Préchargement texture 1×1/1,5 s** pour tout swap d'image : un decode+
  upload 1080p sur le thread de rendu gèle ~200 ms (~25 fps GUI max sur Pi4).
- **Paramètres unifiés dans Aura** (`settings_engine.py` + catalogue) au
  lieu de raccourcis vers les écrans Kodi/LibreELEC — pile
  catégories → réglages → picker radio, façon Android TV.
- **i18n une seule source** (`i18n.py` → `.po` générés, `LANGUAGES` prêt
  pour ajouter des langues ; français d'abord, tests de garde CI).
- **Endpoints publics** `plex.akasha.ing` / `connector.akasha.ing` (pas de
  VPN) ; UA custom obligatoire (Cloudflare 1010 bannit `urllib`).
- **Mutations Plex uniquement via le client direct** (rate/scrobble/
  removeFromContinueWatching) — le connector n'a pas de mutations.
- **Dedup par série** dans les rangées de reco (épisode→série via
  `grandparent_rating_key`).

## En cours

- **Mission active** : boucle de parité visuelle/comportementale
  Plex Android TV ↔ Aura (consigne utilisateur : « continuer en boucle le
  cycle tant que tout n'est pas identique… polish visuel le plus parfait
  possible »). Audit complet dans `docs/plex-parity/PARITY.md`.
- **Prochaine étape prévue** : déployer les 7 versions en attente dès que
  le Pi est allumé, vérifier visuellement (vague de chargement, drift
  ambiant, top-bar, dedup, menu Paramètres), puis reprendre le backlog :
  B17 (écran erreur serveur) → B1 (On Deck) → B14 (chapitres OSD).
- **Travail non commité** : aucun dans le repo (`git status` propre sauf
  `ARIANE.md` régénérable).
- **Stash orphelin** : `stash@{0}` « wip-fix-aura-interruptions » (guide/
  sleep-timer/keymaps) — quasi-certainement obsolète (sleep-timer mergé
  via PR #133) : vérifier puis supprimer.
- **Branche `feature/voice-commands`** : pushée sur origin pour
  préservation ; projet commandes vocales en pause (fiche Atlas
  `akasha-os-voice-commands`) — ne pas reprendre sans réactivation ariane.
- Claude bridge : session `plex-parity` persistante (MCP `claude-bridge`,
  param `session="plex-parity"` obligatoire) à continuer pour les
  arbitrages design.

## TODO / prochaines étapes

1. Allumer/vérifier le Pi → déployer v0.54.3…v0.59.0, confirmer le label
   de version à l'écran + vérif visuelle des nouveautés.
2. **B17** — écran d'erreur serveur (brique réutilisable états vides/
   offline).
3. **B1** — comportement « On Deck / Up Next » Plex.
4. **B14** — chapitres dans l'OSD.
5. Restauration du focus au retour de fiche/recherche/sheet ; refresh de
   rangée après action ; threads touchant l'UI après fermeture de fenêtre.
6. Appuis longs : personnes, résultats recherche, tuiles app, store,
   épisodes de la fiche.
7. États vides/erreur/chargement sur device ; Back à la racine (sortie
   confirmation façon Plex ?) ; mémoire textures sur sessions longues.
8. Ambiant reculés (volontaire) : crédit photo, fond flou non-16:9,
   appariement portrait, luminosité nocturne.
9. Ménage : stash orphelin, ~20 branches locales stale.

## Blocages / points d'attention

- **Pi éteint** (`192.168.1.88`, pas de route) — tout déploiement/vérif
  visuelle bloqué tant qu'il n'est pas allumé. SSH **par clé** fonctionne
  (pas besoin du mot de passe attendu par `apply.sh`).
- GUI Kodi ~**25 fps en animation** sur Pi4 (~40 ms/frame même en governor
  performance) — optimiser en réduisant les animations concurrentes.
- `System.FPS` lissé = inutilisable ; mesurer via `drm_prof.py` (hash des
  frames présentées, ~90 fps de capture).
- Kodi résout la navigation géométriquement malgré `<onup>` → intercepter
  avant `super().onAction()` + `setFocus`.
- `NotifyAll` arrive en `onNotification` préfixé `Other.`.
- **Ne jamais déclarer une parité visuelle** sans capture émulateur/Pi.
- Le Pi est une vraie TV de salon : pas de reboot/poweroff/CEC sans
  confirmation ; préférer « Redémarrer Akasha » (Kodi seul).
- Repo **public** : aucun secret ; `ARIANE.md` généré par ariane (ne pas
  éditer à la main, il est tracké).
- `/tmp` du Pi (tmpfs) se remplit vite — éviter d'y stocker des captures.

## Fichiers clés

| Chemin | Rôle |
|---|---|
| `kodi/addons/script.akasha.aura/resources/lib/aura_window.py` | dispatcher principal, top-bar, rangées reco, grille biblio, sheets appui long, handoff lecture |
| `…/lib/aura_detail.py`, `aura_search.py`, `aura_person.py`, `aura_app.py`, `aura_store.py`, `osd_menu.py` | écrans Aura |
| `…/lib/plex_client.py` | client Plex (cache, mutations, breaker+UA, removeFromContinueWatching) |
| `…/lib/i18n.py` | source unique des chaînes → régénère les `.po` |
| `…/lib/settings_engine.py` + `settings_catalog.py` + `aura_settings_panel.py` | menu Paramètres unifié |
| `kodi/addons/script.akasha.ambient/` + `service.akasha.ambient/` | Mode Ambiant (fenêtre + trigger idle) |
| `kodi/addons/service.akasha.perfanalyzer/` | collecteur perf + `resources/lib/report.py` |
| `kodi/scripts/analyser-de-performances.py` | CLI rapport perf |
| `skin-patches/` | patchs skin AH2 appliqués par `install.sh` (`patch_native_loading.py` = overlay chargement) |
| `scripts/install.sh`, `scripts/apply.sh` | installation/déploiement Pi |
| `docs/plex-parity/` | audit, captures, outils (`emu.sh`, `drm_prof.py`, `pi.sh`, `compare.py`) |
| `docs/perf-analyzer.md` | doc analyseur + overlay de chargement |
| `docs/ambient-mode/`, `docs/settings/` | specs et décisions des features |

## Contexte machine

- **Pi** : `root@192.168.1.88` (LibreELEC, SSH par clé OK). TV = écran via
  CEC/HDMI ; Pi allumé + TV éteinte = SSH joignable quand même.
- **Déploiement** : `apply.sh` exige un mot de passe → reproduire ses
  étapes en key-auth : tarball (`scripts/install.sh` + addons + media) →
  scp → `install.sh` sur le Pi → restart Kodi.
- **Vérifs** : label version dans le menu Guide ; `kodi-send`/`pi.sh` pour
  commandes ; `drm_film.py`/`drm_prof.py` pour captures/profiling ;
  `analyser-de-performances` sur le Pi pour le rapport perf.
- **Émulateur** : AVD `google-tv` (Android TV + Plex) via `emu.sh` —
  références dans `docs/plex-parity/reference/`.
- **Workflow** : branche courte → PR → squash merge → Release Please PR →
  tag. Commits anglais, docs projet en français OK. Atlas : consulter
  `projects/akasha-os.md`, journaliser dans `journal/session-*` sur
  branche `session/*`.
