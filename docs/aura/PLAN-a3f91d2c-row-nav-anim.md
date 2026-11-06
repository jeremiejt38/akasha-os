# PLAN-a3f91d2c — Row-to-row animation: Plex-parity corrections

## Contexte

Analyse mesurée frame-par-frame (Plex `screenrecord` ~35 fps vs Akasha slow-mo
×10) — voir `docs/plex-parity/ANIM.md` pour les chiffres et la matrice complète.
Vidéos de référence : `docs/plex-parity/reference/_video/` (local, gitignoré).

Référence Plex établie : hop rangée→rangée ~300 ms, colonne entière glisse d'un
pitch en ease-out ; rangée sortante s'estompe dans le voile sombre du hero ;
rangée entrante arrive chargée et opaque ; hero crossfade ~100-150 ms pendant le
slide sur l'item d'arrivée ; sous presses rapides chaque anim joue en entier en
file, le contenu ne disparaît jamais.

## Exigences

### R1 — Void en multi-hop (majeur)

Sous presses rapides (hold Down/Up ou salve), la zone des rangées devient vide
pendant le vol : labels orphelins, aucune carte, aucun ring.
**Requis** : le contenu ne doit jamais disparaître intégralement. Conserver le
dernier contenu lié pendant le vol, OU remplacer le slide par un fondu court
colonne-sortante/colonne-entrante quand le saut dépasse une rangée ou que les
presses s'enchaînent plus vite que l'anim.

### R2 — Rangée sortante fantôme sur le hero (majeur)

La rangée qui quitte le haut glisse *par-dessus* le backdrop translucide :
cartes semi-transparentes superposées à l'art + label qui percute le titre.
**Requis** : la rangée sortante doit disparaître « dans l'ombre » — voile/
gradient sombre opaque au-dessus de la couche rangées dans la zone hero
(z-order), ou masquage de la rangée dès qu'elle atteint la frontière du hero.

### R3 — Hero décorrélé du slide (fort)

Plex : crossfade du hero **pendant** le slide, vers l'item d'arrivée.
Akasha : le hero garde l'ancien item pendant la transition puis change ~1-2 s
plus tard ; sous nav rapide il poursuit les items avec plusieurs rangées de
retard.
**Requis** : déclencher la mise à jour du hero au début du mouvement avec un
fondu court, cibler l'item d'arrivée ; sous nav rapide, ne pas empiler les
repaints intermédiaires (sauter directement à l'item final — debounce).

### R4 — Peek row en fondu retardé (fort)

La rangée suivante finit de fondre après l'atterrissage → scintillement
post-settle. **Requis** : la rangée suivante doit être opaque dès son entrée
dans le viewport (pré-liage / fade supprimé ou absorbé par le slide).

### R5 — Réglage fin (mineur)

Durées : viser ~300 ms de hop total (slide 250→~280-300, glide swap aligné).
Le zoom 104 % de la carte focusée est une extension Aura assumée — **conserver**.

## Hors-scope / à préserver

- Pas de régression : no-wrap `fixedlist`, gate hold-Left (guards + timer 250 ms),
  barre de progression 6 px zoomée, conditions `HasFocus(5x9x)` des guards.
- Parité limitée au contenu Divertissement (cf. `docs/plex-parity/SPEC.md`).

## Vérification

- Tests Python (baseline 492 verts) + validation XML.
- Live Pi : hop simple Down/Up filmé en slow-mo ×10 puis à vitesse réelle ;
  salve 4× Down rapides → vérifier absence de void ; vérifier voile hero,
  crossfade hero, peek opaque ; re-tester hold-Left et bords.

## Résultat (implémenté et vérifié live)

| Req | Statut | Solution livrée |
|-----|--------|-----------------|
| R1 | ✅ | Sticky `AuraFocusSlot` injecté dans **toutes** les conditions `HasFocus(5Nxx)` (pos + nég) du groupe reco — la colonne reste ancrée pendant le park du focus. Rebind en 2 phases (ancre ~100 ms, autres slots worker +120 ms ancre-vers-extérieur, coalescé). `_sync_navigation` (−0,5 s) différé. Squelettes sous chaque carte → shimmer au lieu du vide pendant le décodage texture. Glide `AuraRowSwap` en dip 30 %. |
| R2 | ✅ | Contre-slide `+236/easing=in` → `+472/easing=out` (courbe miroir du slide colonne → net 0) : la rangée sortante se dissout **sur place**, plus de fantôme sur le hero. |
| R3 | ✅ | Paint optimiste `_update_hero(list_id=cible)` à l'émission + `_hero_after_landing()` (poll 30 ms, latest-wins) + repaint confirmé à l'atterrissage. |
| R4 | ✅ | Résolu via sticky conditions (le flicker venait des reversals pendant le park). |
| R5 | ✅ | Slides 250→280 ms. Zoom 104 % conservé. |

**Bug trouvé et corrigé en vol** : fuite d'`AuraFocusSlot` (compteur partagé
avec `_defer_focus` tuait le worker de libération → propriété collée → colonne
hors écran). Fix : `_fslot_gen` dédié + watchdog.

**Concession** : le dip 30 % du glide masque les resets restants — un contenu
opaque en continu exigerait une rangée entrante pré-liée hors écran (slot 6),
architecture évaluée puis reportée.

Vérifications live Pi : 492 tests, XML valide, hold-Left (parc guard →
pression fraîche → rail → retour), dead-keys bas/droite, salve 4× Down
(contenu présent + squelettes pendant le vol), hero synchro à +120 ms.
