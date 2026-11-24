# Changelog

All notable changes to this project are recorded here.

# Changelog

All notable changes to this project are recorded here.

## [1.1.0] - 2026-11-23

The animations, the player and the cast.

### Added

- `--list-actions` prints the animations a model carries, with the frame
  range and the number of bones each one drives.
- `--action all` shoots every animation in the model, each into its own
  folder (`walk`, `aim`, `fire`), the layout a game reads.
- `--frames all` takes the whole cycle, resampled into `--compress` frames.
- `--batch` shoots a whole cast from a JSON job list, one folder per
  character and one per animation inside it.
- `--fps` and `--manifest`: every run writes `sprite_manifest.json`, which
  says how the frames are laid out, so a game can wire them up.
- `sprite_viewer.html`, the player that comes with every sheet: the
  animation plays, the turntable turns, and the animation, the angle and
  the speed are all under your hand.
- The Windows window now lists the animations in the model you picked and
  lets you shoot one or all of them, and opens the player when it is done.
- The Blender panel reads the animations in your scene and shoots the one
  you pick.

### Fixed

- **A rig that carried its clips as NLA tracks rendered the same pose on
  every frame.** The tracks are now muted before the pose is set by hand,
  so an animation really is in the sheet.
- The size of a model is now measured on the rest pose, before any
  animation is applied, so every animation of one model shares the same
  world scale and the same ground line.

### Licence

MIT.

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
