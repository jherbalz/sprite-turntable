# Changelog

All notable changes to this project are recorded here.

## [1.0.0] - 2026-11-23

The first public release.

### Added

- `--angles` from 1 to any number, with presets for 16, 32 and 64.
- The scale contract: `--px-per-m` and `--ground-px`, so every sheet made
  with the same numbers lines up in a game.
- Flat-albedo rendering, so the game's own light does the shading.
- Rig support: `--action`, `--frames`, `--compress`, `--in-place`.
- Spin sheets with `--spin`, `--spin-angle` and `--spin-axis`.
- `--length` to rescale a model, and `--anchor floor|center`.
- A flat mid-grey fallback for models that arrive with no material, so the
  frames are never an empty black silhouette.
- `sprite_turntable.bat` (Windows) and `sprite_turntable.sh` (Mac, Linux),
  which find Blender for you.
- A test suite that runs on every push.

### Licence

MIT.
