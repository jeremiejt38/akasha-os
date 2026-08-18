# Changelog

## [0.35.6](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.35.5...akasha-os-v0.35.6) (2026-08-18)


### Bug Fixes

* **aura:** retry Divertissement load if a transient failure left it empty ([b776025](https://github.com/jeremiejt38/akasha-os/commit/b7760254bbd55fbb2847dc181b53c020d3b53894))

## [0.35.5](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.35.4...akasha-os-v0.35.5) (2026-08-18)


### Bug Fixes

* **aura:** local cache self-heals if its sqlite table ever goes missing ([4c750c7](https://github.com/jeremiejt38/akasha-os/commit/4c750c7f67a5df264157dbaffb1155736689f69f))

## [0.35.4](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.35.3...akasha-os-v0.35.4) (2026-08-18)


### Bug Fixes

* **aura,ambient:** guard against stacking a duplicate window on repeat RunScript triggers ([8ef80e5](https://github.com/jeremiejt38/akasha-os/commit/8ef80e5f70c52e3ef2978cda715f38fa46b200b6))

## [0.35.3](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.35.2...akasha-os-v0.35.3) (2026-08-18)


### Bug Fixes

* **aura:** stale search/genre/sort state leaking into reused Bibliotheque window ([ac39a60](https://github.com/jeremiejt38/akasha-os/commit/ac39a60f47c5abf930b0b5d37423a035f6e31dc4))

## [0.35.2](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.35.1...akasha-os-v0.35.2) (2026-08-18)


### Bug Fixes

* **aura:** local page cache corrupted (items, total) tuples into [items, total] lists ([76618ef](https://github.com/jeremiejt38/akasha-os/commit/76618efe1cf9c32fb678861c01a8be0425e6b7c8))

## [0.35.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.35.0...akasha-os-v0.35.1) (2026-08-18)


### Bug Fixes

* **aura:** reuse sub-windows instead of re-instantiating them on every open ([b458bc1](https://github.com/jeremiejt38/akasha-os/commit/b458bc165fc22e68b5c059f5e74b8ebfb655cc1f))

## [0.35.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.34.0...akasha-os-v0.35.0) (2026-08-18)


### Features

* **aura:** show the real total item count immediately (plan a3f9c2e1) ([ad9642f](https://github.com/jeremiejt38/akasha-os/commit/ad9642f9cd1de2497f1c0a6db2797602ccef77c2))

## [0.34.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.33.2...akasha-os-v0.34.0) (2026-08-18)


### Features

* **aura:** Bibliotheque as a poster grid instead of a plain text list ([e1b0669](https://github.com/jeremiejt38/akasha-os/commit/e1b06699d12e71ef606a8469330f0ddbcc11297d))

## [0.33.2](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.33.1...akasha-os-v0.33.2) (2026-08-18)


### Bug Fixes

* **aura:** focus the first Recommandations row on open instead of the back button ([ce4f5ce](https://github.com/jeremiejt38/akasha-os/commit/ce4f5ce5aae46f2871c64875368e0ec7430eec49))
* **aura:** only highlight the actually-focused item, not every list's last selection ([ea1532b](https://github.com/jeremiejt38/akasha-os/commit/ea1532bc2119d60e73ec7d16660d9568135e82be))

## [0.33.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.33.0...akasha-os-v0.33.1) (2026-08-18)


### Performance Improvements

* **aura:** lazy-load rows/grids incrementally + on-device page cache ([c9b17ac](https://github.com/jeremiejt38/akasha-os/commit/c9b17ac7ceea30e663b461d2ccfa028141800208))

## [0.33.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.32.1...akasha-os-v0.33.0) (2026-08-18)


### Features

* **remote:** add keymap for Amazon Fire TV Bluetooth remote ([409ba24](https://github.com/jeremiejt38/akasha-os/commit/409ba24f2f62ea15e94b7b6828246004b752e742))

## [0.32.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.32.0...akasha-os-v0.32.1) (2026-08-18)


### Bug Fixes

* **aura:** sidebar onright pointed to a non-focusable label, breaking navigation ([4f64920](https://github.com/jeremiejt38/akasha-os/commit/4f649201aeffa7c1a5efda56fae6c657681855e8))

## [0.32.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.31.3...akasha-os-v0.32.0) (2026-08-18)


### Features

* **aura:** retractable left sidebar for Divertissement library navigation ([538ff74](https://github.com/jeremiejt38/akasha-os/commit/538ff742b8b475919c58db99962d66eac7343343))

## [0.31.3](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.31.2...akasha-os-v0.31.3) (2026-08-18)


### Bug Fixes

* **aura:** connector_client.section_items() forward genre/search + URL-encode sort ([d655ab8](https://github.com/jeremiejt38/akasha-os/commit/d655ab839c3ba6e47201e92b30f7298b08530b54))

## [0.31.2](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.31.1...akasha-os-v0.31.2) (2026-08-18)


### Bug Fixes

* **aura:** section_genres reads title field, not tag (Plex API response shape) ([d4ab825](https://github.com/jeremiejt38/akasha-os/commit/d4ab8257e5282cf775a26cd630d6b4b314a1b55a))

## [0.31.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.31.0...akasha-os-v0.31.1) (2026-08-18)


### Bug Fixes

* **aura:** widen top-bar buttons (255px) to stop truncating Recommande/Bibliotheque/Categories/Parametres ([5e40e5e](https://github.com/jeremiejt38/akasha-os/commit/5e40e5e9c342ceab2ea6f07cb1291f0f77d93635))

## [0.31.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.30.0...akasha-os-v0.31.0) (2026-08-18)


### Features

* **aura:** add Categories view (genre browser) matching Plex UI reference ([a6546e4](https://github.com/jeremiejt38/akasha-os/commit/a6546e4f33c39169ecd0ad8f540052f8f5cf6f70))
* **aura:** show 2-line item labels (title + S/E or year) matching Plex UI reference ([c2f8a9e](https://github.com/jeremiejt38/akasha-os/commit/c2f8a9e8e3ffd291f8502cddadbff39c901e4448))

## [0.30.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.29.0...akasha-os-v0.30.0) (2026-08-18)


### Features

* **aura:** wire Bibliotheque view (search/sort/genre) to the connector with Plex fallback ([d825a9b](https://github.com/jeremiejt38/akasha-os/commit/d825a9b8e0faecb3eacba079ff69698e9687da0f))

## [0.29.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.28.1...akasha-os-v0.29.0) (2026-08-18)


### Features

* **aura:** add Sorties recentes row to Pour vous view ([e1264eb](https://github.com/jeremiejt38/akasha-os/commit/e1264eb48705a79e8a984862beae8c53838ca088))

## [0.28.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.28.0...akasha-os-v0.28.1) (2026-08-18)


### Bug Fixes

* **aura:** shorten Recommandations top-bar button label to avoid text scroll ([5bc3cf5](https://github.com/jeremiejt38/akasha-os/commit/5bc3cf576b939e9681e436b3066bb0ecee4c84b0))

## [0.28.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.27.1...akasha-os-v0.28.0) (2026-08-18)


### Features

* **aura:** add Recommandations view (Continuer a regarder / Ajoutes recemment) ([b7cb64f](https://github.com/jeremiejt38/akasha-os/commit/b7cb64f7515628f383000b93faa3732d74ef7971))

## [0.27.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.27.0...akasha-os-v0.27.1) (2026-08-18)


### Bug Fixes

* **aura:** set explicit User-Agent on connector requests (Cloudflare 403) ([b659d83](https://github.com/jeremiejt38/akasha-os/commit/b659d835971c2ff5b04cf2ef035ec033b5ad8d07))

## [0.27.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.26.1...akasha-os-v0.27.0) (2026-08-18)


### Features

* **aura:** add connector settings + section_items/genres/children client methods ([c3821fd](https://github.com/jeremiejt38/akasha-os/commit/c3821fd55bc0f75d2a3efcac084721b6abc98383))
* **aura:** add connector_client.image_url() using the connector's image proxy ([c1a4d93](https://github.com/jeremiejt38/akasha-os/commit/c1a4d935db2ed2437e0a0aebac3a2de46367445f))
* **aura:** add connector_client.py for akasha-os-connector integration ([e3375cd](https://github.com/jeremiejt38/akasha-os/commit/e3375cdb77b6ee0da1a7510afd0d12425f24970f))
* **aura:** wire connector as primary Divertissement data source with Plex fallback ([0ed836a](https://github.com/jeremiejt38/akasha-os/commit/0ed836ab7e06c9f63f8b7ce6ebdeec7c2225390e))

## [0.26.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.26.0...akasha-os-v0.26.1) (2026-08-18)


### Bug Fixes

* **aura:** center sub-tab button labels to avoid overflow clipping ([c49c6ad](https://github.com/jeremiejt38/akasha-os/commit/c49c6adb6b0545651fb1fc56f51692c9b617b406))

## [0.26.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.25.0...akasha-os-v0.26.0) (2026-08-18)


### Features

* **aura:** icon tabs, per-library sub-tabs, Steam/Sunshine game libraries ([a6b17f7](https://github.com/jeremiejt38/akasha-os/commit/a6b17f774d4b671f365b7b14b52e71a6d1f50076))

## [0.25.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.24.1...akasha-os-v0.25.0) (2026-08-18)


### Features

* **aura:** add poster tiles and horizontal rows to Divertissement tab ([d1a7f63](https://github.com/jeremiejt38/akasha-os/commit/d1a7f632e399bb95640db456fc97f9f0859e7d43))

## [0.24.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.24.0...akasha-os-v0.24.1) (2026-08-18)


### Bug Fixes

* **aura:** exclude inputstreamhelper dependency from App inventory ([40ea1dd](https://github.com/jeremiejt38/akasha-os/commit/40ea1dd45f3a6b66e8f5b95cacda192cee8a6cd0))

## [0.24.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.23.3...akasha-os-v0.24.0) (2026-08-18)


### Features

* **aura:** add Akasha Store to install curated addons ([344bd3a](https://github.com/jeremiejt38/akasha-os/commit/344bd3a35c8349b415503ec894735099a58cdeab))

## [0.23.3](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.23.2...akasha-os-v0.23.3) (2026-08-18)


### Bug Fixes

* **aura:** use the correct 'thumbnail' JSON-RPC field for addon icons ([ecc7483](https://github.com/jeremiejt38/akasha-os/commit/ecc7483cd6811604f3577089fd3a9f5e086af5fd))

## [0.23.2](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.23.1...akasha-os-v0.23.2) (2026-08-18)


### Bug Fixes

* **aura:** repair App inventory JSON-RPC request and filter system addons ([54905da](https://github.com/jeremiejt38/akasha-os/commit/54905dabe948e09e947a9407e8e9409bde320ce5))

## [0.23.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.23.0...akasha-os-v0.23.1) (2026-08-18)


### Bug Fixes

* **aura:** wire tab bar Down navigation to Games/App tiles ([1ff9d9a](https://github.com/jeremiejt38/akasha-os/commit/1ff9d9ade7ba0ce3cfa2b633c271fb9a99d15e50))

## [0.23.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.22.1...akasha-os-v0.23.0) (2026-08-18)


### Features

* **aura:** add App tab with pinned tiles and full addon inventory ([f69507d](https://github.com/jeremiejt38/akasha-os/commit/f69507d859351c085d92d19594cb8d479b3576a1))

## [0.22.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.22.0...akasha-os-v0.22.1) (2026-08-18)


### Bug Fixes

* **aura:** install games.DATA.xml into addon resources/data ([e87b07c](https://github.com/jeremiejt38/akasha-os/commit/e87b07c54ce1fc2e74e542d6de68c0e96a01fec7))

## [0.22.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.21.1...akasha-os-v0.22.0) (2026-08-18)


### Features

* **aura:** add Settings button and Games tiles from shortcuts ([0cf4436](https://github.com/jeremiejt38/akasha-os/commit/0cf4436871d40f612975a76b6f6c3625bf5039d9))

## [0.21.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.21.0...akasha-os-v0.21.1) (2026-08-18)


### Bug Fixes

* **aura:** allow navigation from list to toolbar in library view ([966ced0](https://github.com/jeremiejt38/akasha-os/commit/966ced0855df6ec5b1252f329a9c73999e0fd5f9))

## [0.21.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.20.1...akasha-os-v0.21.0) (2026-08-17)


### Features

* **aura:** add full library view with search, sort and genre filter ([d74e0ff](https://github.com/jeremiejt38/akasha-os/commit/d74e0ffc2c72dfbb72385446c2f1fd2324474eba))

## [0.20.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.20.0...akasha-os-v0.20.1) (2026-08-17)


### Bug Fixes

* **ambient:** remove pre-v0.20.0 default videos without a manifest ([424d212](https://github.com/jeremiejt38/akasha-os/commit/424d212e319fada761fe9867d312405a7a727042))

## [0.20.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.19.0...akasha-os-v0.20.0) (2026-08-17)


### Features

* **settings:** expose all Mode Ambiant settings in Akasha Settings ([e38456c](https://github.com/jeremiejt38/akasha-os/commit/e38456c8157014b108cbe78c61d50f65f84eb187))


### Bug Fixes

* **ambient:** default to a curated landscape photo pack instead of videos ([d21ab3d](https://github.com/jeremiejt38/akasha-os/commit/d21ab3dcb76c136a37a304aef5d76d0299e522c0))

## [0.19.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.18.1...akasha-os-v0.19.0) (2026-08-17)


### Features

* **aura:** load Plex entertainment rows via direct API ([eefd18f](https://github.com/jeremiejt38/akasha-os/commit/eefd18fbca6589267102804db6f061b3cdac469f))

## [0.18.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.18.0...akasha-os-v0.18.1) (2026-08-17)


### Bug Fixes

* **aura:** remove radiobutton/texturenofocus artifacts from tab bar ([5f81fc4](https://github.com/jeremiejt38/akasha-os/commit/5f81fc421529a799bb2450d3a224ff2df807c51a))

## [0.18.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.17.0...akasha-os-v0.18.0) (2026-08-17)


### Features

* add Akasha Aura home screen (milestone 1: navigable shell) ([e1735f9](https://github.com/jeremiejt38/akasha-os/commit/e1735f93297cb237eb25b6520b00077e5ae8fcd0))

## [0.17.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.16.0...akasha-os-v0.17.0) (2026-08-17)


### Features

* **ambient:** transcode default landscape pack to H.264 and fix fullscreen playback ([8eb9718](https://github.com/jeremiejt38/akasha-os/commit/8eb971846b11ed02d49281d2a21d6e248229d29b))

## [0.16.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.15.0...akasha-os-v0.16.0) (2026-08-16)


### Features

* **ambient:** switch to static-camera looping landscape videos from Commons ([7129cc8](https://github.com/jeremiejt38/akasha-os/commit/7129cc8092f600e737d245b88f2450bf8d9afa1c))

## [0.15.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.14.4...akasha-os-v0.15.0) (2026-08-16)


### Features

* **ambient:** switch default pack to Wikimedia Commons landscape videos ([bd3d74e](https://github.com/jeremiejt38/akasha-os/commit/bd3d74e493a4db4c0832a01d8c7a9c8340762710))

## [0.14.4](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.14.3...akasha-os-v0.14.4) (2026-08-16)


### Bug Fixes

* **ambient:** switch video mode to fullscreen with isPlaying monitor ([0fdce74](https://github.com/jeremiejt38/akasha-os/commit/0fdce7455f487ced151dd7cf82369b2467897259))

## [0.14.3](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.14.2...akasha-os-v0.14.3) (2026-08-16)


### Bug Fixes

* **ambient:** use WindowXML and hidden default control for video playback ([f8b6532](https://github.com/jeremiejt38/akasha-os/commit/f8b653221b685a3eb2c0ca5520ec612949540960))

## [0.14.2](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.14.1...akasha-os-v0.14.2) (2026-08-16)


### Bug Fixes

* **ambient:** move videowindow to top of render stack and bind after visibility ([c6f123e](https://github.com/jeremiejt38/akasha-os/commit/c6f123ec7ece20502ac37a2d4c71e306167b8c34))

## [0.14.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.14.0...akasha-os-v0.14.1) (2026-08-16)


### Bug Fixes

* **ambient:** close busydialog before starting windowed video playback ([7c47992](https://github.com/jeremiejt38/akasha-os/commit/7c4799285503741ff3c4a1bb2dc1c0d4dfd67173))
* **ambient:** loop ambient videos and build proper playlist items ([0aa5937](https://github.com/jeremiejt38/akasha-os/commit/0aa593752bcb987f5a3c9238ed2d9bc1c0d1469c))
* **ambient:** make ambient window background transparent for windowed video ([d2dba82](https://github.com/jeremiejt38/akasha-os/commit/d2dba82c2e699923f885a5e1c613d3c90a0f11b8))

## [0.14.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.13.1...akasha-os-v0.14.0) (2026-08-16)


### Features

* **ambient:** download a default NASA EPIC Earth photo pack at install ([02cea6b](https://github.com/jeremiejt38/akasha-os/commit/02cea6b18b09a7057b598301dcad61c4d844f057))
* **ambient:** support ambient video packs with xbmc Player + videowindow ([6cf841c](https://github.com/jeremiejt38/akasha-os/commit/6cf841c09022dd53640ee5f725c0521c126b12f0))

## [0.13.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.13.0...akasha-os-v0.13.1) (2026-08-16)


### Bug Fixes

* **guide:** wire up the AkashaGuidePreset property and Left/Right cycling ([6c5a249](https://github.com/jeremiejt38/akasha-os/commit/6c5a2491c228e0f3ec8e31743b72a0a50760adcc))

## [0.13.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.12.0...akasha-os-v0.13.0) (2026-08-16)


### Features

* **guide:** brand the custom Guide header with logo, title and Montserrat font ([2757796](https://github.com/jeremiejt38/akasha-os/commit/275779627c45de20e5ac01e214318d2fd7f974c8))

## [0.12.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.11.1...akasha-os-v0.12.0) (2026-08-15)


### Features

* **ambient:** add pure logic modules for Akasha Ambient (config, content, weather, energy) ([c3877c0](https://github.com/jeremiejt38/akasha-os/commit/c3877c0c1f8fd20d6ab7456d48fd7cc746cc195c))
* **ambient:** implement the Ambient Mode screensaver window and skin ([b5f0c0e](https://github.com/jeremiejt38/akasha-os/commit/b5f0c0e17e8e03dda330bdf3cc5d5d67100ad32b))
* **guide:** add manual "Mode Ambiant" activation entry ([b361e08](https://github.com/jeremiejt38/akasha-os/commit/b361e08098d4c14aa01765616b7e20d1a9b921f8))
* **install:** deploy screensaver.akasha.ambient and enable it once ([9cbb4af](https://github.com/jeremiejt38/akasha-os/commit/9cbb4af9f2325e32b85f1df27aecc074af899221))
* **settings:** add Mode Ambiant section to Akasha Settings ([5ad25d2](https://github.com/jeremiejt38/akasha-os/commit/5ad25d24527f4dcc798be6a691e405e728208856))

## [0.11.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.11.0...akasha-os-v0.11.1) (2026-08-15)


### Bug Fixes

* **guide:** rename "Redemarrer Kodi" to "Redemarrer Akasha" ([bb7a5c3](https://github.com/jeremiejt38/akasha-os/commit/bb7a5c31091573f8263ca98c2c27f914f690a681))
* **guide:** restore splash screen on restart/shutdown from Guide menu ([30701e4](https://github.com/jeremiejt38/akasha-os/commit/30701e452c478f4d4c957cb0e7df4bc35d890a1d))

## [0.11.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.16...akasha-os-v0.11.0) (2026-08-15)


### Features

* contrôle du volume à la manette et overlay système ([305b97e](https://github.com/jeremiejt38/akasha-os/commit/305b97e3ba02fcdfc46db9aee8624e9972f2336a))
* guide Akasha — logo centre avec espacements egaux ([dd81f62](https://github.com/jeremiejt38/akasha-os/commit/dd81f627f6115b1b26382a9ae506033fdcd6062d))
* guide Akasha — logo plus grand et collé à droite ([52d7faa](https://github.com/jeremiejt38/akasha-os/commit/52d7faa559d375862b31ede676fc1e1c26feee9d))
* guide Akasha — option Mise en veille (CEC standby + wake-on-input) ([edefa8e](https://github.com/jeremiejt38/akasha-os/commit/edefa8eb0154b0d99138e7c81f2c38efa318dbb1))
* guide Akasha — padding uniforme autour du titre ([7524f12](https://github.com/jeremiejt38/akasha-os/commit/7524f1249b86722d8a4b859ba02632b117d15e7a))
* guide Akasha — recentrage du titre et du logo ([371f304](https://github.com/jeremiejt38/akasha-os/commit/371f304be4a64869b6f09797bb6cd46e508c35a4))
* guide Akasha — réduction de l'espace à gauche du titre ([4d80c68](https://github.com/jeremiejt38/akasha-os/commit/4d80c68c4f575d5f60206eebfeb6c7c81bac3601))
* guide Akasha — titre Akasha OS rogne et colle au bord gauche ([088bf22](https://github.com/jeremiejt38/akasha-os/commit/088bf224905f6f38d106b603e06950d070371230))
* guide Akasha — titre centre avec padding uniforme ([93afaf2](https://github.com/jeremiejt38/akasha-os/commit/93afaf235d19fa09ea8ace16ea1e2aa833f8b7ae))
* guide Akasha — titre collé à gauche ([0b2ff7a](https://github.com/jeremiejt38/akasha-os/commit/0b2ff7a56e9e329aab65f5c994672fe7a63e18a5))
* guide Akasha — titre decale plus a gauche ([ffeceb2](https://github.com/jeremiejt38/akasha-os/commit/ffeceb2a7ab02abfca6ac4f692f499dfa5dce6d6))
* guide Akasha — titre splash Akasha OS noir et agrandi ([09b4c9d](https://github.com/jeremiejt38/akasha-os/commit/09b4c9d8b5c3bd36a54248c9a8ce4b2867f84851))
* guide Akasha — titre, logo et version dans le menu contextuel ([14f04f5](https://github.com/jeremiejt38/akasha-os/commit/14f04f5581ffaaa3ad2fd01c5d295f72186f4c7d))
* menu Guide global sur le bouton Guide manette ([433e18e](https://github.com/jeremiejt38/akasha-os/commit/433e18e5ec62a7772ce573e5ed2966f7359407dc))
* **skin:** utiliser Montserrat pour les menus contextuels natifs ([9fcea4e](https://github.com/jeremiejt38/akasha-os/commit/9fcea4e7948690c668a0bcbfaea343712afa0242))


### Bug Fixes

* guide Akasha — centrage vertical dans la zone visible du header ([16d2d54](https://github.com/jeremiejt38/akasha-os/commit/16d2d545c544ba6bda3ffb14ebf3d64d2b09b7d8))
* guide Akasha — layout equilibre titre + logo ([f1124de](https://github.com/jeremiejt38/akasha-os/commit/f1124deea8e9894c9708248f67d2de11d94c466a))
* guide Akasha — titre aligne a gauche sans marge centree ([954254f](https://github.com/jeremiejt38/akasha-os/commit/954254f0cff88fbfb41188d2a336a7136988c618))
* **release:** stop demoting feat commits to patch bumps pre-1.0 ([9f0805b](https://github.com/jeremiejt38/akasha-os/commit/9f0805b3d250547bbfcc674d14bec2901f2a2781))


### Reverts

* **skin:** annule le changement de font13, corrige la hauteur du menu contextuel ([ec4c605](https://github.com/jeremiejt38/akasha-os/commit/ec4c605258ae483ebd9aa6ac183ede6ceb2693d5))

## [0.10.16](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.15...akasha-os-v0.10.16) (2026-08-14)


### Bug Fixes

* **ui:** make A button close success and changelog dialogs ([aa73786](https://github.com/jeremiejt38/akasha-os/commit/aa737862ae05e942360513b7bf4f68cd98dddb76))

## [0.10.15](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.14...akasha-os-v0.10.15) (2026-08-14)


### Bug Fixes

* **splash:** pre-Kodi splash with audio and cleaner OTA dialogs ([256c3fc](https://github.com/jeremiejt38/akasha-os/commit/256c3fc29fd059e7470bc1e99cf00fd79e5c51c2))

## [0.10.14](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.13...akasha-os-v0.10.14) (2026-08-14)


### Bug Fixes

* **ui:** highlight the default update button in yesnocustom dialog ([4c112b4](https://github.com/jeremiejt38/akasha-os/commit/4c112b44a38be1d9c81e13962c231f96fbc2d000))

## [0.10.13](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.12...akasha-os-v0.10.13) (2026-08-14)


### Bug Fixes

* **ui:** use yesnocustom dialog for update prompts ([f339c72](https://github.com/jeremiejt38/akasha-os/commit/f339c72138c7ddd4a7c3497b760a28788f13f813))

## [0.10.12](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.11...akasha-os-v0.10.12) (2026-08-14)


### Bug Fixes

* **ui:** show version arrow in boot-time update dialog ([96da5bb](https://github.com/jeremiejt38/akasha-os/commit/96da5bb2f6f3a1d0592a70f81d7e8c8667bfad22))

## [0.10.11](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.10...akasha-os-v0.10.11) (2026-08-14)


### Bug Fixes

* **splash:** play intro video before update checks ([3086923](https://github.com/jeremiejt38/akasha-os/commit/3086923de823279f31af2eb6f788adad63de6c1a))

## [0.10.10](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.9...akasha-os-v0.10.10) (2026-08-14)


### Bug Fixes

* **ota:** increase update check timeout and add boot diagnostics ([1c79335](https://github.com/jeremiejt38/akasha-os/commit/1c7933539c2f4963d90a1b3b103db1386e2cf8cd))

## [0.10.9](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.8...akasha-os-v0.10.9) (2026-08-14)


### Bug Fixes

* **ui:** clearer update-available dialog title ([a52c2f6](https://github.com/jeremiejt38/akasha-os/commit/a52c2f66486e2ed53e624f3ef2eaaeef258f6890))

## [0.10.8](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.7...akasha-os-v0.10.8) (2026-08-14)


### Bug Fixes

* **install:** enable Akasha addons in Kodi database ([611a2d7](https://github.com/jeremiejt38/akasha-os/commit/611a2d7769b9c026976dda10dae33b424531b1e6))

## [0.10.7](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.6...akasha-os-v0.10.7) (2026-08-14)


### Bug Fixes

* **ota:** extend post-update reboot countdown to 5 seconds ([122c63e](https://github.com/jeremiejt38/akasha-os/commit/122c63ea3718bb4e55558bf6fb10763413b62ed9))

## [0.10.6](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.5...akasha-os-v0.10.6) (2026-08-14)


### Features

* **ota:** check for updates at boot and prompt the user ([d895945](https://github.com/jeremiejt38/akasha-os/commit/d89594544309d905682ab87268d0f484ae1270a7))

## [0.10.5](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.4...akasha-os-v0.10.5) (2026-08-14)


### Features

* **ui:** improve OTA update UX with reboot countdown and post-reboot dialogs ([043b076](https://github.com/jeremiejt38/akasha-os/commit/043b07641660dc7e59701a3473ec71a5e7d179f2))

## [0.10.4](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.3...akasha-os-v0.10.4) (2026-08-14)


### Bug Fixes

* **ui:** warn user not to power off during OTA update ([d1eb472](https://github.com/jeremiejt38/akasha-os/commit/d1eb4728cb90c88a95adb8d8f821115ec16b64f9))

## [0.10.3](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.2...akasha-os-v0.10.3) (2026-08-14)


### Features

* **ui:** add OTA marker to update dialogs and menu ([f18155a](https://github.com/jeremiejt38/akasha-os/commit/f18155a66a216fdf3f54f351bdef531a625cac6d))

## [0.10.2](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.1...akasha-os-v0.10.2) (2026-08-14)


### Bug Fixes

* **ci:** do not mark image build releases as "latest" ([97dd63d](https://github.com/jeremiejt38/akasha-os/commit/97dd63d98b89c0438e3fa953cc9aa8d6d06d979a))
* **install:** derive Akasha OS version from package.json ([97dd63d](https://github.com/jeremiejt38/akasha-os/commit/97dd63d98b89c0438e3fa953cc9aa8d6d06d979a))

## [0.10.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.10.0...akasha-os-v0.10.1) (2026-08-14)


### Bug Fixes

* **updater:** parse semver in release-please tags with package prefix ([219c321](https://github.com/jeremiejt38/akasha-os/commit/219c321e13a376c8a785a3af949570134ef5e4ca))

## [0.10.0](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.9.1...akasha-os-v0.10.0) (2026-08-14)


### Features

* **cec:** wake TV as early as possible during boot ([0caf478](https://github.com/jeremiejt38/akasha-os/commit/0caf478e302efb9f1a98ca13f59b151a35632efc))
* **skin:** Akasha OS branding on startup screen ([b7cf4c1](https://github.com/jeremiejt38/akasha-os/commit/b7cf4c1845a669c6902eab783ced32052003cdf7))
* **splash:** display branded shutdown/reboot splash with message ([b93da90](https://github.com/jeremiejt38/akasha-os/commit/b93da90b2c84eee23b82a49142173d1a315acdbd))
* **splash:** pre-convert shutdown/reboot images to raw framebuffer ([5455905](https://github.com/jeremiejt38/akasha-os/commit/54559059fe83de196b3f07a41dc9853f8b4f379e))
* **update:** full Akasha OS self-update system with LibreELEC/Kodi lock ([07898a0](https://github.com/jeremiejt38/akasha-os/commit/07898a0a026e9a7d2ae16b296c49ef10678db1e3))


### Bug Fixes

* **cec:** ensure TV CEC standby works during poweroff ([fee6d45](https://github.com/jeremiejt38/akasha-os/commit/fee6d455109f9e8600fb4329643e3933046af651))
* **splash:** show shutdown/reboot image before Kodi tears down ([2ba5aee](https://github.com/jeremiejt38/akasha-os/commit/2ba5aee464b35b0ef2a668d6227c91c79d566881))
* **wifi:** allow WiFi autoconnect when ethernet is unplugged ([d146896](https://github.com/jeremiejt38/akasha-os/commit/d146896b095e7011a5e9969affd77125f695aebb))
* **wifi:** resolve connectivity drops and conflicts ([2ddce09](https://github.com/jeremiejt38/akasha-os/commit/2ddce0926d022688e37d38f829ae59f7c6c5379f))


### Miscellaneous Chores

* force release 0.10.0 ([10a5627](https://github.com/jeremiejt38/akasha-os/commit/10a5627dcd422be84aa74aa706854d5157fe05d1))

## [0.9.1](https://github.com/jeremiejt38/akasha-os/compare/akasha-os-v0.9.0...akasha-os-v0.9.1) (2026-08-14)


### Features

* **addons:** add Akasha Settings panel ([9915902](https://github.com/jeremiejt38/akasha-os/commit/99159023f6767049401a1524e172e90574eab59e))
* **addons:** add Cloud Gaming launcher + guide watchdog ([e086a19](https://github.com/jeremiejt38/akasha-os/commit/e086a1945fa7cc08122a8e717122fb185e291224))
* **boot:** add config.txt, cmdline.txt, splash screen ([207b765](https://github.com/jeremiejt38/akasha-os/commit/207b7655f0785921bcf5fa823a8bcdab1871615f))
* **boot:** add splash intro video on Kodi startup ([a030444](https://github.com/jeremiejt38/akasha-os/commit/a03044427556ff2a05a980d8c99466ba20351216))
* **scripts:** add apply.sh installer ([55356ac](https://github.com/jeremiejt38/akasha-os/commit/55356ac82bceb2ab7a2f853e829ea2665e995f39))
* **skin:** add menu patches + logo Akasha ([ce10e3d](https://github.com/jeremiejt38/akasha-os/commit/ce10e3dc899857efeef3c65c01756a563ccf29c4))
* **skin:** move Akasha menu to first position, remove logo overlay ([3671417](https://github.com/jeremiejt38/akasha-os/commit/3671417125a6010b21c97a4535c62a4616401e9d))
* **system:** add CEC shutdown service + WiFi retry script ([fe4498c](https://github.com/jeremiejt38/akasha-os/commit/fe4498cb1fcdff863798cba4b1ba97fde3515d89))
* **system:** add WiFi watchdog auto-reconnect service ([eafd0a4](https://github.com/jeremiejt38/akasha-os/commit/eafd0a4002f2e7c66312ec1f4a2601015fea54bc))
* **wifi:** register a silent connman Agent to permanently kill the popup ([3dae846](https://github.com/jeremiejt38/akasha-os/commit/3dae846075df0a30c9ac4ca9479f22f4d2b1d1ef))


### Bug Fixes

* **boot:** replace deprecated autoexec.py with service addon ([6fa5a49](https://github.com/jeremiejt38/akasha-os/commit/6fa5a49ebeb00a7900acc83095269f65aa3c9bc9))
* **ci:** fix Build Akasha OS Image workflow (never passed since creation) ([a7f0f9c](https://github.com/jeremiejt38/akasha-os/commit/a7f0f9cc19203c89101a24effd6d3994a24bc8da))
* **ci:** fix partition offset parsing broken by the boot flag column ([8019b5a](https://github.com/jeremiejt38/akasha-os/commit/8019b5ac5c75461092369ddb3226c7f05c3d9e83))
* **systemd:** break ordering cycle that could delete kodi.service's start job ([26a672d](https://github.com/jeremiejt38/akasha-os/commit/26a672d0d9fe408e4cd202504b9fc26671f4f55e))
* **wifi:** order regdomain fix before iwd, not just connman ([d6b05bc](https://github.com/jeremiejt38/akasha-os/commit/d6b05bc53ee6405d2854ac4aa2f3908d1ff466e0))
* **wifi:** rewrite watchdog — never delete profiles, only ensure passphrase ([3b32392](https://github.com/jeremiejt38/akasha-os/commit/3b3239256a995d5add48a3a08cdcdf1bd075bf4d))
* **wifi:** set regulatory domain before connman to fix boot-time invalid-key failure ([c79de2c](https://github.com/jeremiejt38/akasha-os/commit/c79de2c6dc2da0a7affb0574c6ee0769b52bcfe2))
* **wifi:** speed up watchdog reconnection to prevent Kodi prompt ([fc7c04b](https://github.com/jeremiejt38/akasha-os/commit/fc7c04b001fce2244811ab9ae1a49481496ec327))

## Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
