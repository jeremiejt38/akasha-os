# HANDOFF — Reprise de session (akasha-os)

> Passation pour une nouvelle session Devin, au `2026-10-24` (tag
> `akasha-os-v0.59.0`), **actualisée au 2026-10-25** (tag
> `akasha-os-v0.69.0`, déployée sur le Pi). Complète
> `docs/plex-parity/HANDOFF.md` (focus parité Plex, détails outils/pièges) et
> `docs/plex-parity/PARITY.md` (audit d'écrans + backlog).

## État du projet

Distribution LibreELEC/Kodi custom pour Raspberry Pi 4 en mode appliance
salon : l'addon `script.akasha.aura` remplace l'interface Kodi par une UI
type Plex Android TV (modules Divertissement / Jeux / App).

- **Version livrée** : `0.69.3` (tags `akasha-os-vX.Y.Z`, Release Please).
- **Version réellement sur le Pi** : `0.69.3` — **déployée le 2026-10-25**
  (push ciblé de `script.akasha.aura` + restart Kodi ; le flux complet
  reste tarball → `install.sh`). v0.68.1 :
  (le déploiement a d'abord poussé 0.59.0 depuis un `main` local périmé,
  puis 0.68.0, puis le fix aura → refaire `git pull` avant tout déploiement,
  le repo avance vite : une session parallèle a livré 0.60 → 0.68 pendant la
  passation). Pi joignable : `root@192.168.3.77` (WiFi `Freebox-37FD5E`,
  LAN `192.168.3.0/24`, SSH par clé OK). L'IP `192.168.1.88` citée dans
  `AGENTS.md` est **obsolète** — migration réseau du 2026-10-23, source de
  vérité : `atlas/docs/hosts.md`.
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
- **Focus « Plex » au premier contenu** : Down depuis la barre atterrit
  sur la première rangée/grille (pas les sous-onglets), sélection d'un
  onglet focus la grille, fiche série → saison en cours, saison → prochain
  épisode, Back centré sur la carte quittée (v0.69.0).
- **Focus différé par thread + génération** plutôt que `setFocus` au clic :
  un `setFocus` dans le même tick qu'un toggle `<visible>` est annulé par
  la revalidation Kodi → délai 0,3 s + compteur de génération (toute
  action utilisateur invalide le focus en attente) (v0.69.0).
- **Nav Up/Down entre slots reco chaînée en Python** : le contre-slide de
  l'animation de sortie rend les rangées sorties *sous* la rangée focusée
  → le navigateur géométrique Kodi lit un ordre inversé (Down rebouclait
  sur la rangée du dessus, Up sautait une rangée / les sous-onglets).
  Chaînage explicite vers le slot rempli le plus proche (v0.69.2).
- **Labels des pilules d'action via overlays `label`** :
  `ControlButton.setLabel` écrit un champ que ce build Kodi 21.3 ne rend
  jamais (le `<label>` XML est figé au parsing) → les labels dynamiques
  vivent sur des contrôles `label` frères (7150-7156), positionnés par
  `_sync_action_row()` comme les overlays d'icônes (v0.69.3).
- **`border="32"` sur `rounded-solid.png` (source 64 px) = artefact de
  couture** : le milieu étirable tombe à 0 px → utiliser `border="16"`
  sur toutes les textures 9-slice étirées (v0.69.3).
- **Kebab `⋯` par bibliothèque dans la sidebar** : Left sur un item
  bibliothèque (marqué `is_library`) ouvre le menu Épingler/Désépingler
  + Monter/Descendre ; réutilise `divert.pinned_libraries` /
  `divert.library_order` existants (v0.69.3).

- **Mission active** : boucle de parité visuelle/comportementale
  Plex Android TV ↔ Aura (consigne utilisateur : « continuer en boucle le
  cycle tant que tout n'est pas identique… polish visuel le plus parfait
  possible »). Audit complet dans `docs/plex-parity/PARITY.md`.
- **Prochaine étape prévue** : **vérification visuelle sur la TV** —
  v0.69.3 déployée : pilules d'action labelisées (overlay + police
  28 px, coins stade propres), panneau latéral en police 32 px,
  kebab `⋯` sidebar (Left → épingler/désépingler/réordonner,
  vérifié à l'écran). Reste à valider : flux de focus Plex (barre →
  contenu, onglet → grille, saison/épisode en cours, retour centré),
  animation de sortie de rangée adoucie (moitié distance + fade +
  ease-in/out), cadre de focus plus fin (4 px), semi-opaque (`B3FFFFFF`)
  et zoomé avec la carte + coins arrondis conservés. Puis reprendre le
  backlog dans `docs/plex-parity/PARITY.md` — attention, il avance vite
  (session parallèle : B8, B10, B12, B15, B16, B17 livrés entre 0.60 et
  0.68 ; le flux de focus v0.69.0 couvre l'item « restauration du focus »
  partiellement). L'IP dans `AGENTS.md` est corrigée (`.77`).
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

