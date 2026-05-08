#!/usr/bin/env python3
"""
export_glb.py — headless Blender → optimized GLB exporter.

Runs Blender in `--background` mode, opens a `.blend` file, applies clean-up
(transforms, recompute normals, single shape per mesh), and exports a
Draco-compressed GLB. Optional Meshopt post-processing via gltf-transform.

Usage:
    python export_glb.py input.blend --output models/coin.glb
    python export_glb.py input.blend --output models/coin.glb --no-draco
    python export_glb.py *.blend --output-dir models/

Flags:
    --output PATH         single-output mode; one .blend in
    --output-dir DIR      batch mode; one .glb per .blend, named after the .blend
    --no-draco            skip Draco compression (default: ON, level 6)
    --meshopt             post-process with `gltf-transform meshopt`
    --collection NAME     export only objects in the given Blender collection
    --apply-transforms    apply location/rotation/scale before export (default: ON)
    --recalc-normals      Mesh → Normals → Recalculate Outside (default: ON)
    --blender PATH        path to Blender executable (default: auto-detect)
    --quiet               suppress Blender's stdout

Requires:
    Blender 4.0+ on PATH (or pass --blender). Tested with Blender 5.1.1.
    For --meshopt: `npm i -g @gltf-transform/cli`

Examples:
    # Compress one file
    python export_glb.py hero.blend --output dist/hero.glb

    # Batch export all .blends in a folder
    python export_glb.py assets/source/*.blend --output-dir dist/

    # Maximum compression (Draco + Meshopt)
    python export_glb.py hero.blend --output dist/hero.glb --meshopt
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from glob import glob
from pathlib import Path

# UTF-8 stdout on Windows so log glyphs don't crash cp1251.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Blender Python — runs INSIDE Blender via --python-text
# ─────────────────────────────────────────────────────────────────────────────

# Note: this is sent as a string to Blender's --python-text. Don't import any
# project-local modules here — only stdlib + bpy.
BLENDER_SCRIPT = r"""
import bpy
import sys

# Args from the host script come in as `argv` after a "--" sentinel.
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opts = {a.split("=", 1)[0].lstrip("-"): a.split("=", 1)[1] for a in argv if "=" in a}

output_path     = opts.get("output", "")
collection_name = opts.get("collection", "")
draco_enabled   = opts.get("draco", "1") == "1"
apply_transforms = opts.get("apply", "1") == "1"
recalc_normals  = opts.get("normals", "1") == "1"

if not output_path:
    print("[blender] ERROR: --output= not provided", file=sys.stderr)
    sys.exit(1)

# Filter to selected collection if given, else all mesh objects
if collection_name:
    coll = bpy.data.collections.get(collection_name)
    if not coll:
        print(f"[blender] ERROR: collection '{collection_name}' not found", file=sys.stderr)
        sys.exit(1)
    mesh_objects = [o for o in coll.objects if o.type == "MESH"]
else:
    mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]

if not mesh_objects:
    print("[blender] ERROR: no mesh objects found to export", file=sys.stderr)
    sys.exit(1)

print(f"[blender] Found {len(mesh_objects)} mesh object(s) to export")

# Apply transforms
if apply_transforms:
    bpy.ops.object.select_all(action="DESELECT")
    for o in mesh_objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print("[blender] Applied transforms")

# Recompute normals
if recalc_normals:
    for o in mesh_objects:
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    print("[blender] Recomputed normals")

# Select all targets, export
bpy.ops.object.select_all(action="DESELECT")
for o in mesh_objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objects[0]

export_kwargs = dict(
    filepath=output_path,
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_yup=True,
)
if draco_enabled:
    export_kwargs["export_draco_mesh_compression_enable"] = True
    export_kwargs["export_draco_mesh_compression_level"] = 6

try:
    bpy.ops.export_scene.gltf(**export_kwargs)
except Exception as e:
    print(f"[blender] Export failed with Draco: {e}; retrying without Draco", file=sys.stderr)
    export_kwargs["export_draco_mesh_compression_enable"] = False
    bpy.ops.export_scene.gltf(**export_kwargs)

