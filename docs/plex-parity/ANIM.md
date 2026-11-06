# ANIM — Navigation rangée → rangée : comparaison mesurée Plex TV vs Aura

Analyse frame-par-frame réalisée le 2026-11-06.

## Méthode

- **Plex** : `adb shell screenrecord` (~35 fps réels) sur l'émulateur Google TV, trois
  séquences : `home_nav_down_x3.mp4` (3× Down espacés), `home_nav_up_x2.mp4`,
  `home_nav_rapid_down4_up2.mp4` (4× Down ~350 ms puis 2× Up). Vidéos dans
  `reference/_video/`. Fenêtres de mouvement détectées par diff moyen inter-frames,
  positions mesurées par corrélation de gabarit.
- **Akasha OS** : le screenshot JSON-RPC est **mis en file** (flush après l'action,
  jamais synchronisé vsync — les rafales denses produisent des frames identiques).
  Méthode : animations ×10 sur le XML déployé (`time=150/200/220/250` → ×10) +
  captures espacées ~0,4-0,6 s → vraies phases intermédiaires. Restore `.bak`
  après capture.

## Référence Plex (mesuré)

| Aspect | Mesure |
|--------|--------|
| Durée totale du hop | ~280-340 ms (10-12 frames @35 fps) |
| Déplacement | colonne entière glisse d'un pitch (~580 px) |
| Easing | ease-out — vitesse de crête en milieu d'anim, forte décélération finale |
| Slot focusé | fixe (~y=525 label / ~570-930 cartes @1080p) |
| Rangée sortante | garde le ring, glisse vers le haut, **s'estompe dans le gradient sombre opaque du hero** — jamais visible *par-dessus* le contenu du hero |
| Rangée entrante | monte depuis le bas **déjà chargée et opaque** ; le ring se pose à l'arrivée |
| Rangée suivante | dépasse en bas de l'écran, pleine opacité, aucun fade différé |
| Hero | **crossfade ~100-150 ms pendant le slide**, bascule sur l'item d'arrivée |
| Carte focusée | ring blanc seul — **pas de zoom** |
| Pressions rapides | chaque pression produit une anim complète, exécutées en file — le contenu reste visible en continu, jamais de vide |

## Akasha OS observé (slow-mo sur Pi, v0.78.4)

| Aspect | Observation |
|--------|-------------|
| Slide | présent (groupe coulissant ancré par `HasFocus`, 250 ms + glide `AuraRowSwap` 220 ms) |
| Rangée sortante | glisse vers le haut **par-dessus le backdrop hero translucide** → cartes fantômes semi-transparentes superposées à l'art + labels qui se chevauchent avec le texte du hero |
| Rangée entrante | arrive au slot rapidement (~50 % de la fenêtre anim) |
| Rangée suivante | **matérialise par fondu lent** — encore ~50 % d'opacité bien après l'atterrissage de la rangée focusée |
| Hero | **ne change pas pendant le slide** — mis à jour après, avec latence de chargement d'art (~1-2 s constatée) ; sous nav rapide il poursuit les items avec plusieurs rangées de retard (observé : affiche « Les Simpson » en fondu alors que le focus est déjà sur « Koh-Lanta ») |
| Ring | saute correctement : l'ancienne carte le conserve en glissant, la nouvelle le reçoit à l'arrivée — conforme à Plex |
| **Multi-hop rapide (4× Down)** | **VIDE TOTAL pendant le vol** : la zone des rangées est entièrement vide (fond violet), seuls des labels flottent sans cartes, aucun ring nulle part — puis le contenu réapparaît à l'atterrissage. Cause : les 5 slots virtuels rebindent tous en cascade ; pendant le vol aucun n'est lié à une rangée affichable |

## Matrice des écarts (priorisée)

| # | Écart Akasha | Sévérité |
|---|--------------|----------|
| 1 | **Void en multi-hop** — zone rangées vide + labels orphelins pendant un saut de plusieurs rangées | 🔴 majeur |
| 2 | **Fantôme de la rangée sortante par-dessus le hero** — backdrop translucide/clair au lieu d'un voile opaque ; labels qui percutent le texte du hero | 🔴 majeur |
| 3 | **Hero décorrélé du slide** — pas de crossfade synchronisé ; mise à jour tardive dépendante du fetch d'art ; sous nav rapide plusieurs items de retard | 🟠 fort |
| 4 | **Peek row en fondu retardé** — la rangée suivante finit de fondre après l'atterrissage → scintillement post-settle | 🟠 fort |
| 5 | Zoom 104-108 % de la carte focusée (Plex : ring seul) — extension Aura volontaire probable, à arbitrer | 🟡 mineur |
| 6 | Durées ~250-220 ms vs ~300 ms Plex — quasi-conforme, micro-réglage seulement | 🟡 mineur |

## Pistes de correction

