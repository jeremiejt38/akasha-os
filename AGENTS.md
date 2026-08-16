# Akasha OS Development Guidelines

- Follow `docs/PROJECT_WORKFLOW.md` (synced from KSP under `.devin/templates/project-standards/`) for branches, Conventional Commits, validation, merges, releases and branch cleanup.
- Keep `main` stable. Work from short-lived `feature/*`, `fix/*`, `docs/*`, `chore/*`, `refactor/*` or `test/*` branches (direct commits on `main` are tolerated for single-session iterative work, as long as each commit stays atomic and correctly typed).
- Keep commits atomic and use Conventional Commits. This is a **public** repository: commit descriptions must be in **English**.
- Release only through the Release Please PR and its annotated `vX.Y.Z` tag. Default to patch releases; a minor release requires a coherent feature milestone; never approve a major release without explicit maintainer approval.
  - Progression attendue : `1.0.0 → 1.0.1 (patch) → 1.0.2 (patch) → 1.1.0 (mineure) → 1.1.1 (patch) → …`.
- **Release + redeploy after every patch that reaches the device**: the Guide menu and the native context menu header both display the running version (`vX.Y.Z`, read from `package.json` at install time by `scripts/install.sh` / `skin-patches/patch_contextmenu_title.py`). This is the visual proof that a fix was actually applied on the Raspberry Pi. After committing `fix:`/`refactor:`/`feat:` changes:
  1. Push to `main`.
  2. Let the "Release Please" GitHub Action open its release PR, then merge it (bumps `package.json` + `.release-please-manifest.json`, updates `CHANGELOG.md`, creates the tag).
  3. Pull the merge commit locally and redeploy with `./scripts/apply.sh <pi-ip> <pi-password>`.
  4. Verify the new version label on screen (PixelCamera + `kodi-send`, or ask the user to check the TV) before considering the patch done.
- Never jump directly from `X.0.0` to `(X+1).0.0`. A major version consolidates a roadmap of milestones that must each ship first as their own minor release within the current major series (`X.1.0`, `X.2.0`, …), with patch versions between them (`X.0.1`, `X.0.2`, `X.1.1`, …); see `docs/PROJECT_WORKFLOW.md` ("Progression de version et feuille de route").
- Keep one authoritative project version (`package.json`, the Node.js SSOT). Keep detailed release history in `CHANGELOG.md` and GitHub Releases, not as a growing README section.
- Never commit secrets, private data (Pi IP/password, Wi-Fi credentials, etc.) or generated production artifacts (e.g. `splash-reboot.png`/`splash-shutdown.png` are generated at install time, not versioned).
- The Raspberry Pi (`root@192.168.1.88`, LibreELEC/Kodi) is a real living-room device: restart/shutdown/CEC actions are destructive to test — confirm with the maintainer before triggering a poweroff, or use the less disruptive "Redemarrer Akasha" (Kodi-only restart) path when possible.
- Talos is enabled for isolated, non-`xbmc*`, non-skin-regex jobs (see `docs/talos-strategy.md` and `docs/talos-instructions.md`). Log every use in `docs/talos-reports.md`.
