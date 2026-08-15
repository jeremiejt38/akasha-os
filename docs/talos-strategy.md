# Stratégie d'utilisation de Talos — Akasha OS

## Objectif

Talos est utilisé comme outil de génération de code auxiliaire pour décharger les tâches isolées et
mécaniques (scripts Python Kodi, fragments de skin XML, documentation), pendant que la logique
sensible (CEC, systemd, séquences de redémarrage/extinction, patchs de skin par regex) reste pilotée
directement.

## Principes d'utilisation

1. **Morceaux isolés** : chaque job Talos porte sur une tâche précise et limitée (un script, une
   fonction, un fragment XML, un fichier de doc).
2. **Vérification systématique** : tout résultat de Talos est relu et validé avant intégration —
   jamais de copier-coller aveugle, surtout pour du code qui finira déployé sur le Raspberry Pi du
   salon.
3. **Réessai** : si un job échoue (résultat incorrect ou validation KO), on réessaie jusqu'à 3 fois
   avec un prompt affiné.
4. **Pas d'abandon** : un échec sur un job n'empêche pas d'utiliser Talos sur les jobs suivants.
5. **Rapport** : chaque utilisation de Talos est consignée dans `docs/talos-reports.md`.

## Types de jobs adaptés à Talos

- Scripts Kodi Python autonomes et testables hors runtime `xbmc` (ex : parsing, utilitaires,
  helpers de formatage, petits scripts `kodi/scripts/*.py` sans dépendance directe aux modules
  `xbmc*`).
- Fragments de documentation structurée (README, docs/*.md, résumés de changelog).
- Scripts shell utilitaires isolés (vérifiables avec `sh -n`).
- Génération de squelettes de fichiers de configuration (JSON, `addon.xml` basique) à partir d'un
  modèle existant.
- Tests unitaires ciblés sur des fonctions pures (sans mocker `xbmcgui`/`xbmcaddon`).

## Types de jobs à NE PAS déléguer à Talos

- Toute logique touchant CEC, `systemctl reboot|poweroff`, splash/framebuffer : erreurs difficiles
  à valider sans le device réel et potentiellement disruptives (TV du salon).
- Les patchs de skin par regex (`skin-patches/*.py`) qui modifient `DialogContextMenu.xml`,
  `DialogConfirm.xml`, etc. : trop fragile pour une génération non supervisée, un regex mal formé
  peut casser le skin Arctic Horizon 2 en silence.
- Code Kodi qui dépend de `xbmc`, `xbmcgui`, `xbmcaddon` à l'exécution (non testable sans Kodi ;
  toute erreur ne se voit qu'au déploiement sur le Pi).
- `install.sh` / `apply.sh` et tout ce qui touche au déploiement sur l'infrastructure réelle.
- Décisions d'architecture, de structure de menu ou d'UX.
- Revue finale avant merge et avant déploiement sur le Pi.

## Workflow d'un job Talos

1. **Préparation du prompt** :
   - Contexte clair (fichiers ou snippets pertinents, style du projet).
   - Objectif précis et atomique.
   - Contraintes (style KSP, pas de secrets, pas d'IP/mot de passe du Pi en dur).
   - Commande de validation si possible (`python3 -m py_compile ...`, `sh -n ...`, test unitaire).

2. **Soumission** via `talos_add` ou `talos_add_batch`.

3. **Suivi** via `talos_status` ou `talos_batch_status` (non bloquant).

4. **Validation** du résultat :
   - Lire les fichiers proposés.
   - Vérifier la cohérence avec le reste du code et l'absence de secrets.
   - Lancer la validation prévue.
   - Si KO : relancer jusqu'à 3 fois.

5. **Intégration** manuelle si nécessaire après échecs, puis test réel sur le Pi (PixelCamera +
   `kodi-send`) avant de considérer la tâche terminée.

6. **Rapport** dans `docs/talos-reports.md` : job, prompt, résultat, problèmes, corrections,
   apprentissages.

## Exemple de prompt

```
Crée le fichier kodi/scripts/akasha-version.py contenant une fonction pure
`read_version(manifest_path: str) -> str` qui lit .release-please-manifest.json
et retourne la valeur de la clé ".".

Contraintes :
- Python 3, stdlib uniquement (json, os).
- Aucune dépendance à xbmc/xbmcgui/xbmcaddon.
- Gérer le cas fichier absent en levant FileNotFoundError.
- Docstring courte.

Validation : python3 -m py_compile kodi/scripts/akasha-version.py
```

## Rapports Talos

Les rapports sont stockés dans `docs/talos-reports.md`. Chaque entrée contient :
- Date et job ID.
- Description du job.
- Prompt utilisé (résumé).
- Évaluation : réussi / partiel / échoué.
- Problèmes constatés et corrections.
- Apprentissages pour les prochains prompts.
