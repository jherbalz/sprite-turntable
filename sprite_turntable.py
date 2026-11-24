"""Sprite Turntable - make a fake-3D sprite sheet from a 3D model.

Turn a model into a sheet of flat "fake 3D" frames that a game can play
back like a 2D animation. One frame per angle, all of them at the SAME
world scale and standing on the SAME ground line, so the game can put
every character on screen at one sprite scale and they line up.

This is the tool that sits behind paywalls on asset stores. It is free,
MIT licensed, and it never sends anything anywhere.

THE CONTRACT WITH THE GAME
    Every sheet is rendered with the SAME world scale and the SAME ground
    anchor, so the game can put characters on screen at a single sprite
    scale and they line up physically. The default is 307 px per metre
    with the feet 82 px above the bottom of a 512x512 frame.

THE LOOK
    "Replacement lighting": the frame is rendered FLAT - pure albedo, no
    baked directional light - so the game's own PointLight2D and toon
    banding do the shading. Only the thruster nozzles keep their emission,
    because in that fiction they are light sources.

    Grit and the hand-drawn read belong in the game's shader, not baked
    into the frames.

WHAT IT NEEDS
    Blender (free, https://www.blender.org/download/). Nothing else. No
    Python packages to install, no model weights, no account, no network.
    The script only uses Blender's own bpy and mathutils.

HOW TO RUN IT
    Windows:   double-click sprite_turntable.bat
    Mac/Linux: bash sprite_turntable.sh
    Or call Blender yourself:

        blender --background --factory-startup \
            --python sprite_turntable.py -- \
            --model character.glb --out ./sheet --angles 64

Copyright (c) 2026 Jason T. Herbert (Herberto Malmars Toys LLC).
MIT licensed - see LICENSE.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

try:
    import bpy
    from mathutils import Matrix, Vector
    IN_BLENDER = True
except ImportError:  # running outside Blender: --help and the checks still work
    bpy = None
    Matrix = None
    Vector = None
    IN_BLENDER = False

HERE = Path(__file__).resolve().parent
VERSION = "1.1.0"

SHEET_RANGE = 8.0
PX_PER_M = 307.0
GROUND_PX = 82.0
RES = 512
ANGLES = 16
ELEV = 6.0          # degrees above horizontal
DIST = 4.0          # camera distance (ortho, so only used for clipping)

MODEL_SUFFIXES = (".blend", ".fbx", ".glb", ".gltf")


# --------------------------------------------------------------------------
# arguments
# --------------------------------------------------------------------------

PRESETABLE = ("angles", "res", "px_per_m", "ground_px", "elev")


def build_parser(defaults=None):
    d = defaults or {}

    def value(name, fallback):
        return d.get(name, fallback)

    p = argparse.ArgumentParser(
        prog="sprite_turntable",
        description="Make a fake-3D sprite sheet from a 3D model. "
                    "Runs inside Blender.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="example: blender --background --factory-startup "
               "--python sprite_turntable.py -- "
               "--model hero.glb --out ./sheet --angles 64")
    p.add_argument("--model", "--blend", dest="model", required=True,
                   help="the model: .blend, .fbx, .glb or .gltf")
    p.add_argument("--out", required=True,
                   help="folder the PNG frames are written to")
    p.add_argument("--prefix", default="sheet",
                   help="name the frame files start with (default: sheet)")
    p.add_argument("--angles", type=int, default=value("angles", ANGLES),
                   help="how many angles around the model (default: %(default)s)")
    p.add_argument("--res", type=int, default=value("res", RES),
                   help="frame size in pixels, square (default: %(default)s)")
    p.add_argument("--px-per-m", dest="px_per_m", type=float,
                   default=value("px_per_m", PX_PER_M),
                   help="world scale: pixels per metre (default: %(default)s)")
    p.add_argument("--ground-px", dest="ground_px", type=float,
                   default=value("ground_px", GROUND_PX),
                   help="pixels from the bottom of the frame to the model's "
                        "feet (default: %(default)s)")
    p.add_argument("--elev", type=float, default=value("elev", ELEV),
                   help="camera tilt in degrees (default: %(default)s)")
    p.add_argument("--anchor", choices=("floor", "center"), default="floor",
                   help="floor: the model stands on the ground line "
                        "(default). center: the model is centred in the frame")
    p.add_argument("--length", type=float, default=0.0,
                   help="rescale the model to this length in metres "
                        "(0 keeps the model's own size)")
    p.add_argument("--action", default="",
                   help="the animation action to pose the rig with. "
                        "'all' shoots every action the model has")
    p.add_argument("--frames", "--frame", dest="frames", default="1",
                   help="frame or frames of that action, comma or colon "
                        "separated, or 'all' for the whole cycle "
                        "(default: 1)")
    p.add_argument("--list-actions", dest="list_actions", action="store_true",
                   help="print the animations the model has, then stop")
    p.add_argument("--batch", default="",
                   help="a JSON job list: one sheet per model and action")
    p.add_argument("--fps", type=int, default=12,
                   help="frames per second recorded in the manifest "
                        "(default: %(default)s)")
    p.add_argument('--fit', action='store_true',
                   help='pull the camera back so the whole model fits '
                        'in the frame (a tall model is cut off otherwise)')
    p.add_argument('--manifest', default='',
                   help="where the manifest is written (default: "
                        "sprite_manifest.json in the output folder)")
    p.add_argument("--compress", type=float, default=8.0,
                   help="rescale the action's keyframes into this many "
                        "frames (default: %(default)s)")
    p.add_argument("--in-place", dest="in_place", action="store_true",
                   help="pin the rig's root so a walk cycle does not walk "
                        "the model out of frame")
    p.add_argument("--spin", type=int, default=0,
                   help="render a spin sheet of this many frames instead of "
                        "an angle sheet (the model turns, the camera stays)")
    p.add_argument("--spin-angle", dest="spin_angle", type=float, default=0.0,
                   help="where the camera sits for a spin sheet, in degrees")
    p.add_argument("--spin-axis", dest="spin_axis", choices=("x", "y"),
                   default="y", help="the axis a spin sheet turns on "
                                     "(default: %(default)s)")
    p.add_argument("--preset", default="",
                   help="a preset from the presets folder, for example "
                        "turntable-64")
    p.add_argument("--version", action="version",
                   version="sprite_turntable " + VERSION)
    return p


def load_preset(name):
    """A preset is a small JSON file of the same names as the switches."""
    if not name:
        return {}
    candidates = [Path(name)]
    if not Path(name).is_absolute():
        candidates.append(HERE / "presets" / name)
        candidates.append(HERE / "presets" / (name + ".json"))
    for path in candidates:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            out = {}
            for key, value in data.items():
                if key in PRESETABLE:
                    out[key] = value
            return out
    raise SystemExit("no such preset: " + name)


def script_args():
    """Blender puts everything after -- into the arguments."""
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return sys.argv[1:]


def parse_args():
    raw = script_args()
    parser = build_parser()
    args = parser.parse_args(raw)
    if args.preset:
        preset = load_preset(args.preset)
        if preset:
            args = build_parser(preset).parse_args(raw)
    return args


# --------------------------------------------------------------------------
# the render
# --------------------------------------------------------------------------

def ensure_materials():
    """A model with no material renders as a black silhouette, which is
    useless as a sprite.

    Plenty of game models arrive with no material at all - an STL turned
    into a GLB, or an export with placeholders. Those meshes are given a
    plain mid-grey albedo so the shape is readable. The game tints the
    sprite itself, so the colour here does not have to be the real one.
    """
    default = None

    def grey():
        nonlocal default
        if default is None:
            default = bpy.data.materials.new("SheetDefault")
            default.use_nodes = True
            bsdf = next((n for n in default.node_tree.nodes
                         if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is not None:
                bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)
                bsdf.inputs["Roughness"].default_value = 1.0
        return default

    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if not o.material_slots:
            o.data.materials.append(grey())
            continue
        for i, slot in enumerate(o.material_slots):
            if slot.material is None:
                o.data.materials[i] = grey()
    return default


def flatten_to_albedo():
    """Replace every material with flat emission of its own albedo.

    Emission is what the game receives; the game's light multiplies it.
    The albedo TEXTURE has to be kept - the Base Color input is white on a
    textured material, and reading the input value instead of the link
    throws the artwork away and leaves a white silhouette.
    """
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue

        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 1.0

        src = None
        links = bsdf.inputs["Base Color"].links
        if links:
            src = links[0].from_socket
        elinks = bsdf.inputs["Emission Color"].links
        if elinks and bsdf.inputs["Emission Strength"].default_value > 1.01:
            src = elinks[0].from_socket
            em.inputs["Strength"].default_value = bsdf.inputs["Emission Strength"].default_value
        if src is not None:
            nt.links.new(src, em.inputs["Color"])
        else:
            em.inputs["Color"].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])


def bind_action(arm, act):
    """Assign an action AND its slot.

    Blender 4.4+ uses SLOTTED actions: assigning animation_data.action
    without binding a slot leaves the rig in its rest pose and every bone
    reads zero. This is the whole reason a rig can look 'broken' when it
    is not.
    """
    arm.animation_data_create()
    arm.animation_data.action = act
    if hasattr(act, "slots") and len(act.slots):
        slot = next((s for s in act.slots if s.name_display == arm.name),
                    act.slots[0])
        try:
            arm.animation_data.action_slot = slot
        except Exception:
            pass


def action_fcurves(act):
    """Every f-curve of an action, slotted or not."""
    fcs = []
    if hasattr(act, "layers"):
        for layer in act.layers:
            for strip in layer.strips:
                for bag in (getattr(strip, "channelbags", None) or []):
                    fcs.extend(list(bag.fcurves))
    if not fcs and hasattr(act, "fcurves"):
        try:
            fcs = list(act.fcurves)
        except Exception:
            pass
    return fcs



def action_range(act):
    """The action's real frame range, measured off its keyframes.

    act.frame_range comes back empty on some slotted actions, so the
    range is read from the curves instead of trusting the property.
    """
    lo = hi = None
    for fc in action_fcurves(act):
        for kp in fc.keyframe_points:
            x = float(kp.co[0])
            if lo is None or x < lo:
                lo = x
            if hi is None or x > hi:
                hi = x
    if lo is None:
        return (0.0, 0.0)
    return (lo, hi)


def pose_from_curves(arm, act, frame):
    """Set the pose by hand from the action's curves.

    Some rigs leave the armature unposed on frames past a point, and a
    skinned mesh with an unposed rig collapses to a point: the sheet comes
    out empty. Driving the bones from the curves ourselves is slower but
    it is always right.

    Both rotation channel types are read: euler (XYZ) and quaternion.
    glTF/FBX rigs - Unreal-style 28-bone characters, for example - store
    quaternion rotations, and a sheet built from those with euler only
    comes out as a collapsed or frozen pose.
    """
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0.0, 0.0, 0.0)
    for fc in action_fcurves(act):
        dp = fc.data_path
        if not dp.startswith('pose.bones[') or '"' not in dp:
            continue
        # A bone LOCATION curve is an absolute position. The retro clips
        # key it to near zero, which drops the whole mesh onto the origin
        # and the sheet comes out empty. Only the rotations are used.
        if dp.endswith(".location") or dp.endswith(".scale"):
            continue
        try:
            name = dp.split('"')[1]
            idx = fc.array_index
        except Exception:
            continue
        pb = arm.pose.bones.get(name)
        if pb is None:
            continue
        if dp.endswith(".rotation_quaternion"):
            # fcurve order for a quaternion is w, x, y, z
            if idx > 3:
                continue
            pb.rotation_mode = 'QUATERNION'
            q = list(pb.rotation_quaternion)
            q[idx] = fc.evaluate(frame)
            pb.rotation_quaternion = q
            continue
        if idx > 2:
            continue
        pb.rotation_mode = 'XYZ'
        rot = list(pb.rotation_euler)
        rot[idx] = fc.evaluate(frame)
        pb.rotation_euler = rot


def make_sheet_action(act, new_range):
    """Copy an action with its keys compressed into a short range.

    These rigs only evaluate cleanly over the first handful of frames, so
    a 32 frame cycle is rescaled into 8 frames for the sheet. The game only
    ever needs the loop, not the original timing.
    """
    src_start, src_end = action_range(act)
    span = max(src_end - src_start, 0.001)
    new = act.copy()
    new.name = act.name + "_sheet"
    for fc in action_fcurves(new):
        for kp in fc.keyframe_points:
            kp.co[0] = (kp.co[0] - src_start) / span * new_range
        fc.update()
    try:
        new.frame_range = (0.0, float(new_range))
    except Exception:
        pass
    return new, src_start, span


SHEET_ACTION = {}


def quiet_rig(arm):
    """Stop anything else from driving the rig.

    A rig file can carry its clips as NLA tracks as well as an action.
    Any frame change re-poses the bones from those tracks and throws
    away a pose that was set by hand, so the tracks are muted first.
    Without this the sheet renders the same pose on every frame.
    """
    ad = arm.animation_data
    if ad is None:
        return
    ad.action = None
    for track in ad.nla_tracks:
        track.mute = True


def set_pose(arm, action_name, frame):
    """Drive the rig to a named action at a given frame."""
    acts = list(bpy.data.actions)
    # An exact name wins. A partial name is still accepted, because the
    # clips in a rig are often called Armature|Walk or Walk.001.
    pick = None
    for act in acts:
        if act.name == action_name:
            pick = act
            break
    if pick is None:
        for act in acts:
            if action_name and action_name in act.name:
                pick = act
                break
    if pick is None:
        return False
    act = pick
    if SHEET_RANGE > 0.0:
        key = act.name
        if key not in SHEET_ACTION:
            SHEET_ACTION[key] = make_sheet_action(act, SHEET_RANGE)
        sheet, src_start, span = SHEET_ACTION[key]
        act = sheet
        frame = int(round((frame - src_start) / span * SHEET_RANGE))
    # The action is NEVER bound to the rig. On some of these rigs the
    # action own evaluation collapses the skinned mesh to a point,
    # so the pose is driven from the curves by hand instead and the
    # scene stays on a frame where nothing is bound.
    bpy.context.scene.frame_set(1)
    quiet_rig(arm)
    pose_from_curves(arm, act, frame)
    bpy.context.view_layer.update()
    return True


def safe_name(text):
    """A name that is safe as a folder name on every system."""
    out = []
    for ch in str(text):
        out.append(ch if (ch.isalnum() or ch in '-_.') else '_')
    return "".join(out).strip("._") or "action"


def action_folder(act_name, arm):
    """The folder an action lands in: walk, aim, fire.

    Rig files name their clips after the rig, so 11_Sentinel_Rig_Walk
    becomes walk. That is the layout a game reads: one folder per
    animation, inside one folder per character.
    """
    name = str(act_name)
    if arm is not None:
        prefix = arm.name + "_"
        if name.startswith(prefix):
            name = name[len(prefix):]
        elif name.startswith(arm.name):
            name = name[len(arm.name):]
    return safe_name(name).lower()


def action_info():
    """Every action in the file: name, frame range, animated bones.

    This is what the window shows, so the person can pick the animation
    they actually want - walk, attack, whatever the model carries.
    """
    out = []
    for act in bpy.data.actions:
        fcs = action_fcurves(act)
        bones = sorted({fc.data_path.split(chr(34))[1] for fc in fcs
                        if fc.data_path.startswith('pose.bones[')
                        and chr(34) in fc.data_path})
        lo, hi = action_range(act)
        out.append({
            'name': act.name,
            'start': round(lo, 3),
            'end': round(hi, 3),
            'frames': int(round(hi - lo)) + 1,
            'bones': len(bones),
        })
    return out


def frames_for(name, args, found):
    """Which frames of an action are shot.

    all is the whole cycle, resampled into --compress frames so the
    sheet stays short. Anything else is the list that was asked for.
    """
    want = str(getattr(args, 'frames', '1') or '1').strip().lower()
    if want in ('all', '*'):
        info = None
        for a in found:
            if a['name'] == name:
                info = a
                break
        if info is None:
            return [1]
        lo = int(info['start'])
        hi = int(info['end'])
        count = max(1, int(round(float(args.compress))))
        span = max(hi - lo, 0)
        if count == 1 or span == 0:
            return [lo]
        picked = []
        for i in range(count):
            f = lo + int(round(i * span / float(count - 1)))
            if f not in picked:
                picked.append(f)
        return picked
    picked = []
    for x in want.replace(",", ":").split(":"):
        x = x.strip()
        if x:
            picked.append(int(x))
    return picked or [1]


def run_batch(args):
    """A JOB LIST: many models, one sheet each.

    The job file is JSON: a list of name, model, action and frames.
    Each job lands in out/name/action, which is the layout the Blaster
    Master game already reads, so a whole roster is one command.
    """
    path = Path(args.batch)
    if not path.is_file():
        raise SystemExit('no such job list: ' + str(path))
    data = json.loads(path.read_text(encoding='utf-8'))
    jobs = data.get('jobs') if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        raise SystemExit('the job list must be a list of jobs')
    outroot = Path(args.out)
    outroot.mkdir(parents=True, exist_ok=True)
    done = 0
    for job in jobs:
        if not isinstance(job, dict):
            continue
        name = job.get('name') or Path(job.get('model', 'model')).stem
        action = job.get('action', '')
        folder = outroot / safe_name(name) / (safe_name(action) if action else '')
        for key in ('model', 'action', 'frames', 'angles', 'res',
                    'px_per_m', 'ground_px', 'elev', 'compress',
                    'length', 'anchor', 'spin', 'spin_angle',
                    'spin_axis', 'fps', 'in_place'):
            if key in job:
                setattr(args, key, job[key])
        args.out = str(folder)
        args.prefix = job.get('prefix', safe_name(name).lower())
        args.action = action
        args.batch = ''
        print('BATCH JOB:', name, action, '->', folder, flush=True)
        render_sheet(args)
        done += 1
    print('BATCH DONE:', done, 'jobs ->', outroot)
    return 0


VIEWER_TEMPLATE = HERE / 'sprite_viewer.html'


def write_viewer(outdir, manifest):
    """Write the player next to the frames.

    The player is one HTML file. Open it and the sheet plays: the
    animation runs and the turntable turns, the way the game plays it.
    No install, no server - it works on any computer with a browser.
    """
    data = {
        'model': manifest.get('model', ''),
        'angles': manifest.get('angles', 0),
        'fps': manifest.get('fps', 12),
        'actions': manifest.get('actions', []),
    }
    try:
        html = VIEWER_TEMPLATE.read_text(encoding='utf-8')
    except OSError:
        print('no viewer template next to the script')
        return ''
    html = html.replace('/*__DATA__*/ null', json.dumps(data))
    out = Path(outdir) / 'sprite_viewer.html'
    out.write_text(html, encoding='utf-8')
    print('VIEWER WRITTEN:', out)
    return str(out)


def set_engine(scene):
    """EEVEE, whichever name this Blender gives it."""
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = name
            return name
        except TypeError:
            continue
    raise SystemExit("this Blender has no EEVEE engine")


def load_model(path):
    src = str(path).lower()
    # --factory-startup still gives the default Cube/Camera/Light, and an
    # import adds to that scene. The Cube is 2 m across at the origin, so it
    # doubles the measured height and ends up in the frame.
    if not src.endswith(".blend"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
    if src.endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=str(path))
    elif src.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True,
                                 automatic_bone_orientation=True)
    elif src.endswith(".glb") or src.endswith(".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
        # The importer parks a helper icosphere in 'glTF_not_exported'. It is
        # 2 m across, sits at the origin, and would dominate the framing.
        for o in list(bpy.data.objects):
            if any(c.name == "glTF_not_exported" for c in o.users_collection):
                bpy.data.objects.remove(o, do_unlink=True)
    else:
        raise SystemExit("unsupported model: " + str(path))


def main():
    # The switches are read first, so --help and --version work outside
    # Blender too - that is where somebody meets this tool for the first
    # time.
    args = parse_args()

    # The model is checked first, so the same clear error comes back
    # whether or not Blender is installed.
    model = Path(args.model)
    if not model.is_file():
        raise SystemExit("no such model: " + str(model))
    if model.suffix.lower() not in MODEL_SUFFIXES:
        raise SystemExit("unsupported model type: " + model.suffix +
                         " (use .blend, .fbx, .glb or .gltf)")

    if not IN_BLENDER:
        print("This script runs inside Blender.")
        print("blender --background --factory-startup "
              "--python sprite_turntable.py -- --model model.glb "
              "--out ./sheet --angles 64")
        return 1

    return render_sheet(args)


def render_sheet(args):
    """Render the sheet. args carries the switches.

    Split out of main() so the window UI and the command line use exactly
    the same engine. args only has to have the attributes on it.
    """
    model = Path(args.model)
    if not model.is_file():
        raise SystemExit("no such model: " + str(model))
    if model.suffix.lower() not in MODEL_SUFFIXES:
        raise SystemExit("unsupported model type: " + model.suffix +
                         " (use .blend, .fbx, .glb or .gltf)")
    # A JOB LIST shoots many models in one run. This is the shape the
    # Blaster Master build uses: a name, a model, an action, the frames.
    if getattr(args, 'batch', ''):
        return run_batch(args)

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix
    angles = max(int(args.angles), 1)
    res = int(args.res)
    px_per_m = float(args.px_per_m)
    ground_px = float(args.ground_px)
    elev = float(args.elev)
    global SHEET_RANGE
    SHEET_RANGE = float(args.compress)
    # the cached copies of the actions belong to the old range
    SHEET_ACTION.clear()

    load_model(model)
    ensure_materials()

    # hidden reference meshes must not pollute the framing
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.hide_render:
            o.hide_viewport = True

    # --- what animations does this model actually have? --------------------
    # The window lists these, so the person can pick the animation they
    # want - walk, attack, whatever the model carries.
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    found = action_info()
    if getattr(args, 'list_actions', False):
        print('ACTIONS_JSON:' + json.dumps(found))
        for a in found:
            print('  %-26s frames %-12s bones %d'
                  % (a['name'], '%g-%g' % (a['start'], a['end']),
                     a['bones']))
        print('ACTION LIST DONE:', len(found), 'actions ->', model.name)
        return 0
    if found:
        print('model has %d action(s): %s'
              % (len(found), ', '.join(a['name'] for a in found)))

    def roots():
        return [o for o in bpy.data.objects
                if o.type in ('MESH', 'ARMATURE', 'EMPTY') and o.parent is None]

    def measure():
        bpy.context.view_layer.update()
        pts = []
        for o in bpy.data.objects:
            if o.type == 'MESH' and not o.hide_render:
                pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        if not pts:
            raise SystemExit("nothing to render")
        mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        return mn, mx

    # --- scale to the target size (only the roots; children follow) --------
    # The size is measured on the REST pose, before any animation is
    # applied. Every action of a model then shares ONE world scale and ONE
    # ground line, which is the point of the contract: the game can put a
    # walking model and an attacking model on the same floor.
    target_len = float(args.length)
    if target_len > 0.0:
        mn, mx = measure()
        span = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
        s = target_len / span
        for o in roots():
            o.scale = (o.scale.x * s, o.scale.y * s, o.scale.z * s)
        print("scaled by %.5f -> length %.3f m" % (s, target_len))

    # --- anchor ------------------------------------------------------------
    # "floor" puts the lowest point on z = 0, like the character rigs.
    # "center" centres the model in the frame.
    anchor = args.anchor
    mn, mx = measure()
    if anchor == "floor":
        for o in roots():
            o.location.z -= mn.z
    bpy.context.view_layer.update()

    # --- does the whole model fit the frame? ------------------------------
    # The frame is res/px_per_m metres across, and the feet sit
    # ground_px above the bottom of it. A model taller than that is cut
    # off: the head goes missing. --fit pulls the camera back, which
    # changes px_per_m and NOT the size of the model, so the ground line
    # stays exactly where it was and the model keeps its real size.
    mn, mx = measure()
    height = mx.z - mn.z
    half = max(abs(mn.x), abs(mx.x), abs(mn.y), abs(mx.y))
    if anchor == "floor":
        visible_h = (res - ground_px) / px_per_m
    else:
        visible_h = res / px_per_m
    visible_w = res / px_per_m
    need = max(height / max(visible_h, 1e-6),
               (2.0 * half) / max(visible_w, 1e-6))
    if need > 1.001:
        if getattr(args, 'fit', False):
            px_per_m = px_per_m / need
            print('FIT: the model is %.3f m tall - px per metre lowered to %.2f'
                  % (height, px_per_m))
        else:
            print('WARNING: the model is %.3f m tall but the frame only '
                  'shows %.3f m. The head is cut off.' % (height, visible_h))
            print('WARNING: use --fit, or a smaller --px-per-m.')

    flatten_to_albedo()

    sc = bpy.context.scene
    engine = set_engine(sc)
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'

    # --- measure the model -------------------------------------------------
    bpy.context.view_layer.update()
    pts = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and not o.hide_render:
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = Vector((0.0, 0.0, (mn.z + mx.z) / 2.0))
    print("MODEL bbox min", tuple(round(v, 4) for v in mn),
          "max", tuple(round(v, 4) for v in mx))

    # --- camera: orthographic, fixed px per metre --------------------------
    cam_data = bpy.data.cameras.new("SheetCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = res / px_per_m          # metres across the frame
    cam = bpy.data.objects.new("SheetCam", cam_data)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam

    # frame centre: the point that lands in the middle of the frame.
    # ground_px is measured UP FROM THE BOTTOM of the frame, so:
    #   centre_z = ground_z + (res/2 - ground_px) / px_per_m
    frame_m = res / px_per_m
    z_centre = mn.z + ((res / 2.0) - ground_px) / px_per_m
    target = Vector((0.0, 0.0, z_centre))
    print("frame width %.3f m | ground z=%.4f | frame centre z=%.4f"
          % (frame_m, mn.z, z_centre))

    el = math.radians(elev)

    def aim(ang):
        """Put the camera on the given bearing and aim it at the frame centre."""
        dirv = Vector((math.sin(ang), -math.cos(ang), 0.0))
        loc = target + dirv * DIST + Vector((0.0, 0.0, math.tan(el) * DIST))
        # camera basis: +Z points AWAY from the subject (the camera looks -Z),
        # so the subject lands exactly in the middle of the frame
        zaxis = (loc - target).normalized()
        xaxis = Vector((0.0, 0.0, 1.0)).cross(zaxis)
        if xaxis.length < 1e-6:
            xaxis = Vector((1.0, 0.0, 0.0))
        xaxis.normalize()
        yaxis = zaxis.cross(xaxis).normalized()
        m = Matrix((xaxis, yaxis, zaxis)).transposed().to_4x4()
        cam.matrix_world = Matrix.Translation(loc) @ m
        bpy.context.view_layer.update()

    # A SPIN sheet: the camera stays put and the model turns about its own
    # axis.
    spin = int(args.spin)
    if spin > 0:
        aim(math.radians(float(args.spin_angle)))
        for f in range(spin):
            for o in roots():
                o.rotation_euler = (0.0, 0.0, 0.0)
                if args.spin_axis == "x":
                    o.rotation_euler[0] = 2.0 * math.pi * float(f) / float(spin)
                else:
                    o.rotation_euler[1] = 2.0 * math.pi * float(f) / float(spin)
            bpy.context.view_layer.update()
            sc.render.filepath = str(outdir / ("%s_spin%02d" % (prefix, f)))
            bpy.ops.render.render(write_still=True)
        print("SPIN DONE:", spin, "frames ->", outdir)
        return 0

    # --- which animations are we shooting? ---------------------------------
    act_name = args.action
    if act_name == 'all':
        # Only the clips that drive the rig. A rig file also carries mesh
        # actions (an eye effect, a shape key) that pose nothing.
        rig_acts = [a['name'] for a in found if a['bones'] > 0]
        if not rig_acts:
            raise SystemExit('no rig animations in ' + str(model))
        todo = rig_acts
    elif act_name:
        todo = [act_name]
    else:
        todo = ['']                 # the rest pose

    manifest = {
        'tool': 'sprite_turntable',
        'version': VERSION,
        'model': model.name,
        'angles': angles,
        'res': res,
        'px_per_m': px_per_m,
        'ground_px': ground_px,
        'fps': int(getattr(args, 'fps', 12) or 12),
        'prefix': prefix,
        'grid': 'one row per angle, each row is the animation frames',
        'actions': [],
    }
    total = 0
    for name in todo:
        folder = action_folder(name, arms[0] if arms else None)
        sub = outdir if len(todo) <= 1 else outdir / folder
        sub.mkdir(parents=True, exist_ok=True)
        frame_list = frames_for(name, args, found) if name else [1]
        root_name = ''
        root_loc = None
        if name:
            if not arms:
                raise SystemExit('no armature in ' + str(model))
            if not set_pose(arms[0], name, frame_list[0]):
                raise SystemExit('action not found: ' + name)
            print('posed:', name, 'frames', frame_list)
            # A walk cycle that also moves the root would walk the model
            # out of the frame, so the root is pinned to where it stands
            # on the first frame and the legs do the moving.
            if args.in_place and len(arms[0].data.bones):
                root_name = arms[0].data.bones[0].name
                bpy.context.view_layer.update()
                root_loc = tuple(arms[0].pose.bones[root_name].location)
        for i in range(angles):
            aim(2 * math.pi * i / angles)
            for f in frame_list:
                if name:
                    set_pose(arms[0], name, f)
                    if root_name and root_loc is not None:
                        arms[0].pose.bones[root_name].location = root_loc
                        bpy.context.view_layer.update()
                if len(frame_list) > 1:
                    sc.render.filepath = str(
                        sub / ('%s_a%02d_f%02d' % (prefix, i, f)))
                else:
                    sc.render.filepath = str(sub / ('%s_a%02d' % (prefix, i)))
                bpy.ops.render.render(write_still=True)
            print('  angle %2d  frames %s' % (i, frame_list))
        total += angles * len(frame_list)
        manifest['actions'].append({
            'name': name if name else 'rest',
            'folder': '' if len(todo) <= 1 else folder,
            'prefix': prefix,
            'angles': angles,
            'frames': len(frame_list),
            'frame_numbers': frame_list,
            'pattern': (('%s_a%%02d_f%%02d.png' % prefix)
                        if len(frame_list) > 1 else ('%s_a%%02d.png' % prefix)),
        })
        print('ACTION DONE:', name if name else 'rest pose', '->', sub)

    mpath = Path(args.manifest) if getattr(args, 'manifest', '') \
        else outdir / 'sprite_manifest.json'
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('MANIFEST:', mpath)
    write_viewer(outdir, manifest)

    print('SHEET DONE:', total, 'frames ->', outdir)
    print('engine:', engine, '| res:', res, '| px per metre:', px_per_m)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
