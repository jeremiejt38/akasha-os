#!/usr/bin/env python3
"""Akasha Guide — deprecated addon entry point.

The actual menu logic now lives in /storage/.kodi/scripts/akasha-guide.py,
bound directly to the controller Guide button via
userdata/keymaps/keymap.xml. This addon package is kept only to host the
shared skin resources (Guide.xml, fonts, media) used by the custom XML
window style; this default.py simply forwards to the real script so that
RunAddon(script.akasha.guide) keeps working if invoked anywhere.
"""
import xbmc

if __name__ == '__main__':
    xbmc.executebuiltin('RunScript(/storage/.kodi/scripts/akasha-guide.py)')
