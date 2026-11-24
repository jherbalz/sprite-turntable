"""The sprite turntable has to be release-ready, not just work.

These tests check the things that decide whether this can be handed to
anybody: it runs from the command line, it ships no weights and no network
calls, the licence is there, and the presets are honest.
"""

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / "sprite_turntable.py"
PRESETS = HERE / "presets"


class CommandLineTests(unittest.TestCase):
    """Somebody meets this tool by typing it in a terminal."""

    def test_the_help_works_without_blender(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0)
        self.assertIn("--angles", result.stdout)
        self.assertIn("--px-per-m", result.stdout)

    def test_it_says_so_when_it_is_run_outside_blender(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "x.glb"
            model.write_bytes(b"")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--model", str(model),
                 "--out", folder, "--angles", "64"],
                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Blender", result.stdout)

    def test_a_missing_model_is_a_clear_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--model", "does-not-exist.glb",
             "--out", "y"],
            capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no such model", (result.stdout + result.stderr).lower())


class PresetTests(unittest.TestCase):
    """The presets are what most people will actually use."""

    def test_the_three_presets_are_there(self):
        for name in ("turntable-16", "turntable-32", "turntable-64"):
            path = PRESETS / (name + ".json")
            with self.subTest(preset=name):
                self.assertTrue(path.is_file())

    def test_the_preset_says_the_angle_count(self):
        expected = {"turntable-16": 16, "turntable-32": 32, "turntable-64": 64}
        for name, angles in expected.items():
            data = json.loads((PRESETS / (name + ".json"))
                              .read_text(encoding="utf-8"))
            with self.subTest(preset=name):
                self.assertEqual(data["angles"], angles)
                self.assertEqual(data["res"], 512)
                self.assertEqual(data["px-per-m"], 307)
                self.assertEqual(data["ground-px"], 82)


class ReleaseTests(unittest.TestCase):
    """What ships, and what must not."""

    def test_no_weights_and_no_models_ship(self):
        for path in HERE.rglob("*"):
            if path.is_file():
                with self.subTest(path=path.name):
                    self.assertNotIn(path.suffix.lower(),
                                     (".safetensors", ".onnx", ".pt", ".pth",
                                      ".ckpt", ".bin", ".gguf", ".glb", ".gltf"))

    def test_it_imports_nothing_that_could_reach_the_network(self):
        """The only modules it may import are the standard library ones that
        do not talk to the outside, plus Blender's own two."""
        allowed = {"argparse", "json", "math", "os", "sys", "pathlib",
                   "bpy", "mathutils"}
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
        for name in sorted(imported):
            with self.subTest(module=name):
                self.assertIn(name, allowed,
                              "%s is imported and it is not on the allowed "
                              "list" % name)

    def test_it_has_no_url_that_could_be_fetched(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for banned in ("urlopen", "urlretrieve", "requests.get", "http.client",
                       "socket.socket"):
            with self.subTest(banned=banned):
                self.assertFalse(banned in source,
                                 "%s is in the script" % banned)

    def test_it_carries_no_game_specific_leftovers(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for banned in ("recolor_lib", "BM_FLIPPED", "RC_Tyre", "SOPHIA_RC",
                       "Malmars Local", "dread-gecko"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)

    def test_the_only_brand_name_is_the_copyright_holder(self):
        """The company name appears once, in the copyright line, and nowhere
        else - this tool is not a Malmars Local product."""
        source = SCRIPT.read_text(encoding="utf-8")
        for line in source.splitlines():
            if "Malmars" in line:
                with self.subTest(line=line.strip()):
                    self.assertIn("Herberto Malmars Toys LLC", line)

    def test_the_licence_is_mit_and_names_the_author(self):
        licence = (HERE / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", licence)
        self.assertIn("Jason T. Herbert", licence)
        self.assertIn("Herberto Malmars Toys LLC", licence)

    def test_the_notices_say_blender_is_not_bundled(self):
        notices = (HERE / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("Blender", notices)
        self.assertIn("not included here", notices)

    def test_the_readme_says_how_to_run_it(self):
        readme = (HERE / "README.md").read_text(encoding="utf-8")
        self.assertIn("--model", readme)
        self.assertIn("--angles", readme)
        self.assertIn("sprite_turntable.bat", readme)
        self.assertIn("MIT", readme)


if __name__ == "__main__":
    unittest.main()
