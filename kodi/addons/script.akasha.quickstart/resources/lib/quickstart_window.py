"""Akasha Quick Start -- first-run setup wizard window.

Phase 1 (plan 3aba4284) scope only: the generic multi-step navigation
skeleton (Suivant/Precedent/Passer, progress indicator, per-step
placeholder content, completion marker). Real step content (network
scan, display test, controller pairing, account linking...) lands in
later phases, each step's group in QuickStart.xml gets filled in without
touching this navigation scaffolding.
"""
import xbmc
import xbmcgui

import quickstart_state as state

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

BTN_PREVIOUS = 100
BTN_NEXT = 101
BTN_SKIP = 102

STEP_TITLE_LABEL_ID = 11
STEP_PROGRESS_LABEL_ID = 12
SUMMARY_LABEL_ID = 1001


class QuickStartWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.step = state.STEP_WELCOME
        self._finished = False
        # Placeholder for per-step results, filled in as later phases add
        # real content (network SSID chosen, display resolution confirmed,
        # accounts linked...) -- surfaced on the Recapitulatif step.
        self.results = {}

    def onInit(self):
        self._show_step(state.STEP_WELCOME)

    def _show_step(self, step_id):
        self.step = state.clamp_step(step_id)
        self.setProperty('QSStep', str(self.step))

        try:
            self.getControl(STEP_TITLE_LABEL_ID).setLabel(state.step_title(self.step))
        except RuntimeError:
            pass
        try:
            self.getControl(STEP_PROGRESS_LABEL_ID).setLabel(
                'Etape {} sur {}'.format(self.step + 1, len(state.STEPS)))
        except RuntimeError:
            pass

        is_last = self.step == len(state.STEPS) - 1
        try:
            next_btn = self.getControl(BTN_NEXT)
            next_btn.setLabel('Terminer' if is_last else 'Suivant')
        except RuntimeError:
            pass
        try:
            skip_btn = self.getControl(BTN_SKIP)
            skip_btn.setVisible(state.is_skippable(self.step) and not is_last)
        except RuntimeError:
            pass
        try:
            prev_btn = self.getControl(BTN_PREVIOUS)
            prev_btn.setVisible(self.step > state.STEP_WELCOME)
        except RuntimeError:
            pass

        if self.step == state.STEP_SUMMARY:
            self._render_summary()

    def _render_summary(self):
        # Phase 1 placeholder -- Phase 6 fills this with the real choices
        # made across every step (reseau connecte, TV configuree, manette
        # appairee, comptes lies/sautes, profil cree), per section 2 etape 10.
        try:
            self.getControl(SUMMARY_LABEL_ID).setLabel(
                "Recapitulatif detaille a venir (plan 3aba4284, etape 10).")
        except RuntimeError:
            pass

    def _next(self):
        if self.step == len(state.STEPS) - 1:
            self._finish()
            return
        self._show_step(self.step + 1)

    def _previous(self):
        if self.step == state.STEP_WELCOME:
            return
        self._show_step(self.step - 1)

    def _skip(self):
        if not state.is_skippable(self.step):
            return
        self._next()

    def _finish(self):
        state.mark_completed()
        self._finished = True
        self.close()
        xbmc.executebuiltin('RunScript(script.akasha.aura)')

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._confirm_exit()
            return
        super().onAction(action)

    def _confirm_exit(self):
        # Section 1: an early exit must NOT count as "completed" -- the
        # marker is only ever set from _finish() above, so simply closing
        # here (without calling it) already guarantees the wizard
        # re-appears next boot. Still ask for a clear confirmation instead
        # of exiting on a single stray Back press, per section 1's
        # "fermeture avec confirmation claire".
        if xbmcgui.Dialog().yesno(
                'Akasha Quick Start',
                "Quitter l'assistant ? Vos choix deja valides sont conserves, "
                "il se represente au prochain demarrage tant qu'il n'est pas termine."):
            self.close()

    def onClick(self, controlID):
        if controlID == BTN_PREVIOUS:
            self._previous()
        elif controlID == BTN_NEXT:
            self._next()
        elif controlID == BTN_SKIP:
            self._skip()
