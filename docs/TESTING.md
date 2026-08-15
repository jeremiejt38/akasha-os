# Tests — Akasha OS

## Modules purs (sans Kodi)

Certains modules Python n'ont aucune dépendance à `xbmc`/`xbmcgui`/`xbmcaddon` et sont donc
testables avec un simple `python3`, sans installer ni lancer Kodi. C'est le cas des modules du
Mode Ambiant (`kodi/addons/screensaver.akasha.ambient/resources/lib/`) :
`config.py`, `content_manager.py`, `weather_client.py`, `energy.py`.

Lancer les tests :

```bash
cd kodi/addons/screensaver.akasha.ambient
python3 -m unittest discover -s tests -v
```

Ces tests couvrent uniquement la logique pure (validation de configuration, résolution du dossier
de contenu, calcul de la temporisation d'assombrissement, client météo avec accès réseau injecté).
Ils ne remplacent pas une vérification sur l'appareil réel.

## Code dépendant de Kodi

Tout ce qui importe `xbmc`, `xbmcgui` ou `xbmcaddon` (fenêtres `WindowXMLDialog`, services, skins
XML, actions CEC/`systemctl`) ne peut pas être testé unitairement en dehors du runtime Kodi. Ce
code doit être validé directement sur le Raspberry Pi :

1. Déployer avec `./scripts/apply.sh <ip-du-pi> <mot-de-passe>`.
2. Déclencher l'action à tester via `kodi-send --action='...'` (menus, screensaver, etc.).
3. Observer l'écran avec l'outil PixelCamera (voir le projet Atlas séparé) pour confirmer le rendu
   réel, sans avoir à être physiquement devant la TV.
4. Vérifier les logs Kodi (`/storage/.kodi/temp/kodi.log`) en cas de comportement inattendu.

## Vérification de syntaxe rapide

Avant de déployer, valider au minimum la syntaxe des fichiers modifiés :

```bash
# Python
python3 -m py_compile chemin/vers/le_fichier.py

# Shell
sh -n chemin/vers/le_script.sh

# XML (skins, addon.xml, settings.xml)
python3 -c "import xml.etree.ElementTree as ET; ET.parse('chemin/vers/le_fichier.xml')"
```

Ces vérifications n'attrapent que les erreurs de syntaxe, pas les erreurs de comportement Kodi
(control ID inexistant, info-label mal formé, etc.) — d'où la nécessité du test réel sur le Pi pour
tout ce qui touche à l'UI ou au matériel.
