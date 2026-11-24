"""Sprite Turntable - the button.

This runs inside Blender. Open the 3D view, press N, click the Sprite tab,
pick your model, press MAKE SPRITE SHEET.

The sheet is rendered by a second, background copy of Blender, so your own
scene is never touched and Blender stays responsive while the frames are
made. The rendering is the same script the command line uses, so both ways
produce identical sheets.

ANIMATIONS
    A rigged model carries its clips: walk, aim, fire. Press READ
    ANIMATIONS and the ones in this scene are listed. Pick one and the
    sheet is shot with that animation playing - one frame per animation
    frame, for every angle. Pick ALL and every animation is shot, each
    into its own folder, which is the layout a game reads.
"""

import subprocess
import sys
import webbrowser
from pathlib import Path

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator, Panel

HERE = Path(__file__).resolve().parent
CORE = HERE / "sprite_turntable.py"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import sprite_turntable as core

ANGLES = [
    ("16", "16 angles", "quick look"),
    ("32", "32 angles", "smooth turning"),
    ("64", "64 angles", "full turnaround"),
]

RES = [
    ("256", "256 px", "fast"),
    ("512", "512 px", "standard"),
    ("1024", "1024 px", "big"),
]

_state = {"proc": None, "log": None, "out": None, "total": 0, "done": 0,
          "status": "", "actions": []}