1. ~~Déployer~~ **fait 2026-10-25** (v0.68.1 sur le Pi). Reste :
   vérification visuelle TV + `analyser-de-performances` après quelques
   heures d'usage (rapport sur les stalls/erreurs réels).
2. Backlog parité : se référer à `docs/plex-parity/PARITY.md` — **la
   session parallèle a déjà livré B8, B10, B12, B15, B16, B17** (v0.60 →
   v0.68) ; revérifier chaque item avant de l'attaquer.
3. **B1** — comportement « On Deck / Up Next » Plex (si non livré).
4. **B14** — chapitres dans l'OSD (si non livré).
5. Restauration du focus au retour de fiche/recherche/sheet ; refresh de
   rangée après action ; threads touchant l'UI après fermeture de fenêtre
   — **partiellement couvert par le flux de focus v0.69.0** ; à revérifier
   sur device (le focus différé tourne dans un thread Python — vérifier
   qu'il ne subsiste pas d'erreur « asked to focus, but it can't » liée à
   notre code ; celle de `defaultcontrol 2007` au chargement est
   préexistante et bénigne).
6. Appuis longs : personnes, résultats recherche, tuiles app, store,
   épisodes de la fiche.
7. États vides/erreur/chargement sur device ; Back à la racine (sortie
   confirmation façon Plex ?) ; mémoire textures sur sessions longues.
8. Ambiant reculés (volontaire) : crédit photo, fond flou non-16:9,
   appariement portrait, luminosité nocturne.
9. Ménage : stash orphelin, ~20 branches locales stale, IP dans `AGENTS.md`.

## Blocages / points d'attention

- **Deux IPs circulent pour le Pi** : `192.168.3.77` = la vraie (Atlas
  `docs/hosts.md`, testée 2026-10-24) ; `192.168.1.88` = obsolète (encore
  dans `AGENTS.md` et de vieux docs — toujours vérifier `docs/hosts.md`
  d'Atlas avant de déployer).
- SSH **par clé** fonctionne (pas besoin du mot de passe attendu par
  `apply.sh`).
- GUI Kodi ~**25 fps en animation** sur Pi4 (~40 ms/frame même en governor
  performance) — optimiser en réduisant les animations concurrentes.
- `System.FPS` lissé = inutilisable ; mesurer via `drm_prof.py` (hash des
  frames présentées, ~90 fps de capture).
- Kodi résout la navigation géométriquement malgré `<onup>` → intercepter
  avant `super().onAction()` + `setFocus`.
- `NotifyAll` arrive en `onNotification` préfixé `Other.`.
- **Pas de parenthèses dans les conditions skin Kodi** (`visible`,
  `condition` d'animation) : le parseur coupe sur `|` et log « unmatched
  parentheses », la règle est ignorée silencieusement. Écrire la forme DNF :
  `(A|B)+C` → `A+C | B+C`, `!(A|B)` → `!A + !B` (corrigé dans Aura.xml,
  v0.68.1).
- **Nouveaux services à activer dans `install.sh`** : la liste `INSERT ...
  enabled` d'`install.sh` doit inclure tout nouvel addon service sinon il
  reste désactivé dans Addons33.db et ne démarre jamais (bug trouvé sur
  perfanalyzer, corrigé v0.68.1).
- **La navigation géométrique Kodi utilise les bornes animées** : une
  animation slide qui déplace un contrôle au-delà de son voisin inverse
  l'ordre Up/Down perçu — chaîner explicitement en `onAction` quand une
  animation déplace des contrôles navigables (v0.69.2).
- **Focus et `<visible>` en même tick** : `setFocus` juste après avoir
  rendu un contrôle visible est annulé par la revalidation Kodi → pattern
  focus différé dans `aura_window.py::_defer_focus` (thread 0,3 s +
  garde de génération ; `AlarmClock` inadapté, granularité `hh:mm`).
  Vérifier sur device que le thread ne viole pas la règle UI-thread.
- `tail -1`-style de matching fragile dans les patchs skin : les fenêtres
  AH2 finissent par `</controls>\n\n</window>` (ligne vide) — insérer avant
  le dernier `</controls>` plutôt que de matcher une fin exacte.
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

- **Pi** : `root@192.168.3.77` (LibreELEC, SSH par clé OK, WiFi
  Freebox-37FD5E). ~~192.168.1.88~~ obsolète. TV = écran via CEC/HDMI ;
  Pi allumé + TV éteinte = SSH joignable quand même.
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
