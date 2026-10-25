# HANDOFF — Reprise de session (parité Plex/Google TV × Aura)

> Document de passation pour une nouvelle session Devin. Contient le contexte
> exact, l'état réel au `2026-10-25`, les outils et les pièges connus.
> Complète `PARITY.md` (audit d'écrans) et `SPEC.md`.

## Mission (consigne utilisateur, à préserver)

> « ton seul mot d'ordre est de continuer en boucle le cycle tant que tout
> n'est pas identique entre les deux (app Plex pour Android TV et Akasha OS),
> surtout niveau visuel — le polish visuel doit être le plus parfait possible,
> n'hésite pas à échanger avec Claude et à lui envoyer des captures. »

Traduire en pratique : auditer chaque écran/interaction d'Aura face à Plex
Android TV, corriger, tester, release, redéployer sur le Pi, vérifier à
l'écran — en boucle. Claude (`claude-bridge` MCP, **session `plex-parity`
obligatoire**) sert de partenaire design pour tout doute sur le comportement
Plex/Google TV.

## État des releases (au tag `akasha-os-v0.68.1`)

**Déployé sur le Pi le 2026-10-25** (`root@192.168.3.77` — vraie IP,
`192.168.1.88` obsolète depuis la migration réseau du 23/10). Toute la
parité fonctionnelle livrée jusqu'à v0.68.1 reste **« à vérifier à
l'écran »**.

Depuis le 2026-10-24/25, le backlog serveur est quasiment épuisé :
v0.60→v0.66 couvrent B17 (états erreur), B1 (Up Next), B14 (chapitres OSD),
B3 (`/:/timeline`), B2 (skip intro), B4 (filtres dynamiques), B7 (titres
similaires), B6 (onglet Activité + historique), B8 (recherche enrichie),
B10 (playlists), B11 (Go to Show), B12 (versions), B13 (UltraBlurColors),
B15 (continuité pistes par série), B16 (musique dans la sidebar), feuille
d'options partagée `context_sheet.py` sur toutes les surfaces de cartes,
Back à deux niveaux, fade bord droit rangées/grille, icônes clavier.

