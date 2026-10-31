# HANDOFF — Reprise de session (akasha-os)

> Passation pour une nouvelle session Devin, **actualisée au 2026-10-31**
> (2e « refresh » de conversation — la précédente pesait ~5 Go à cause des
> captures base64 ; la règle 960×540 d'`AGENTS.md` corrige désormais le
> problème à la source). Complète `docs/plex-parity/HANDOFF.md` (focus
> parité Plex, outils/pièges) et `docs/plex-parity/PARITY.md` (audit
> d'écrans + backlog, quasi entièrement vert).

## État du projet

Distribution LibreELEC/Kodi custom pour Raspberry Pi 4 en mode appliance
salon : l'addon `script.akasha.aura` remplace l'interface Kodi par une UI
type Plex Android TV (modules Divertissement / Jeux / App).

- **Version livrée** : `akasha-os-v0.69.10` (tag, Release Please,
  2026-10-26).
- **Version sur le Pi** : `0.69.10` (label Guide vérifié dans le splash
  log : `local=0.69.10, remote=0.69.10`) **+ working copy de
  `aura_detail.py` poussée par scp** (fix staleness saisons, hash
  `c13a4b86f5ac25129a0c4be68ea81aa0` identique repo↔Pi) — **déployée mais
  NON commitée**. Le Pi tourne en avance sur git.
- **Branche active** : `fix/aura-search-rail` — ~200 commits d'avance sur
  `origin/main` (accumulation de plusieurs sessions de parité ; le cycle
  release est en retard, voir TODO n°1).
- Pi joignable : `root@192.168.3.77` (SSH par clé OK, WiFi
  `Freebox-37FD5E`, LAN `192.168.3.0/24`). L'IP `192.168.1.88` citée dans
  `AGENTS.md` est **obsolète** — source de vérité : `atlas/docs/hosts.md`.
- Fonctionne : lecture Plex (reprise, notes, watched), fiches détail
  films/séries/saisons/épisodes/personnes, recherche, bibliothèque A-Z,
  Catégories + drill-in filtré, Store + apps externes, OSD Plex complet
  (cercles queue+gear, thumb, badge −10, overlay chapitres/queue, menu
  pistes), FAST Live TV + EPG now/next (238 chaînes), pseudo-sections
  livetv/playlists à chrome collapsé, menu Paramètres unifié, Mode
  Ambiant, télécommande service, perfanalyzer.
- Statut de travail : `active` (source canonique : ariane, `ARIANE.md`).
- Tests : **443 unitaires verts** (dernier run 2026-10-31).

## Décisions prises (depuis le handoff 2026-10-25)

- **Coins arrondis des cartes = PNG alpha réel via proxy loopback**
  (`resources/lib/art_proxy.py`, commit `91248c5`) : Kodi ne clippe pas
  l'alpha et les covers `*-corners.png` teintées laissaient des pixels
  opaques visibles sur fond clair/voile coloré. Le proxy
  `http://127.0.0.1:8194/art` wrap `plex_client.image_url` /
  `connector_client.image_url` via le param `radius` (poster 16 px,
  landscape 22 px, catégorie 26 px), fetch upstream, arrondit avec PIL,
  sert du PNG caché sur disque (dédup par lock). Les covers XML se
  masquent quand l'URL art pointe sur `127.0.0.1`. Validé au pixel près
  sur grilles, recherche, fiche, voile coloré et tuiles catégories.
- **Log proxy sans secrets** : les URLs Plex portent `X-Plex-Token` en
  query → les logs d'erreur masquent la query (commit inclus dans
  `91248c5`).
- **Saisons fiche = appartenance par `rating_key`** (`_seasons_key`) +
  **garde `parent_rating_key`** : la fenêtre détail est réutilisée entre
  pages et `_load_seasons` court-circuitait sur `self._seasons` non vide
  → Black Butler affichait le poster de saison d'Alya (metadata 81486).
  Deuxième couche : le backend `show_seasons(82547)` a **réellement servi
  1 saison étrangère** → les saisons dont `parent_rating_key` ≠ rk du
  show sont droppées avec warning. Validé live : Black Butler →
  « 5 Saisons » correctes, log `dropped 1 foreign seasons (rk=82547)`
  (non commité, voir « En cours »).
- **Captures légères obligatoires** (`AGENTS.md` commit `9aaf80b`) :
  ~960×540 JPEG par défaut (`convert -resize 960x540 -quality 70`),
  1080p uniquement pour texte fin/pixels (le dire), jamais deux captures
  du même écran, dossier dédié `/tmp/akasha-shots`.
- **Restart Kodi par `systemctl restart kodi`** : `Application.Quit`
  JSON-RPC est **ignoré** sur ce build (retourne OK, process inchangé).
