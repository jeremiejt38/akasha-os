# Instructions d'utilisation de Talos — Akasha OS

> À relire avant chaque utilisation de Talos (CLI, MCP `talos_*`, soumission de job).

## Modèle et endpoint Ollama

- Modèle rapide/lent local : `ollama/qwen2.5-coder:14b` (config globale `~/.talos/.env`, partagée
  entre projets).
- Endpoint Ollama : `http://10.20.0.4:11434` (via VPN AkashaVPN).
- Vérifier que le VPN est actif avant de soumettre un job (`ping 10.20.0.4`).
- Format d'édition Aider : `diff` (SEARCH/REPLACE).

## Workflow de sécurité

1. **Sandbox par défaut** : `TALOS_AUTO_APPLY=false`, aucune application automatique sur le repo.
2. **Pas de code `xbmc*` non supervisé** : ne jamais laisser Talos écrire directement dans un
   fichier qui tourne dans le runtime Kodi (`kodi/addons/**/default.py`, `kodi/scripts/*.py`
   important comme `akasha-guide.py`, `akasha-sleep.py`) sans relecture complète — ces fichiers ne
   sont testables qu'en conditions réelles sur le Pi.
3. **Pas de patch de skin XML par regex** délégué à Talos (`skin-patches/*.py`) : trop risqué sans
   supervision directe.
4. **Validation adaptée au projet** (pas de venv Python comme Sentarr) :
   - Python pur (sans `xbmc*`) : `python3 -m py_compile <fichier>`.
   - Shell : `sh -n <fichier>` (vérification de syntaxe).
   - JSON : `python3 -c "import json; json.load(open('<fichier>'))"`.
   - XML (skin) : `python3 -c "import xml.etree.ElementTree as ET; ET.parse('<fichier>')"`.
5. **Revue manuelle obligatoire** avant d'appliquer tout fichier généré par Talos.
6. **Pas de secrets** : jamais l'IP ou le mot de passe du Raspberry Pi (`root@192.168.1.88`) dans un
   prompt, un fichier généré ou une commande de validation.
7. **Réessai max 3 fois** par job. En cas d'échec persistant, implémenter manuellement mais
   continuer à utiliser Talos pour les jobs suivants.

## Découpage des jobs — limite de tokens

- Le modèle `qwen2.5-coder:14b` a une fenêtre de contexte limitée ; préférer plusieurs petits jobs
  indépendants à un seul job monolithique.
- Chaque job vise un objectif atomique avec sa propre commande de validation.
- Pour un chantier de la v0.12, découper par sous-tâche (un script, un fragment de skin, un
  document) plutôt que par gros morceau fonctionnel.
- Utiliser `talos chain <batch_id>` pour enchaîner des étapes dépendantes sans attendre
  manuellement chaque job.

## Rapports

- Consigner chaque utilisation de Talos dans `docs/talos-reports.md`.
- Noter le job ID, le provider, la validation, le résultat et les apprentissages.

## Vérification pré-job

- [ ] VPN AkashaVPN actif (`ping 10.20.0.4`).
- [ ] `talos_daemon_status` renvoie `daemon_running: true`.
- [ ] Le prompt est atomique, isolé, et ne touche pas à un fichier runtime `xbmc*` sensible ou à un
      patch de skin regex.
- [ ] Une commande de validation est définie et adaptée (pas de venv Python, cf. ci-dessus).

## Post-job

- [ ] Relire le diff proposé.
- [ ] Vérifier qu'aucun secret (IP/mdp du Pi, tokens) n'apparaît.
- [ ] Lancer la validation prévue.
- [ ] Mettre à jour `docs/talos-reports.md`.
- [ ] Pour tout code destiné au Pi : test réel après déploiement (PixelCamera + `kodi-send`) avant
      de considérer la tâche terminée.

## Statistiques, review et coût

- `talos_daemon_status` / `talos status` / `talos dashboard` : état live et statistiques agrégées
  (`~/.talos/stats.json`), tokens, durée, coût estimé Devin vs Ollama local (`0` pour Ollama).
- `talos review <job_id>` : notation manuelle 0–10 d'un job terminé, alimente le *negative
  preamble* utilisé pour les prompts suivants du même modèle.
- Ces statistiques sont globales (partagées entre projets) ; seuls les rapports dans
  `docs/talos-reports.md` sont propres à Akasha OS.