| Version | Contenu |
|---------|---------|
| v0.54.3 | Dédup par série dans les rangées de recommandations (épisode→série via `grandparent_rating_key`, doublons exacts fusionnés) |
| v0.55.0 | Menu Paramètres unifié façon Android TV : pile d'écrans (catégories → réglages → picker radio), vraies valeurs via `settings_engine.py` (Kodi JSON-RPC, connman, bluetooth, addon settings) |
| v0.56.0 | Audit fonctionnel : « Retirer de Continuer à regarder » (`PUT /actions/removeFromContinueWatching`), historique de recherche persisté, fix focus Up grille→sous-onglet, littéraux i18n, code mort supprimé |
| v0.57.0 | Top-bar rétractable : elle fond à 0% quand le focus descend, sous-onglets recentrés, hook `onFocus` |
| v0.57.1 | Couverture i18n complétée + générateur multi-langue (`LANGUAGES` dans `i18n.py`) |
| v0.58.0 | Mode Ambiant Ken Burns façon Google TV : 2 slots `image` alternés (`ambient.slot`/`kb{0,1}`/`img{0,1}`), 45 s/photo, crossfade 3 s, preload 1,5 s, horloge démarre bas-gauche + scrims dégradés |
| v0.59.0 | **`service.akasha.perfanalyzer`** (collecteur perf en fond, JSONL borné, boot marker autostart) + CLI **`analyser-de-performances`** ; **overlay de chargement permanent** sur les fenêtres natives (Home + menus nav : logo, « Chargement… », vague organique) — fini les flashs du menu Kodi au boot et au lancement vidéo |
| v0.60.0–v0.66.0 | Tout le backlog serveur de parité (voir la liste ci-dessus + `PARITY.md`) |
| v0.68.1 | Fix overlay de chargement (insertion avant `</controls>` au lieu d'un tail exact — seul Home.xml était patché), activation de `service.akasha.perfanalyzer` dans `install.sh` (restait désactivé), conditions Aura réécrites en DNF (Kodi ignore les parenthèses : « unmatched parentheses » dans kodi.log) |

**Première action d'une nouvelle session : vérification visuelle à l'écran**
— le Pi tourne v0.68.1. Valider spécifiquement : tout le paragraphe
« à vérifier à l'écran » de `PARITY.md`, la vague de l'écran de chargement
natif, `analyser-de-performances` en SSH, le pic mémoire retour hub
(perfanalyzer), le Back à deux niveaux, les feuilles d'options sur
recherche/filmographie/épisodes, la musique (B16) et la continuité des
pistes (B15).

## Déploiement

`./scripts/apply.sh <ip> <password>` attend un mot de passe — **l'auth SSH
fonctionne par clé** (`ssh -o BatchMode=yes root@192.168.3.77` passe sans mot
de passe). Méthode utilisée : reconstituer les étapes d'`apply.sh` en
key-auth (tarball du repo → scp → extraction → `install.sh` sur le Pi →
`systemctl restart kodi`). **Toujours `git pull` avant de construire le
tarball** — le repo avance vite. Le Pi est une vraie TV de salon :
pas de reboot/poweroff/CEC sans confirmation ; préférer « Redémarrer Akasha »
(Kodi seul).

## Outils déjà en place (`docs/plex-parity/scripts/`)

- `emu.sh` : pilote l'AVD **`google-tv`** (Android TV + Plex) — captures de
  référence dans `docs/plex-parity/reference/` et `akasha-direct/`.
- `drm_film.py` / `drm_grab.py` : capture vidéo/frames du DRM du Pi via SSH
  (fonctionne même sans HDMI branché).
- `drm_prof.py` : profiler ~90 fps — hash par frame présentée, détecte les
  stalls (a identifié le stall de 219 ms du swap fanart → fix préload 1px).
- `pi.sh` : helpers SSH rapides (kodi-send, log tail…).
- `compare.py` : diff captures Aura vs Plex.

## Conventions du repo (à respecter)

- **i18n** : toute chaîne visible passe par `STRINGS` dans
  `resources/lib/i18n.py` → `PYTHONPATH=resources/lib python3 resources/lib/i18n.py`
  régénère les deux `.po`. Tests de garde : `.po` non régénéré ou `tr()` sur
  id inexistant = CI rouge. IDs 33400+ réservés aux nouvelles chaînes.
- **Tests** : `cd kodi/addons/<addon> && PYTHONPATH=resources/lib python3 -m
  pytest tests -q` (dernière passe : ambient 67, aura 265, total ~390).
- **Workflow** : branche `feature|fix|docs/*` → PR → merge squash → Release
  Please ouvre une release PR → merger → tag `akasha-os-vX.Y.Z`. Commits en
  **anglais**, Conventional Commits. Repo **public** : aucun secret.
- **Ne jamais déclarer une parité visuelle** sans capture émulateur ou Pi.

## Pièges Kodi/Pi4 déjà rencontrés (ne pas réapprendre)

- Le GUI Kodi rend à **~25 fps en animation** sur Pi4 (~40 ms/frame, même en
  governor performance) — c'est le plafond, optimiser en réduisant le nombre
  d'animations concurrentes, pas en cherchant plus de fps.
- **Swap d'image = stall** si non préchargée : préchauffer le cache texture
  via un contrôle `image` 1×1 caché (technique du hero Aura et du préload
  ambiant).
- Screensaver Python natif = tué par le watchdog CPythonInvoker ~20 s → le
  Mode Ambiant est un `WindowXML` ouvert par `service.akasha.ambient`.
- Chaque `xbmcgui.WindowXML` construit **consomme définitivement un ID de
  fenêtre dynamique** (~100/session) → réutiliser les instances
  (`_get_sub_window()` côté Aura, instance unique côté ambient).
- `System.FPS` est lissé → inutilisable pour mesurer le rendu ; utiliser
  `drm_prof.py` (hash de frames présentées).
- Kodi résout la navigation géométriquement malgré `<onup>` — pour forcer une
  cible : intercepter l'action **avant** `super().onAction()` puis `setFocus`
  (zéro flash).
- `NotifyAll` arrive en `onNotification` avec le préfixe `Other.`.

## Backlog audit (priorités Claude, détails dans `PARITY.md`)

Tous les B1–B17 serveur sont implémentés (vérifiés au code, écran en
attente). Restants :

1. **Vérif écran de tout le backlog** — le vrai jalon restant.
2. **Hub `style=hero`** (`home.continue` sur `/hubs/promoted`, constat
   serveur 2026-10-25) : Plex le rend en **cartes paysage** (bannières 16:9
   avec barre de progression), Aura le traite en rangée shelf posters.
   Conversion à faire avec la vérif écran (slots de rangée dédiés ou
   itemlayout paysage — le viewport coulissant complique le binding).
3. Ghost icon près du hero (non identifié — les deux `icon-home.png` des
   rails sont volontaires), trou ~90 px titre/méta sans clearlogo (corrigé,
   à confirmer), couleur de fondu backdrop, typographie, format timecodes.
4. Pic mémoire retour hub → `perfanalyzer` sur le Pi.
5. Mode Ambiant : reculés volontaires — crédit photo, fond flou non-16:9,
   appariement portrait, luminosité nocturne.
6. **Émulateur `google-tv`** : Plex bloqué sur l'écran PIN du profil
   `.Akasha` — le PIN n'est pas dans le vault ; demander à Jérémie pour
   reprendre l'audit capture.

## Contexte opérationnel (endpoints, préférences, emplacements)

- **Source Plex d'Aura** : `https://plex.akasha.ing` (endpoint public
  Cloudflare→Traefik Hetzner→Unraid:32400, pas de VPN). **Cloudflare bloque
  le User-Agent `urllib` par défaut (erreur 1010)** → les clients Python
  envoient `User-Agent: AkashaOSAura/1.0` (`plex_client._headers()`).
