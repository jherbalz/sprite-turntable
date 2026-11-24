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
VERSION = "1.0.0"

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
                   help="the animation action to pose the rig with")
    p.add_argument("--frames", "--frame", dest="frames", default="1",
                   help="frame or frames of that action, comma or colon "
                        "separated (default: 1)")
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
    src_start, src_end = act.frame_range[0], act.frame_range[1]
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


def set_pose(arm, action_name, frame):
    """Drive the rig to a named action at a given frame."""
    for act in list(bpy.data.actions):
        if action_name and action_name not in act.name:
            continue
        if SHEET_RANGE > 0.0:
            key = act.name
            if key not in SHEET_ACTION:
                SHEET_ACTION[key] = make_sheet_action(act, SHEET_RANGE)
            sheet, src_start, span = SHEET_ACTION[key]
            act = sheet
            frame = int(round((frame - src_start) / span * SHEET_RANGE))
        # The action is NEVER bound to the rig. On some of these rigs the
        # action's own evaluation collapses the skinned mesh to a point,
        # so the pose is driven from the curves by hand instead and the
        # scene stays on a frame where nothing is bound.
        arm.animation_data.action = None
        pose_from_curves(arm, act, frame)
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        return True
    return False


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

    load_model(model)
    ensure_materials()

    # --- drive the rig to a named action -----------------------------------
    act_name = args.action
    # frames can be a list: for a walk sheet you want several frames of the
    # same action, one per animation frame, for every angle
    frame_list = [int(x) for x in
                  args.frames.replace(",", ":").split(":") if x]
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if act_name:
        if not arms:
            raise SystemExit("no armature in " + str(model))
        if not set_pose(arms[0], act_name, frame_list[0]):
            raise SystemExit("action not found: " + act_name)
        print("posed:", act_name, "frames", frame_list)

    # A walk cycle that also moves the root would walk the model out of the
    # frame, so the root is pinned to where it stands on the first frame and
    # the legs do the moving.
    root_name = ""
    root_loc = None
    if args.in_place and arms and len(arms[0].data.bones):
        root_name = arms[0].data.bones[0].name
        set_pose(arms[0], act_name, frame_list[0])
        bpy.context.view_layer.update()
        root_loc = tuple(arms[0].pose.bones[root_name].location)

    # hidden reference meshes must not pollute the framing
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.hide_render:
            o.hide_viewport = True

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

    for i in range(angles):
        aim(2 * math.pi * i / angles)
        for f in frame_list:
            if act_name:
                set_pose(arms[0], act_name, f)
                if root_name and root_loc is not None:
                    arms[0].pose.bones[root_name].location = root_loc
                    bpy.context.view_layer.update()
            if len(frame_list) > 1:
                sc.render.filepath = str(outdir / ("%s_a%02d_f%02d" % (prefix, i, f)))
            else:
                sc.render.filepath = str(outdir / ("%s_a%02d" % (prefix, i)))
            bpy.ops.render.render(write_still=True)
        print("  angle %2d  frames %s" % (i, frame_list))

    print("SHEET DONE:", angles, "frames ->", outdir)
    print("engine:", engine, "| res:", res, "| px per metre:", px_per_m)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
