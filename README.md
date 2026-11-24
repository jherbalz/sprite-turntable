# Sprite Turntable

**Turn a 3D model into a fake-3D sprite sheet. Free, MIT licensed, runs
entirely on your own machine.**

Asset stores sell this. This is the same job, free, with no account, no
subscription and no network calls.

Get the code: <https://github.com/jherbalz/sprite-turntable>

**Where this came from:** this is the same renderer that ships inside
Blaster Master, cleaned of the game-specific code and given to everybody.
The scale contract, the flat-albedo look and the angle grid are the ones
the game already uses, so a sheet made here drops straight into a project
that uses them.

---

## What it makes

Give it a model. It walks the camera around it and writes one flat PNG per
angle: 16, 32 or **64 angles**, your choice.

The frames are not photographs and they are not 3D. They are flat,
game-ready sprite frames that look like a 3D model rotating, which is how
a lot of 2D games do their "3D" characters. Your game turns the frames
around and it reads as a model spinning in a room.

The frames come out **flat** - pure colour, no baked-in lighting. Your game
lights them. That is the point: one light in your game, the same light on
every character, and no light baked twice.

## What you need

**Blender.** That's it. It is free:

- <https://www.blender.org/download/>

Nothing else. No Python packages to install, no model to download, no
sign-up, no key. The script uses only Blender's own Python.

## Quick start

### Windows

Double-click **sprite_turntable.bat**, or from a command prompt:

    sprite_turntable.bat --model hero.glb --out .\sheet --angles 64

The batch file finds Blender for you. If Blender is installed somewhere
unusual, set `BLENDER_EXE` to the full path of `blender.exe` first.

### Mac and Linux

    bash sprite_turntable.sh --model hero.glb --out ./sheet --angles 64

### Any way you like

    blender --background --factory-startup \
        --python sprite_turntable.py -- \
        --model hero.glb --out ./sheet --angles 64

### The first time

    --model   the file to shoot: .blend, .fbx, .glb or .gltf
    --out     the folder the PNG frames are written to
    --angles  how many angles around the model

    sprite_turntable.bat --model hero.glb --out .\sheet --angles 64

You get `sheet_a00.png`, `sheet_a01.png` and so on - one file per angle,
numbered in order around the model.

## The three numbers that make it work

This is the part people pay for, and it is the part that is easy to get
wrong by hand. A sprite sheet only works if every character in the game
stands on the same ground line and is the same size in the world.

    --px-per-m    pixels per metre. Default 307.
    --ground-px  pixels from the bottom of the frame to the model's feet.
                 Default 82.
    --res        frame size in pixels, square. Default 512.

The camera is orthographic, so the size of the model on screen is fixed by
`--px-per-m` and not by how far away the camera is. Every frame of every
sheet made with the same numbers lines up with every other one. Change
`--px-per-m` once for your whole game and everything stays consistent.

`--ground-px` is the ground line. A model whose feet are 82 px above the
bottom of the frame stands on the same floor as every other character, so
your game can drop them all onto one floor line.

## Presets

Three ready-made setups are in the `presets` folder:

    --preset turntable-16     16 angles, the quick look
    --preset turntable-32     32 angles, smooth turning
    --preset turntable-64     64 angles, the full turnaround

Anything you type on the command line wins over the preset, so this is
fine:

    sprite_turntable.bat --preset turntable-64 --res 1024

## All the options

| Option | What it does |
|---|---|
| `--model` | the model: `.blend`, `.fbx`, `.glb`, `.gltf` |
| `--out` | folder the PNG frames are written to |
| `--prefix` | name the frames start with (default `sheet`) |
| `--angles` | how many angles around the model (default 16) |
| `--res` | frame size in pixels, square (default 512) |
| `--px-per-m` | world scale: pixels per metre (default 307) |
| `--ground-px` | pixels from the bottom of the frame to the feet (default 82) |
| `--elev` | camera tilt in degrees (default 6) |
| `--anchor` | `floor` (feet on the ground line) or `center` |
| `--length` | rescale the model to this length in metres |
| `--action` | the animation to pose the rig with, or `all` for every animation in the model |
| `--frames` | frames of that animation, e.g. `1,8,16`, or `all` for the whole cycle |
| `--list-actions` | print the animations the model has, then stop |
| `--batch` | a JSON job list: one sheet per model and animation |
| `--fps` | frames per second written into the manifest (default 12) |
| `--manifest` | where the manifest is written (default: in the output folder) |
| `--compress` | rescale the action's keyframes into this many frames |
| `--in-place` | pin the rig's root so a walk cycle stays in frame |
| `--spin` | render a spin sheet of N frames instead of an angle sheet |
| `--spin-angle` | where the camera sits for a spin sheet, in degrees |
| `--spin-axis` | the axis a spin sheet turns on, `x` or `y` |
| `--preset` | a preset from the `presets` folder |

## Rigged models

If the model has a rig, you can shoot a pose instead of the rest pose:

    sprite_turntable.bat --model hero.glb --out .\sheet --angles 64 \
        --action Walk --frames 1,8,16

That writes one frame per angle per animation frame:
`sheet_a00_f01.png`, `sheet_a00_f08.png`, and so on - a walk cycle your
game can play back over the turning model.

