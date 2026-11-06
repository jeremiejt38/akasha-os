# PLAN-1c4561df — Scroll & progress-bar polish (Aura)

User feedback (live, on Pi): visual polish of scrolling behaviour and the
"Continuer à regarder" progress bar. All items verified live before close.

## Requirements

1. **Progress bar thickness + focus zoom** [DONE — implemented]
   - The orange `AuraProgress` bar on poster cards is too thin → 4px → 6px,
     bottom edge kept flush, `prog-bar.png` regenerated at 24×6.
   - The poster zooms 104-105% on focus but the bar stays static → give the
     bar the same zoom, centred on the *poster* centre (explicit `center=`
     so the bar tracks the poster's bottom edge).

2. **No wrap-around, ever** [DONE — verified live]
   - Horizontal rows: Right at the last item dead-ends (53-item row: 6
     extra Right presses stayed on item 53).
   - Vertical lists/panels: Down at the last item dead-ends.
   - Applies to: reco rows (511x-551x), sidebar 3310, A-Z rail 3250, library
     grid 3230, category panel 6010, Jeux 2060, search 2010, app grid 2030,
     and the same patterns in AuraStore/AuraApp/AuraSearch/AuraMenu/
     AuraSettingsPanel/AuraSwitcher/AuraRelated/AuraDetail/AuraOsd*/
     AuraPerson/AuraProfileMenu/AuraWhoWatching.
   - Mechanism: converted every `type="list"` to `type="fixedlist"`.
     Kodi's plain `list` wraps internally as soon as declared navigation
     fails (non-focusable target falls back to spatial nav); `fixedlist`
     dead-keys natively at both ends while keeping focus and ring. The
     non-focusable label 3260 stays as the dead-end target for `panel`
     directions only.

3. **Sidebar edge gating** [DONE — verified live]
   - Holding Left in a horizontal row must stop at the first item; the
     sidebar opens only after the user releases and presses Left again.
   - Final mechanism (after several discarded attempts): each reco row
     declares `left` = a dedicated guard button (`RECO_GUARD_IDS`,
     lid+80) permanently. The guard is invisible, self-pinned left,
     Right returns to its row, Up/Down mirror the row chain, and it draws
     the same focus ring over the first card so the park is seamless.
     All `Control.HasFocus(5x1x)` conditions that drive the column slide
     and row masking were extended with the row's guard ids so a parked
     focus keeps the row translated and rendered.
   - Why not timing/rewire: Kodi coalesces rapid key repeats, so the edge
     press may never reach `onAction` at all, and delivery gaps >0.5 s can
     occur mid-hold. Declarative guards are immune to both.
   - Exit: a parked LEFT with a >0.5 s gap arms a 250 ms confirm timer;
     another LEFT arriving first aborts it (still holding), otherwise the
     focus jumps to the rail (`_gate_left_edge`).
   - Verified: 3 soak cycles — 50×85 ms holds park on the guard (sidebar
     closed), Right returns to pos0, fresh Left after ~1 s opens the rail.

4. **Frame-by-frame capture tooling** [DONE — alternate method]
   - `xbmc.RenderCapture` is a dead end on this build (GBM readback
     unsupported — `getImage()` returns empty buffers).
   - Working substitute: slow the deployed animation to ~2200 ms and fire
     a `screenshot` JSON-RPC burst (~60 ms cadence) — yielded real
     mid-animation frames, enough to diagnose and verify.

5. **Softer vertical transition** [DONE — verified live]
   - Diagnosis (from slowed frames): the harshness was `inout` easing +
     simultaneous slide/fade/zoom + an instant content rebind (teleport)
     at the last visible slot.
   - Fixes: slide `easing` → `out`; added `AuraRowSwap` alternating
     property (d1/d2/u1/u2) driving four conditional one-shot animations
     on the sliding group so a rebound column glides one row pitch
     (472 px) instead of teleporting, with a short fade to mask art
     materialisation. Confirmed on-device: the rebound row enters at ~40%
     opacity mid-glide.

## Delivery

- Branch `fix/scroll-polish`, atomic Conventional Commits, PR, Release
  Please, apply.sh deploy, live verification + captures, decisions.md,
  Atlas journal.
