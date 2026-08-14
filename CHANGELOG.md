# Changelog

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
