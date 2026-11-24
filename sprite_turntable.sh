#!/usr/bin/env bash
# Sprite Turntable - makes a fake-3D sprite sheet from a 3D model.
#
# Usage:
#   ./sprite_turntable.sh --model model.glb --out ./sheet --angles 64
#
# Needs Blender (free). If Blender is somewhere unusual, set BLENDER_EXE
# to the full path of the blender binary before running this.

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BLENDER="${BLENDER_EXE:-}"
if [ -z "$BLENDER" ]; then
  for c in blender /Applications/Blender.app/Contents/MacOS/Blender /usr/local/bin/blender /usr/bin/blender; do
    if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then
      BLENDER="$c"
      break
    fi
  done
fi
if [ -z "$BLENDER" ]; then
  echo "Could not find Blender." >&2
  echo "Install it from https://www.blender.org/download/ and run this again," >&2
  echo "or set BLENDER_EXE to the full path of the blender binary." >&2
  exit 1
fi
echo "Using Blender: $BLENDER"
exec "$BLENDER" --background --factory-startup --python "$HERE/sprite_turntable.py" -- "$@"