Blender 4.4 and later use slotted actions, and this script binds the slot
as well as the action. If a rig comes out frozen in its rest pose, that is
the reason, and it is handled here.

## Which animation plays

This is the part that turns a spinning model into a character. A rigged
model carries its clips - walk, aim, fire - and each one can be shot as
its own sheet.

**Ask the model what it has:**

    sprite_turntable.bat --model hero.glb --list-actions

It prints every clip in the file, the frame range and how many bones it
drives:

    11_Sentinel_Rig_Walk   frames 0-24    bones 5
    11_Sentinel_Rig_Aim    frames 0-24    bones 1

**Shoot one clip:**

    sprite_turntable.bat --model hero.glb --out .\sheet --action Walk --frames all

`--frames all` takes the whole cycle, resampled into `--compress` frames
(8 by default). `--frames 1,8,16` takes the frames you name instead.

**Shoot every clip at once:**

    sprite_turntable.bat --model hero.glb --out .\sheet --action all --frames all

Each animation lands in its own folder:

    sheet\walk\sheet_a00_f00.png
    sheet\aim\sheet_a00_f00.png
    sheet\fire\sheet_a00_f00.png

One folder per character, one folder per animation inside it. That is the
layout a game reads: `walk`, `aim`, `fire`, `die`.

## Wiring it to Godot

The frames are a grid: one row per angle, each row is the animation
frames. `sprite_manifest.json` is written next to them and says so:

    {
      "angles": 64,
      "fps": 12,
      "actions": [
        { "name": "11_Sentinel_Rig_Walk", "folder": "walk",
          "angles": 64, "frames": 8,
          "frame_numbers": [0, 3, 6, 9, 12, 15, 18, 21],
          "pattern": "sheet_a%02d_f%02d.png" }
      ]
    }

In Godot, load the frames of one animation as an array of arrays: rows
are angles, and the inner array is the animation. Play the animation
frames for the row of the angle you are facing. Blending the two
nearest angles looks smooth, and at 64 angles the blend IS the true
rotation, so the turn never snaps.

## The player

Every run writes `sprite_viewer.html` next to the frames. Open it and the
sheet plays: the animation runs, the turntable turns, and you can pick
the animation, the angle and the speed. It is one HTML file - no
install, no server, works on any computer with a browser.

| What it does | |
|---|---|
| The dropdown | every animation in the sheet |
| The animation slider | step the animation frame by frame |
| The turntable slider | turn the model to any angle |
| SPIN | the model turns while the animation plays |
| The strip at the bottom | the animation frames of the current angle |

Space plays and pauses. Left and right step the animation. Up and down
turn the model.

## Shooting a whole cast

One JSON file, one command. Each job is a model and an animation:

    {
      "jobs": [
        { "name": "GUARDIAN", "model": "guards/guard.blend",
          "action": "Walk", "frames": "1:7:13:19", "angles": 64 },
        { "name": "GUARDIAN", "model": "guards/guard.blend",
          "action": "Fire", "frames": "1:5" }
      ]
    }

    sprite_turntable.bat --batch cast.json --out .\cast

Every job lands in `cast\GUARDIAN\walk\` and `cast\GUARDIAN\fire\`.

## What it does not do

- **It does not go online.** There is no network call anywhere in it.
- **It does not download anything.** No model weights, no textures.
- **It does not need an account.**
- **It does not touch your model.** It opens it, reads it, renders it and
  leaves it exactly where it was.
- **It does not bake lighting into your frames.**

## If something goes wrong

**The frames are empty.** The model was probably outside the frame. Lower
`--px-per-m` (a smaller number means more of the world fits) or set
`--length` to the size you want.

**The model is in the wrong place in the frame.** Use `--anchor center`
instead of `--anchor floor`.

**The rig came out as a T-pose or a blob.** Pass the action by the exact
name in the file (`--action Walk`), and make sure `--frames` names a frame
that is actually inside the action.

**Blender was not found.** Set `BLENDER_EXE` to the full path of
`blender.exe`.

**A white silhouette.** The model's texture was not found when the file was
opened. Keep the textures next to the model, or pack them into the
`.blend` before shooting it.

## What's in this repository

| file | what it is |
|---|---|
| `sprite_turntable.py` | the whole tool |
| `sprite_turntable_gui.ps1` | the Windows window: one button |
| `sprite_turntable_ui.py` | the same button inside Blender |
| `sprite_viewer.html` | the player that comes with every sheet |
| `sprite_turntable.bat` | double-click runner for Windows |
| `sprite_turntable.sh` | runner for Mac and Linux |
| `presets/` | ready-made setups for 16, 32 and 64 angles |
| `tests/` | the tests, run on every push |
| `LICENSE` | MIT |
| `THIRD-PARTY-NOTICES.md` | what it needs, and what it does not bundle |

## Licence

MIT. See `LICENSE`. Use it in commercial games, no obligation, no
attribution required - though if you want to say thanks, that is welcome.

## The story

I built this for my own game, then found out people pay real money for
tools like it. My sons are autistic, and one of my rules as their dad is
that anything I build has to be something a child - or anybody on the
spectrum - can understand and run without help. A paywall in front of a
tool a kid wants to use is not that.

So: free, one download, one button, works the first time. Same as always.

- Jason T. Herbert
