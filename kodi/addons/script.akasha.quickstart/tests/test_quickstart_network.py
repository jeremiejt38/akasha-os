import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import quickstart_network as net  # noqa: E402

SAMPLE_OUTPUT = """\
*AO Wired                ethernet_dca632af47be_cable
*   Bbox-3AEEFA4E        wifi_dca632af47bf_42626f782d3341454546413445_managed_psk
*   Bbox-3AEEFA4E-5GHz   wifi_dca632af47bf_42626f782d33414545464134452d3547487a_managed_psk
    Fbx_maison_hm        wifi_dca632af47bf_4662785f6d6169736f6e5f686d_managed_psk
    Freebox 324429       wifi_dca632af47bf_46726565626f782d333234343239_managed_psk
"""


class ParseConnmanServicesTests(unittest.TestCase):
    def test_parses_all_lines(self):
        services = net.parse_connman_services(SAMPLE_OUTPUT)
        self.assertEqual(len(services), 5)

    def test_ethernet_service_parsed(self):
        services = net.parse_connman_services(SAMPLE_OUTPUT)
        eth = services[0]
        self.assertEqual(eth['name'], 'AO Wired')
        self.assertEqual(eth['service_id'], 'ethernet_dca632af47be_cable')
        self.assertTrue(eth['favorite'])
        self.assertFalse(eth['is_wifi'])

    def test_wifi_service_parsed(self):
        services = net.parse_connman_services(SAMPLE_OUTPUT)
        wifi = services[1]
        self.assertEqual(wifi['name'], 'Bbox-3AEEFA4E')
        self.assertTrue(wifi['is_wifi'])
        self.assertTrue(wifi['favorite'])

    def test_non_favorite_service_parsed(self):
        services = net.parse_connman_services(SAMPLE_OUTPUT)
        non_fav = services[3]
        self.assertFalse(non_fav['favorite'])

    def test_name_with_spaces_preserved(self):
        services = net.parse_connman_services(SAMPLE_OUTPUT)
        spaced = [s for s in services if s['name'] == 'Freebox 324429']
        self.assertEqual(len(spaced), 1)

    def test_empty_output(self):
        self.assertEqual(net.parse_connman_services(''), [])

    def test_garbage_line_ignored(self):
        services = net.parse_connman_services('not a real connman line\n')
        self.assertEqual(services, [])


if __name__ == '__main__':
    unittest.main()
