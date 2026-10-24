# Analyseur de performances (`analyser-de-performances`)

Collecteur léger en tâche de fond pour comprendre ce qui bloque, gèle ou
erreur sur le Pi, consultable après coup.

## Composants

- **`service.akasha.perfanalyzer`** — service Kodi (`start="startup"`, le
  plus tôt possible côté Kodi). Toutes les 10 s :
  - charge (`/proc/loadavg`), mémoire dispo (`/proc/meminfo`), température
    CPU (`/sys/.../thermal_zone0`), mémoire libre Kodi, état lecture/idle ;
  - `vcgencmd get_throttled` toutes les ~60 s (sous-voltage, fréquence
    plafonnée) ;
  - scan incrémental de `kodi.log` (offset suivi, lignes `ERROR`/`CRITICAL`,
    50 lignes max par tick) ;
  - **détection de stall** : si un tick prévu à 10 s s'exécute en >30 s,
    événement `loop_lag` (blocage système/GUI).
- **Marqueur de boot** écrit par `autostart.sh` (avant même Kodi) pour borner
  la fenêtre d'analyse.
- **Stockage borné** : `/storage/.config/akasha-os/perf/metrics.jsonl` et
  `errors.jsonl`, rotation à 512 Ko + 1 backup — aucune croissance en mémoire
  ni sur disque. Les anomalies sont aussi relayées dans `kodi.log` (WARNING).
- **CLI** : `analyser-de-performances`
  (`/storage/.config/akasha-os/bin/analyser-de-performances`, lien vers
  `/storage/.kodi/scripts/analyser-de-performances.py`) — imprime la fenêtre
  d'analyse, le dernier échantillon, le décompte par type d'anomalie, les
  derniers événements et les dernières erreurs Kodi.

## Seuils

| Anomalie | Seuil |
|---|---|
| `loop_lag` | tick > 3× l'intervalle prévu (10 s) |
| `high_temp` | ≥ 80 °C |
| `low_mem` | MemAvailable ≤ 150 Mo |
| `high_load` | load1 ≥ 4.0 |
| `throttled` | `vcgencmd get_throttled` ≠ `0x0` |
| `low_kodi_mem` | mémoire libre Kodi ≤ 100 Mo |
| erreurs Kodi | lignes `ERROR`/`CRITICAL` du `kodi.log` |

## Écran de chargement natif (même livraison)

`skin-patches/patch_native_loading.py` couvre les fenêtres de navigation
natives (Home, MyVideoNav, MyMusicNav, MyPrograms, MyPics, MyWeather,
MyGames, MyPlaylists, MyFileNav) d'un écran de chargement opaque et
permanent — fond de démarrage + logo Akasha (includes de la skin),
« Chargement… » et une vague organique (deux couches sinusoïdales
périodiques glissant en boucle, aucune rupture visible). Le menu Kodi reste
fonctionnel dessous mais n'apparaît jamais, y compris pendant le handoff
vers la lecture vidéo qui laissait transparaître Home une fraction de
seconde.