- **Décodage logiciel Live TV restauré** : après un passage en soft
  decode pour les chaînes FAST, `useprimedecoder` est remis à `true` à la
  sortie (sinon la lecture VOD HW suivante casse).
- **Fetches détail en parallèle + maps bg reset par render** :
  `_render()` reset `_bg_done`/`_bg_results` et `_bg_start()` capture le
  dict courant → un thread tardif d'un render précédent ne peut pas
  écrire dans la page suivante (architecture anti-staleness, v0.69.x).
- **`/status/sessions/history/all` ignore `X-Plex-Container-Size`** :
  appel non scopé = tout l'historique (~25 Mo) → OOM `kodi.bin` sur Pi4.
  Toujours `watch_history(rating_key=)` ou `since_days=` borné.

## En cours (au moment du refresh)

- **Chantier actif** : boucle de parité Plex Android TV ↔ Aura, consigne
  « continuer en boucle tant que tout n'est pas identique, polish visuel
  le plus parfait possible ». `PARITY.md` quasi entièrement vert.
- **Travail NON commité** (un seul fichier) :
  `kodi/addons/script.akasha.aura/resources/lib/aura_detail.py` —
  fix staleness saisons (`_seasons_key` + garde `parent_rating_key`,
  diff ~35 lignes, commentaires français dans le code expliquant le cas
  Alya→Black Butler observé live). **Déjà déployé et validé sur le Pi**
  (hash identique, restart Kodi fait, reproduction A→B propre).
  Reste à faire : tests auto puis commit.
- **Prochaine étape prévue** : écrire les tests `_seasons_key` /
  foreign-season dans `tests/test_aura_detail.py` (pattern existant :
  méthodes unbound appelées sur un `SimpleNamespace`, xbmc stubbé) →
  suite 443 → commit `fix(aura-detail):` → cycle release complet →
  reprendre la boucle parité sur les écarts restants de `PARITY.md`.

## TODO / prochaines étapes (ordonné)

1. **Commit + release du lot `fix/aura-search-rail`** : ~200 commits
   d'avance, dont le fix staleness déjà sur le Pi. Flux KSP : tests →
   commit → push → PR/merge → Release Please PR → merge → pull →
   `./scripts/apply.sh <pi> <password>` (ou équivalent key-auth : tarball
   → scp → `install.sh` → restart Kodi) → **vérif label version dans le
   menu Guide**. Ne pas déclarer le déploiement fait tant que le label
   n'est pas vu à l'écran.
2. **Investiguer le backend `show_seasons`** : `show_seasons(82547)` a
   retourné 1 saison d'un autre show (log `dropped 1 foreign seasons`) —
   vérifier le connecteur (`connector_client.py` / endpoint Plex
   children) : cache croisé, clé de cache mal scopée, ou réponse Plex
   réellement polluée.
3. Reprendre la boucle parité (surfaces restantes à revérifier dans
   `PARITY.md` : états vides/erreur sur device, appuis longs restants,
   mémoire textures sessions longues, Back à la racine = sortie
   confirmation façon Plex ?).
4. Vérification TV réelle + rapport `analyser-de-performances` après
   quelques heures d'usage.
5. Ménage : stash orphelin `wip-fix-aura-interruptions`, ~20 branches
   locales stale, IP obsolète `192.168.1.88` encore dans `AGENTS.md`.
6. Ambiant reculés (volontaire) : crédit photo, fond non-16:9,
   appariement portrait, luminosité nocturne.

## Blocages / pièges connus

- **Kodi ne redémarre pas via `Application.Quit`** → `ssh root@192.168.3.77
  'systemctl restart kodi'` (non destructif, TV de salon : jamais de
  reboot/poweroff sans confirmation).
- **PixelCamera** (`http://192.168.3.77:8088/frame.jpg`) : doit tourner
  avec `KODI_SCREENSHOT_DIR=/storage/screenshots` (sinon 503/timeout —
  il attend un `screenshot*.png` stable). Relance :
  `export KODI_SCREENSHOT_DIR=/storage/screenshots; python3 -u /storage/pixelcamera.py`.
  Si mort après reboot, le relancer par SSH.
- **ffmpeg absent en local** (poste dev) → downscale via ImageMagick :
  `convert cap.jpg -resize 960x540 -quality 70 cap-s.jpg` (PIL dispo
  aussi). Sur le Pi, kodi-send `TakeScreenshot` écrit dans
  `/storage/screenshots/`.
- **`Input.SendText` ne remplit pas le clavier custom d'Aura** (la
  recherche gère `onClick` sur le panneau 8100 touche par touche) →
  naviguer les touches à la télécommande ou cliquer une entrée de
  l'historique (liste 8110).
- **Back à la racine quitte Aura** et relance le boot splash
  (~20 s) — ne pas Back une fois de trop ; la fenêtre active se vérifie
  via JSON-RPC `GUI.GetProperties` (`currentwindow` : 13002 =
  AuraDetail).