def _count_angles(log_path):
    try:
        text = Path(log_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return text.count("  angle ")


def _action_items(self, context):
    """The dropdown of animations, read from the scene."""
    items = [("REST", "Rest pose (no animation)", "Shoot the model as it stands")]
    names = _state.get("actions") or []
    for i, a in enumerate(names):
        if a.get("bones", 0) > 0:
            items.append(("ACT_%d" % i, a["name"],
                          "%d frames" % a.get("frames", 0)))
    if len(items) > 2:
        items.append(("ALL", "ALL animations",
                      "Shoot every animation the model has"))
    return items


def _selected_action(identifier):
    """The action name for a dropdown entry."""
    names = _state.get("actions") or []
    if identifier == "ALL":
        return "all"
    if identifier.startswith("ACT_"):
        try:
            idx = int(identifier[4:])
        except ValueError:
            return ""
        if 0 <= idx < len(names):
            return names[idx]["name"]
    return ""


class SPRITE_OT_scan_actions(Operator):
    bl_idname = "sprite_turntable.scan_actions"
    bl_label = "Read the animations"
    bl_description = "List the animations that are in this scene"

    def execute(self, context):
        names = core.action_info()
        _state["actions"] = names
        rigs = [n for n in names if n.get("bones", 0) > 0]
        if rigs:
            self.report({"INFO"}, "%d animation(s) found." % len(rigs))
        else:
            self.report({"WARNING"},
                        "No animations in this scene. Import a rigged model first.")
        return {"FINISHED"}


class SPRITE_OT_make(Operator):
    bl_idname = "sprite_turntable.make"
    bl_label = "Make Sprite Sheet"
    bl_description = "Render the sprite sheet in a background Blender"
    bl_options = {"REGISTER"}

    model: StringProperty(
        name="Model",
        subtype="FILE_PATH",
        default="",
        description="The 3D model to shoot: .blend, .fbx, .glb or .gltf",
    )
    out_dir: StringProperty(
        name="Save to",
        subtype="DIR_PATH",
        default="",
        description="Where the PNG frames are written",
    )
    angles: EnumProperty(name="Angles", items=ANGLES, default="64")
    res: EnumProperty(name="Frame size", items=RES, default="512")
    action: EnumProperty(name="Animation", items=_action_items, default="REST")
    frames: StringProperty(
        name="Frames",
        default="all",
        description="Frames of the animation to shoot: all, or 1,8,16",
    )
    prefix: StringProperty(name="File name", default="sheet")

    def invoke(self, context, event):
        return self.invoke_props_dialog(width=560)

    def execute(self, context):
        model = Path(self.model).expanduser()
        if not model.is_file():
            self.report({"ERROR"}, "Pick a model file first.")
            return {"CANCELLED"}
        if self.out_dir.strip():
            out = Path(self.out_dir).expanduser()
        else:
            out = model.parent / "sprite_sheet"
        out.mkdir(parents=True, exist_ok=True)
        log = out / "sprite_turntable.log"
        action = _selected_action(self.action)
        frames = (self.frames or "all").strip() or "all"
        cmd = [
            bpy.app.binary_path,
            "--background",
            "--factory-startup",
            "--python",
            str(CORE),
            "--",
            "--model",
            str(model),
            "--out",
            str(out),
            "--angles",
            self.angles,
            "--res",
            self.res,
            "--prefix",
            self.prefix or "sheet",
        ]
        if action:
            cmd += ["--action", action, "--frames", frames]
        handle = open(log, "w", encoding="utf-8")
        _state["proc"] = subprocess.Popen(
            cmd, stdout=handle, stderr=subprocess.STDOUT, cwd=str(HERE))
        _state["log"] = str(log)
        _state["out"] = str(out)
        _state["total"] = int(self.angles)
        _state["done"] = 0
        _state["status"] = "Rendering..."
        try:
            context.window_manager.modal_handler_add(self)
        except Exception:
            pass
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        proc = _state.get("proc")
        if proc is None:
            return {"CANCELLED"}
        if proc.poll() is None:
            _state["done"] = _count_angles(_state["log"])
            return {"PASS_THROUGH"}
        code = proc.returncode
        _state["proc"] = None
        if code == 0:
            _state["status"] = "Done. " + str(_state["done"]) + " frames."
            self.report({"INFO"}, "Sprite sheet done: " + str(_state["out"]))
        else:
            _state["status"] = "Failed. The log is in " + str(_state["log"])
            self.report({"ERROR"}, "The render failed. See " + str(_state["log"]))
        return {"FINISHED"}

    def cancel(self, context):
        proc = _state.get("proc")
        if proc is not None and proc.poll() is None:
            proc.terminate()
        _state["proc"] = None
        return None


class SPRITE_OT_view(Operator):
    bl_idname = "sprite_turntable.view"
    bl_label = "Play the sheet"
    bl_description = "Open the player that comes with the frames"

    def execute(self, context):
        out = _state.get("out")
        viewer = (Path(out) / "sprite_viewer.html") if out else None
        if viewer is None or not viewer.is_file():
            self.report({"WARNING"}, "Make the sheet first.")
            return {"CANCELLED"}
        webbrowser.open(viewer.as_uri())
        return {"FINISHED"}


class SPRITE_OT_open(Operator):
    bl_idname = "sprite_turntable.open_folder"
    bl_label = "Open the folder"
    bl_description = "Open the folder with the finished frames"

    def execute(self, context):
        out = _state.get("out")
        if not out:
            self.report({"WARNING"}, "Nothing made yet.")
            return {"CANCELLED"}
        bpy.ops.wm.path_open(filepath=out)
        return {"FINISHED"}


class SPRITE_PT_turntable(Panel):
    bl_idname = "SPRITE_PT_turntable"
    bl_label = "Sprite Turntable"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sprite"

    def draw(self, context):
        layout = self.layout
        op = bpy.ops.sprite_turntable.make
        layout.label(text="Turn a 3D model into a flat sprite sheet")
        layout.prop(op, "model", text="Model")
        layout.prop(op, "out_dir", text="Save to")
        layout.prop(op, "angles")
        layout.prop(op, "res")
        layout.prop(op, "action")
        layout.prop(op, "frames")
        layout.prop(op, "prefix")
        total = _state.get("total") or 0
        done = _state.get("done") or 0
        if _state.get("proc") is not None:
            factor = (float(done) / total) if total else 0.0
            layout.progress(factor=factor, text="angle %d of %d" % (done, total))
        elif _state.get("status"):
            layout.label(text=_state["status"])
        layout.separator()
        layout.operator("sprite_turntable.scan_actions", icon="FILE_REFRESH")
        layout.operator("sprite_turntable.make", icon="RENDER_ANIM")
        layout.operator("sprite_turntable.view", icon="PLAY")
        layout.operator("sprite_turntable.open_folder", icon="FILE_FOLDER")


CLASSES = (SPRITE_OT_scan_actions, SPRITE_OT_make, SPRITE_OT_view,
           SPRITE_OT_open, SPRITE_PT_turntable)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


def _popup():
    try:
        bpy.ops.sprite_turntable.make("INVOKE_DEFAULT")
    except Exception:
        pass
    return None


if __name__ == "__main__":
    register()
    bpy.app.timers.register(_popup, first_interval=1.0)
else:
    register()