import os
sz = os.path.getsize(output_path)
print(f"[blender] OK {output_path}  ({sz} bytes / {sz/1024:.1f} KB)")
"""


# ─────────────────────────────────────────────────────────────────────────────
# Host helpers
# ─────────────────────────────────────────────────────────────────────────────

def err(msg: str) -> None:
    print(f"[x] {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"[.] {msg}")


def ok(msg: str) -> None:
    print(f"[+] {msg}")


def find_blender(explicit: str | None) -> str:
    if explicit:
        if not Path(explicit).exists():
            err(f"--blender path does not exist: {explicit}")
            sys.exit(2)
        return explicit
    # Auto-detect
    candidate = shutil.which("blender")
    if candidate:
        return candidate
    # Common Windows install paths
    for guess in [
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/usr/bin/blender",
        "/snap/bin/blender",
    ]:
        if Path(guess).exists():
            return guess
    err("Blender executable not found. Pass --blender PATH.")
    sys.exit(2)


def run_meshopt(input_glb: Path) -> None:
    """Post-process a GLB through `gltf-transform meshopt`."""
    cli = shutil.which("gltf-transform")
    if not cli:
        err("`gltf-transform` not found on PATH. Skipping --meshopt. "
            "Install: npm i -g @gltf-transform/cli")
        return
    tmp = input_glb.with_suffix(".meshopt.tmp.glb")
    try:
        before = input_glb.stat().st_size
        subprocess.run([cli, "meshopt", str(input_glb), str(tmp)], check=True)
        shutil.move(tmp, input_glb)
        after = input_glb.stat().st_size
        ok(f"meshopt: {before} → {after} bytes ({(1 - after/before) * 100:.1f}% smaller)")
    except subprocess.CalledProcessError as e:
        err(f"meshopt failed: {e}")
        if tmp.exists():
            tmp.unlink()


def export_one(blender: str, blend_path: Path, output: Path, args: argparse.Namespace) -> bool:
    """Export a single .blend → .glb. Returns True on success."""
    info(f"export {blend_path.name} → {output}")

    # Write the script to a temp file because --python-text gets unwieldy with quoting
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(BLENDER_SCRIPT)
        script_path = f.name

    cmd = [
        blender,
        "--background",
        str(blend_path),
        "--python", script_path,
        "--",
        f"output={output}",
        f"draco={'1' if not args.no_draco else '0'}",
        f"apply={'1' if args.apply_transforms else '0'}",
        f"normals={'1' if args.recalc_normals else '0'}",
    ]
    if args.collection:
        cmd.append(f"collection={args.collection}")

    try:
        if args.quiet:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            if result.returncode != 0:
                err(f"Blender failed (code {result.returncode}):\n{result.stderr}")
                return False
        else:
            result = subprocess.run(cmd)
            if result.returncode != 0:
                err(f"Blender failed (code {result.returncode})")
                return False
    finally:
        Path(script_path).unlink(missing_ok=True)

    if not output.exists():
        err(f"Expected output not produced: {output}")
        return False

    if args.meshopt:
        run_meshopt(output)

    return True


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="+", help="One or more .blend files (globs supported)")
    p.add_argument("--output", help="Single-file output path (.glb)")
    p.add_argument("--output-dir", help="Batch output directory")
    p.add_argument("--no-draco", action="store_true", help="Skip Draco compression")
    p.add_argument("--meshopt", action="store_true", help="Post-process with gltf-transform meshopt")
    p.add_argument("--collection", help="Export only this Blender collection")
    p.add_argument("--apply-transforms", action="store_true", default=True)
    p.add_argument("--no-apply-transforms", dest="apply_transforms", action="store_false")
    p.add_argument("--recalc-normals", action="store_true", default=True)
    p.add_argument("--no-recalc-normals", dest="recalc_normals", action="store_false")
    p.add_argument("--blender", help="Path to blender executable")
    p.add_argument("--quiet", action="store_true", help="Suppress Blender stdout")
    args = p.parse_args()

    # Expand globs (Windows shell does not expand, so do it manually)
    inputs: list[Path] = []
    for spec in args.inputs:
        matches = glob(spec)
        if matches:
            inputs.extend(Path(m) for m in matches)
        else:
            inputs.append(Path(spec))
    inputs = [i.resolve() for i in inputs if i.suffix.lower() == ".blend"]

    if not inputs:
        err("No .blend files matched.")
        return 1

    # Single vs batch
    if len(inputs) == 1 and args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        blender = find_blender(args.blender)
        ok_count = 1 if export_one(blender, inputs[0], output, args) else 0
        return 0 if ok_count == 1 else 1

    if not args.output_dir:
        err("Multi-input mode requires --output-dir.")
        return 1

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    blender = find_blender(args.blender)

    succeeded = 0
    for blend in inputs:
        target = out_dir / (blend.stem + ".glb")
        if export_one(blender, blend, target, args):
            succeeded += 1

    info(f"Done. {succeeded}/{len(inputs)} exported.")
    return 0 if succeeded == len(inputs) else 1


if __name__ == "__main__":
    sys.exit(main())