- **Connector Akasha** (`connector.akasha.ing`) : métadonnées/auth
  multi-utilisateurs seulement — **pas de mutations** ; les actions type
  `removeFromContinueWatching`, `scrobble`, `rate` ne fonctionnent que via
  le client Plex direct. Les clients ont un disjoncteur par hôte (fail-fast
  30 s) + cache lecture 30 s pour ne jamais geler le GUI.
- **Emplacements de réglages non évidents** : l'activation du Mode Ambiant
  (`ambient.enabled`, bool, défaut `true`) vit dans `script.akasha.settings`,
  lue par `service.akasha.ambient` ; l'historique de recherche dans
  `search.recent` (réglage addon Aura, JSON, 8 entrées, fallback sur
  corruption) ; le délai/dim/sleep ambiant dans `script.akasha.ambient`.
- **Préférence utilisateur** : UI **français d'abord** ; les autres langues
  viendront après — `LANGUAGES` dans `i18n.py` est prêt pour en ajouter.
  Noms propres non traduits (Plex, Moonlight…), titres serveur inchangés,
  options Kodi affichées dans la langue de Kodi.
- **`ARIANE.md`** à la racine : fichier généré par la synchro ariane
  (`http://latitude-9430:8420`) — le laisser **non suivi** par git.
- Réglages Kodi vérifiés : les 21 IDs utilisés par `settings_catalog.py`
  existent tous dans Kodi 21/Omega (`displaysoff`, `shutdowntime`,
  `screensaver.time` n'ont pas d'options → fallback picker `range` prévu).
- **Historique de conversation** : les résumés automatiques Devin vivent
  dans `~/.local/share/devin/cli/summaries/` (`history_*.md`) si jamais la
  nouvelle session veut recouper un détail.
- **Branche `feature/voice-commands`** : chantier commandes vocales, projet
  en pause (fiche Atlas `akasha-os-voice-commands`). Poussée sur origin
  2026-10-24 pour préservation — ne pas la reprendre sans réactivation
  explicite du projet dans ariane.
- **Stash résiduel** : `git stash` contient `stash@{0}` (WIP
  « prevent-aura-app-interruptions » sur `akasha-guide.py`, `akasha-sleep.py`,
  keymaps, `install.sh`). Presque certainement **obsolète** — le sleep-timer
  qu'il introduisait est déjà mergé sur `main` (PR #133). Vérifier le diff
  puis le supprimer plutôt que de le transporter indéfiniment.

## Contexte hors repo

- **Atlas** (mémoire persistante, `~/workspace/atlas`) : journal de session
  `journal/session-2026-10-24-ambient-kenburns.md` commité sur la branche
  `session/2026-10-24-amb01-ambient-kenburns` (worktree
  `/tmp/atlas-session-ambient`, non consolidée). Consulter
  `projects/akasha-os.md` avant de travailler ; consigner les jalons dans
  `journal/` sur une branche `session/*`.
- Pi allumé mais TV éteinte = joignable en SSH quand même (LibreELEC tourne).
- Claude bridge : outil `send_message` avec `session="plex-parity"`.