- **(1)** Conserver le dernier contenu lié pendant le vol multi-hop (ne pas débinder
  un slot avant que son successeur soit prêt), ou déclencher un fondu court
  colonne-sortante/colonne-entrante plutôt qu'un slide de N pitchs quand
  `abs(delta)>1`.
- **(2)** Voiler la zone hero d'un gradient sombre opaque au-dessus des rangées
  (z-order), ou masquer la rangée sortante dès qu'elle atteint la frontière du
  hero — la disparition doit se lire « dans l'ombre », pas en transparence
  sur l'art.
- **(3)** Déclencher le repaint hero au début du slide (crossfade superposé),
  cible = item d'arrivée ; debounce sur l'atterrissage sous nav rapide.
- **(4)** Pré-lier la rangée suivante (art déjà résolu) pour qu'elle soit opaque
  dès son entrée dans le viewport, comme Plex.

## Correctifs livrés (v0.78.5, branche `fix/row-nav-anim`)

Diagnostic confirmé par instrumentation sur le Pi : le `reset()` du rebind
parque le focus hors des rangées pendant ~0,3 s ; pendant ce « park » toutes
les conditions `HasFocus(5Nxx)` tombent à faux → les slides `Conditional
reversible="true"` de la colonne **reprennent en sens inverse vers 0** puis
re-glissent à l'atterrissage → aller-retour géant + void. Le rebind complet
coûte ~1 s sur Pi 4 (reset+labels+placeholders ~80 ms/slot, `addItems` ~0,3 ms
grâce au cache `row['_items']`, `_sync_navigation` ~0,5 s), et les textures de
posters décodent en ~200-400 ms en tâche de fond — les items liés restent donc
invisibles un moment après le bind.

| # | Écart | Correctif livré | Vérifié |
|---|-------|-----------------|---------|
| 1 | Void multi-hop | **a)** Chaque `HasFocus(5Nxx)` (positif **et** négatif) des ~670 conditions du groupe reco substitué par son équivalent « focus logique » : `HasFocus ⭑ AuraFocusSlot=N` — pendant le park, toutes les conditions s'évaluent exactement comme si le slot d'ancrage était focusé → la colonne reste ancrée, plus d'aller-retour. **b)** Rebind en **deux phases** : slot d'ancrage immédiat (~100 ms), les 4 autres en worker à +120 ms ancre-vers-extérieur, gardé par génération → coalescé sous salve. **c)** `_sync_navigation` déplacé dans la phase différée (−0,5 s/hop). **d)** Squelettes `skeleton-poster/landscape` rendus sous **chaque** carte (plus seulement `IsPlaceholder`) → pendant le décodage des textures la zone affiche un shimmer de cartes au lieu du vide. **e)** Fade du glide `AuraRowSwap` abaissé à 30 % → le swap restant lit comme un dip volontaire. | Captures : contenu présent pendant la salve ; squelettes visibles à +1,46 s ; plus de void total. |
| 2 | Fantôme rangée sortante | Contre-slide `+236` → **`+472` avec `easing="out"`** (même courbe que le slide colonne → offset net exactement 0 pendant toute l'anim) : la rangée sortante **se dissout sur place** au lieu de voyager sur le hero. Aucun changement de z-order requis. | Plus de cartes par-dessus le hero dans les captures. |
| 3 | Hero décorrélé | **Paint optimiste** : `_update_hero(list_id=cible)` appelé à l'émission du hop (Python connaît l'item d'arrivée) → le hero crossfade **pendant** le slide, comme Plex. `_hero_after_landing()` poll `getFocusId` (30 ms, timeout 0,7 s, latest-wins) + repaint à l'atterrissage confirmée dans `_clear_focus_slot_later`. | Hero déjà basculé à +120 ms dans les captures ; plus de poursuite multi-rangées. |
| 4 | Peek en fondu retardé | Conséquence du park (conditions qui reversaient) — résolu par le sticky `AuraFocusSlot` : la rangée suivante reste opaque et stable. | — |
| 5 | Zoom 104 % | Conservé — extension Aura volontaire (documentée dans PARITY.md). | — |
| 6 | Durées | Slides colonne + contre-slides 250 → **280 ms**, glides `AuraRowSwap` 220 → 280 ms (Plex ~300 ms, Kodi rend plus snappy légèrement en dessous). | — |

**Bug corrigé en vol** : `AuraFocusSlot` pouvait rester collée indéfiniment
(worker tué par le compteur `_focus_generation` partagé avec `_defer_focus`)
→ deux conditions de slide vraies simultanément → colonne hors écran, rangées
invisibles avec focus sain. Corrigé : compteur dédié `_fslot_gen` + watchdog
qui libère la propriété à `settle+timeout` si aucun rebind plus récent ne l'a
reprise.

**Non livré** : le dip ~30 % du glide reste une concession (le contenu plonge
brièvement au lieu de rester opaque comme chez Plex) — supprimer le void à 100 %
exigerait une rangée entrante pré-liée (slot supplémentaire rendu hors écran),
architecture à évaluer séparément.
