# Rapports d'utilisation de Talos — Akasha OS

Ce document consigne les utilisations de Talos sur le projet Akasha OS : prompts, résultats,
problèmes rencontrés, corrections apportées et apprentissages.

## Format d'une entrée

```markdown
## YYYY-MM-DD — <titre du job>

- **Job ID** : `<id>`
- **Label** : `<label>`
- **Fichiers concernés** : `<chemins>`
- **Provider** : `<provider>`
- **Validation** : `<commande>` ✅ / ❌
- **Résultat** : <résumé>

### Prompt (résumé)

<résumé du prompt envoyé à Talos>

### Problèmes constatés

1. ...

### Corrections appliquées

- ...

### Évaluation

✅ Réussi / ⚠️ Partiel / ❌ Échoué

### Apprentissages pour les prochains prompts

- ...
```

## Entrées

## 2026-08-15 — Mode Ambiant v0.12 : settings.xml + docs/TESTING.md (échec réseau)

- **Job IDs** : `ac405ef6` (ambient-settings-xml), `a988019b` (ambient-testing-doc)
- **Batch** : `1443d4c3`
- **Fichiers concernés** : `kodi/addons/screensaver.akasha.ambient/resources/settings.xml`,
  `docs/TESTING.md` (aucun des deux jamais écrit par Talos)
- **Provider** : `ollama/qwen2.5-coder:14b`
- **Validation** : jamais atteinte
- **Résultat** : échec — les deux jobs sont restés bloqués plus de 5 minutes avant annulation.

### Diagnostic

- `talos_daemon_status` indiquait `daemon_running: true`, mais je n'avais pas vérifié la
  connectivité réelle vers l'hôte Ollama avant de soumettre le batch (étape pourtant listée dans
  `docs/talos-instructions.md`).
- `ping 10.20.0.4` : 100% de perte. Le tunnel WireGuard (`pc-principal`) était pourtant actif avec
  un handshake récent — ce n'est donc pas le VPN qui est en cause, mais l'hôte `nzxt`
  (192.168.1.100, cible `10.20.0.4` en VPN) qui héberge Ollama et qui semblait éteint ou avec
  Ollama arrêté (`curl http://10.20.0.4:11434/api/tags` a timeout après 5s).
- Log du job : `OllamaError: ... litellm.Timeout: Connection timed out after None seconds.`

### Action

- Jobs annulés (`talos_cancel`).
- Les deux fichiers ont été écrits directement (tâches mécaniques et rapides, pas besoin de
  réessayer une fois l'indisponibilité réseau identifiée).

### Apprentissages

- Toujours exécuter concrètement l'étape "VPN actif (`ping 10.20.0.4`)" de la checklist pré-job
  avant de soumettre, pas seulement vérifier l'état du daemon Talos (qui peut être `running` sans
  qu'Ollama soit joignable).
- Une non-réponse ICMP n'implique pas forcément un problème de tunnel VPN : vérifier aussi l'hôte
  cible lui-même (ici, le PC `nzxt` qui héberge Ollama doit être allumé et Ollama démarré).

## 2026-08-18 — aura: connector_client.py (module pur)

- **Job ID** : `b5ac55d2`
- **Label** : `aura: connector_client.py (module pur)`
- **Fichiers concernés** : `resources/lib/connector_client.py`, `tests/test_connector_client.py`
- **Provider** : `ollama`
- **Validation** : `python3 -m unittest kodi.addons.script.akasha.aura.tests.test_connector_client -v` ❌ (erreur de chemin de module dans mon propre `validate_cmd`, pas un bug du code)
- **Résultat** : code correct après relecture, appliqué avec des adaptations mineures de style pour matcher `plex_client.py`/`test_plex_client.py` (import direct `import connector_client` plutôt que manipulation de `sys.path`, `MockHTTPResponse` façon `test_plex_client.py` plutôt que `MagicMock` générique). 54/54 tests passent après intégration.

### Prompt (résumé)

Créer `connector_client.py` (même style stdlib-only que `plex_client.py`) avec une classe
`ConnectorClient` (login, is_authenticated, on_deck, recently_added, sections) parlant à l'API
REST du connector (`akasha-os-connector`), plus les tests unitaires correspondants.

### Problèmes constatés

1. `validate_cmd` que j'ai fourni (`python3 -m unittest kodi.addons.script.akasha.aura.tests.test_connector_client`) suppose un layout de package Python complet depuis la racine du repo, alors que les tests de ce projet s'exécutent avec `PYTHONPATH=resources/lib` depuis le dossier de l'addon (`cd kodi/addons/script.akasha.aura && PYTHONPATH=resources/lib python3 -m unittest discover tests`). Erreur d'environnement de ma part, pas du code généré.
2. Le fichier de test généré par Talos importait via une manipulation manuelle de `sys.path` (`sys.path.insert(0, ...)`) plutôt que de suivre le pattern déjà établi (import direct, `PYTHONPATH` géré par la commande de test) — corrigé pour rester cohérent avec `test_plex_client.py`.
3. Le test `test_http_error_raises_connector_api_error` mockait `urlopen` avec une `Exception` générique plutôt qu'une vraie `urllib.error.HTTPError` — ne testait donc pas le vrai chemin de code (le `except urllib.error.HTTPError` de `_request` n'aurait pas intercepté une `Exception` générique). Réécrit avec une vraie `HTTPError`.

### Corrections appliquées

- Réécriture du fichier de test pour suivre exactement le pattern `test_plex_client.py`
  (`MockHTTPResponse`, import direct, mock avec une vraie `HTTPError`).
- Le fichier `connector_client.py` généré était fonctionnellement correct (logique d'auth, gestion
  d'erreurs, structure des méthodes) — appliqué avec seulement des ajustements de style mineurs.

### Apprentissages

- Toujours vérifier la commande de lancement des tests réellement utilisée par le projet
  (`PYTHONPATH=...`, `discover`, etc.) avant de la donner comme `validate_cmd` à Talos — ne pas
  supposer un layout de package standard.
- Pour un test d'erreur HTTP, insister dans le prompt sur l'usage d'une vraie exception du bon
  type (`urllib.error.HTTPError`) plutôt qu'une `Exception` générique, qui ne validerait pas le
  chemin de gestion d'erreur réel.
