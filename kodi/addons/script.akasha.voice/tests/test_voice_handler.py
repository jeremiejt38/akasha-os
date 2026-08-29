"""Tests for Akasha Voice voice_handler (c8c8548a Section 1)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import voice_handler  # noqa: E402


class Section1NavigationTests(unittest.TestCase):
    def test_open_tab_fr(self):
        self.assertEqual(voice_handler.handle('ouvre divertissement'), 'RunScript(script.akasha.aura)')
        self.assertEqual(voice_handler.handle('va dans jeux'), 'RunScript(script.akasha.aura)')
        self.assertEqual(voice_handler.handle('ouvre applications'), 'RunScript(script.akasha.aura)')

    def test_open_tab_en(self):
        self.assertEqual(voice_handler.handle('open entertainment', lang='en'), 'RunScript(script.akasha.aura)')
        self.assertEqual(voice_handler.handle('go to games', lang='en'), 'RunScript(script.akasha.aura)')

    def test_back_and_home(self):
        self.assertEqual(voice_handler.handle('retour'), 'Action(Back)')
        self.assertEqual(voice_handler.handle('accueil'), 'RunScript(script.akasha.aura)')
        self.assertEqual(voice_handler.handle('back', lang='en'), 'Action(Back)')

    def test_directional(self):
        self.assertEqual(voice_handler.handle('monte'), 'Input.Up')
        self.assertEqual(voice_handler.handle('descends'), 'Input.Down')
        self.assertEqual(voice_handler.handle('gauche'), 'Input.Left')
        self.assertEqual(voice_handler.handle('droite'), 'Input.Right')
        self.assertEqual(voice_handler.handle('selectionne'), 'Input.Select')
        self.assertEqual(voice_handler.handle('ok', lang='en'), 'Input.Select')

    def test_settings_menu_reload(self):
        self.assertEqual(voice_handler.handle('ouvre les parametres'), 'RunScript(script.akasha.aura,opensettings)')
        self.assertEqual(voice_handler.handle('affiche le menu'), 'Action(ContextMenu)')
        self.assertEqual(voice_handler.handle('recharge l interface'), 'ReloadSkin()')

    def test_libraries_and_genres(self):
        self.assertEqual(voice_handler.handle('affiche mes bibliotheques'), 'RunScript(script.akasha.aura,divert=library)')
        self.assertEqual(voice_handler.handle('affiche les genres'), 'RunScript(script.akasha.aura,divert=genres)')

    def test_unknown_phrase(self):
        self.assertIsNone(voice_handler.handle('phrase bidon inconnue'))

    def test_empty_phrase(self):
        self.assertIsNone(voice_handler.handle(''))
        self.assertIsNone(voice_handler.handle('   '))


class Section2PlaybackTests(unittest.TestCase):
    def test_play_pause_stop(self):
        self.assertEqual(voice_handler.handle('lecture'), 'PlayerControl(Play)')
        self.assertEqual(voice_handler.handle('pause'), 'PlayerControl(Pause)')
        self.assertEqual(voice_handler.handle('stop'), 'Stop')

    def test_next_previous(self):
        self.assertEqual(voice_handler.handle('suivant'), 'PlayerControl(Next)')
        self.assertEqual(voice_handler.handle('precedent'), 'PlayerControl(Previous)')


class Section3VolumeTests(unittest.TestCase):
    def test_volume(self):
        self.assertEqual(voice_handler.handle('monte le son'), 'Action(VolumeUp)')
        self.assertEqual(voice_handler.handle('baisse le son'), 'Action(VolumeDown)')
        self.assertEqual(voice_handler.handle('coupe le son'), 'Mute')


class Section4SearchTests(unittest.TestCase):
    def test_search_with_slot(self):
        builtin = voice_handler.handle('cherche interstellar')
        self.assertIn('interstellar', builtin)

    def test_play_title_with_slot(self):
        builtin = voice_handler.handle('lance matrix')
        self.assertIn('matrix', builtin)


class Section5MusicTests(unittest.TestCase):
    def test_play_music(self):
        self.assertEqual(voice_handler.handle('joue de la musique'), 'PlayMedia(musicdb://songs/)')


class Section7EnergyTests(unittest.TestCase):
    def test_standby_shutdown(self):
        self.assertEqual(voice_handler.handle('mets en veille'), 'Suspend')
        self.assertEqual(voice_handler.handle('eteins akasha'), 'Powerdown')


if __name__ == '__main__':
    unittest.main()