- **Items Discover/cloud à clés hex** : `rating_key` provider hex →
  404 attendus sur `/library/metadata/<hex>` (extras/related/stream
  labels/markers/chapters) — pas un bug local ; un trailer IVA peut
  démarrer en fond (comportement Plex).
- **Posters manquants côté serveur** : certains items (Baki 2018, Baki
  the Grappler) n'ont aucun thumb upstream → carte noire + titre, ce
  n'est **pas** une régression du proxy (vérifié via JSON-RPC
  `ListItem.Art(thumb)` vide).
- **Vignettes chapitres noires dans l'overlay OSD** quand le serveur n'a
  pas d'index BIF (`/library/parts/<id>/indexes/sd` → 404) — limitation
  Plex, placeholder sombre acceptable.
- **Genres doublés** (« Comédie/Comedie », « Drame/Drama ») : viennent
  des agents FR+EN du serveur — Plex officiel les affiche pareil.
- **Focus et `<visible>` en même tick** : `setFocus` juste après un
  toggle visible est annulé par Kodi → `_defer_focus` (thread 0,3 s +
  génération).
- **Pas de parenthèses dans les conditions skin** (`visible`) : parseur
  Kodi casse silencieusement → forme DNF (`A+C | B+C`).
- `/tmp` du Pi = tmpfs qui se remplit vite → captures en
  `/storage/screenshots`, jamais `/tmp`.
- Repo **public** : aucun secret, pas de captures/IPs dans git.
  `ARIANE.md` généré, ne pas éditer.
- SSH **par clé** OK ; `apply.sh` attend un mot de passe → reproduire
  ses étapes en key-auth si besoin.

## Fichiers clés

| Chemin | Rôle |
|---|---|
| `kodi/addons/script.akasha.aura/resources/lib/aura_window.py` | dispatcher principal, top-bar, rangées, grille biblio, `_open_detail` (reset état fiche), sheets appui long |
| `…/lib/aura_detail.py` | fiche détail (modes item/show/season, fetches bg parallèles, `_seasons_key`) — **fichier du fix non commité** |
| `…/lib/art_proxy.py` | proxy loopback `127.0.0.1:8194/art` → PNG coins arrondis (PIL, cache disque, dédup lock) |
| `…/lib/plex_client.py`, `connector_client.py` | clients API (`image_url(..., radius=)` wrap proxy) |
| `…/lib/aura_search.py`, `aura_person.py`, `aura_menu.py`, `osd_menu.py` | écrans Aura |
| `…/lib/i18n.py` | source unique des chaînes → `.po` |
| `…/lib/gui_guard.py`, `divert_source.py`, `field_veil.py` | verrous UI, items vidéo, voile fiche |
| `kodi/addons/script.akasha.aura/tests/test_aura_detail.py` | tests fiche (xbmc stubbé, méthodes unbound) |
| `skin-patches/plex-osd/VideoOSD.xml` | OSD Plex (cercles queue/gear, thumb, −10) |
| `docs/plex-parity/` | `PARITY.md` (backlog), `HANDOFF.md` (détails outils), `scripts/pi.sh` (cap/key/ssh), refs officielles |
| `scripts/install.sh`, `scripts/apply.sh` | installation / déploiement Pi |

## Contexte machine

- **Pi** : `root@192.168.3.77` (LibreELEC, SSH clé, Pi allumé + TV
  éteinte = SSH joignable). JSON-RPC `http://192.168.3.77:8080/jsonrpc`.
- **Captures** : `curl http://192.168.3.77:8088/frame.jpg` (PixelCamera,
  port 8088) → `/tmp/akasha-shots/<nom>-s.jpg` en 960×540. Viewer :
  `http://192.168.3.77:8088/frame`.
- **Navigation** : `kodi-send --host=192.168.3.77 --action="Left"` ou
  `docs/plex-parity/scripts/pi.sh key <action>`.
- **Vérif fenêtre/contrôle** : JSON-RPC `GUI.GetProperties`
  (`currentwindow`, `currentcontrol`) ; `ListItem.Art(thumb)` via
  `XBMC.GetInfoLabels` pour l'URL art réelle d'une carte.
- **Log** : `/storage/.kodi/temp/kodi.log` (les warnings `Akasha Aura
  Detail:` y tracent les drops/échecs).
- **Déploiement ponctuel** : `scp` direct vers
  `/storage/.kodi/addons/script.akasha.aura/resources/lib/` +
  `systemctl restart kodi` (hash md5 à comparer après).
- **Workflow** : branche courte → tests → PR → Release Please → tag →
  `apply.sh` → vérif label version. Commits anglais, docs FR OK.
- **Atlas** : fiche `projects/akasha-os.md`, journal de cette session
  dans `journal/session-2026-10-31-*` (branche `session/*` du worktree
  `/tmp/atlas-sess`).
