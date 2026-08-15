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
