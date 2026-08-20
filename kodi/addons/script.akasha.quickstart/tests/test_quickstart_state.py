import os
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import quickstart_state as state  # noqa: E402


class MarkerTests(unittest.TestCase):
    def test_not_completed_when_marker_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, 'sub', 'quickstart-completed')
            self.assertFalse(state.is_completed(marker))

    def test_completed_after_mark(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, 'sub', 'quickstart-completed')
            state.mark_completed(marker)
            self.assertTrue(state.is_completed(marker))

    def test_reset_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, 'quickstart-completed')
            state.mark_completed(marker)
            state.reset_completed(marker)
            self.assertFalse(state.is_completed(marker))

    def test_reset_completed_missing_file_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, 'never-created')
            state.reset_completed(marker)  # must not raise


class StepProgressTests(unittest.TestCase):
    def test_get_last_step_defaults_to_welcome_when_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, 'sub', 'last-step')
            self.assertEqual(state.get_last_step(marker), state.STEP_WELCOME)

    def test_save_and_get_last_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, 'last-step')
            state.save_step(state.STEP_NETWORK, marker)
            self.assertEqual(state.get_last_step(marker), state.STEP_NETWORK)

    def test_get_last_step_corrupt_file_defaults_to_welcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, 'last-step')
            with open(marker, 'w') as f:
                f.write('not-a-number')
            self.assertEqual(state.get_last_step(marker), state.STEP_WELCOME)

    def test_get_last_step_clamps_out_of_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, 'last-step')
            with open(marker, 'w') as f:
                f.write('999')
            self.assertEqual(state.get_last_step(marker), len(state.STEPS) - 1)

    def test_mark_completed_resets_step_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            done_marker = os.path.join(tmp, 'completed')
            step_marker = os.path.join(tmp, 'last-step')
            state.save_step(state.STEP_DISPLAY, step_marker)
            with unittest.mock.patch.object(state, 'STEP_MARKER_PATH', step_marker):
                state.mark_completed(done_marker)
            self.assertEqual(state.get_last_step(step_marker), state.STEP_WELCOME)


class StepMetadataTests(unittest.TestCase):
    def test_steps_cover_the_ten_steps_in_order(self):
        self.assertEqual(len(state.STEPS), 10)
        ids = [sid for sid, _ in state.STEPS]
        self.assertEqual(ids, list(range(10)))

    def test_step_title_known(self):
        self.assertEqual(state.step_title(state.STEP_WELCOME), 'Bienvenue')
        self.assertEqual(state.step_title(state.STEP_NETWORK), 'Connexion reseau')

    def test_step_title_unknown_returns_empty(self):
        self.assertEqual(state.step_title(999), '')

    def test_network_and_welcome_and_summary_not_skippable(self):
        self.assertFalse(state.is_skippable(state.STEP_WELCOME))
        self.assertFalse(state.is_skippable(state.STEP_NETWORK))
        self.assertFalse(state.is_skippable(state.STEP_SUMMARY))

    def test_other_steps_skippable(self):
        self.assertTrue(state.is_skippable(state.STEP_LANGUAGE))
        self.assertTrue(state.is_skippable(state.STEP_DISPLAY))
        self.assertTrue(state.is_skippable(state.STEP_CONTROLLERS))
        self.assertTrue(state.is_skippable(state.STEP_ACCOUNTS))
        self.assertTrue(state.is_skippable(state.STEP_CLOUD_GAMING))
        self.assertTrue(state.is_skippable(state.STEP_POWER))
        self.assertTrue(state.is_skippable(state.STEP_PROFILE))

    def test_clamp_step(self):
        self.assertEqual(state.clamp_step(-5), 0)
        self.assertEqual(state.clamp_step(50), len(state.STEPS) - 1)
        self.assertEqual(state.clamp_step(3), 3)


if __name__ == '__main__':
    unittest.main()
