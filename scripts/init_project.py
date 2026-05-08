#!/usr/bin/env python3
"""
init_project.py — scaffold a new Awwwards-style 3D project from a skill template.

Usage:
    python init_project.py <project-name> [--template TEMPLATE] [--framework FW]
                                          [--models MODELS] [--force] [--no-git]

Examples:
    python init_project.py my-coin-site --template coin-scroll --framework vite
    python init_project.py glass-demo --template glass-product --framework vanilla
    python init_project.py portfolio --template minimal --framework vite --models all

Templates available:
    minimal           — empty scene with the canonical lerp + composer chain
    coin-scroll       — gold coin tumbles + falls on scroll (uses coin.glb)
    room-walkthrough  — camera follows spline through a low-poly room
    glass-product     — single hero orb with MeshPhysicalMaterial transmission

Frameworks:
    vanilla           — single .html file + GLBs, plus a tiny http.server snippet
    vite              — full Vite project (package.json, vite.config.js, src/)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_ROOT / "assets" / "templates"
MODELS_DIR = SKILL_ROOT / "assets" / "models"
HDRI_DIR = SKILL_ROOT / "assets" / "hdri"

VALID_TEMPLATES = ["minimal", "coin-scroll", "room-walkthrough", "glass-product"]
VALID_FRAMEWORKS = ["vanilla", "vite"]
VALID_MODELS_OPTS = ["none", "matching", "all"]

# Pinned versions — must match SKILL.md "Locked Tech Stack"
LOCKED_VERSIONS = {
    "three": "0.170.0",
    "gsap": "3.12.5",
    "lenis": "1.1.0",
}

# Maps template → which model files it references
TEMPLATE_MODELS = {
    "minimal": [],
    "coin-scroll": ["coin.glb"],
    "room-walkthrough": ["room.glb"],
    "glass-product": ["glass_orb.glb"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Ensure UTF-8 stdout on Windows (cp1251 default would mangle log glyphs).
# This is a no-op where stdout already supports UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


def err(msg: str) -> None:
    print(f"[x] {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"[.] {msg}")


def ok(msg: str) -> None:
    print(f"[+] {msg}")


def fail(msg: str, code: int = 1) -> None:
    err(msg)
    sys.exit(code)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip("\n"), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Template scaffolders
# ─────────────────────────────────────────────────────────────────────────────

def scaffold_vanilla(target: Path, template: str, copy_models: list[str]) -> None:
    """Copy the .html template + any required GLB files. Add a tiny serve script."""
    src_html = TEMPLATES_DIR / f"{template}.html"
    if not src_html.exists():
        fail(f"Template not found: {src_html}")

    # index.html
    target_html = target / "index.html"
    target_html.parent.mkdir(parents=True, exist_ok=True)
    html = src_html.read_text(encoding="utf-8")

    # Adjust the relative model path: original `../models/<file>.glb` → `models/<file>.glb`
    # (because the vanilla scaffold flattens templates/ and models/ into one folder)
    html = html.replace("'../models/", "'models/").replace('"../models/', '"models/')
    target_html.write_text(html, encoding="utf-8")
    ok(f"index.html  ← templates/{template}.html (paths flattened)")

    # Copy GLBs
    if copy_models:
        models_target = target / "models"
        models_target.mkdir(parents=True, exist_ok=True)
        for m in copy_models:
            src_glb = MODELS_DIR / m
            if src_glb.exists():
                shutil.copy2(src_glb, models_target / m)
                ok(f"models/{m}")
            else:
                err(f"Missing GLB: {src_glb}")

    # Tiny serve script
    write(target / "serve.py", """
        # Tiny HTTP server. Run with: python serve.py
        import http.server, socketserver
        PORT = 8765
        with socketserver.TCPServer(("127.0.0.1", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
            print(f"http://127.0.0.1:{PORT}")
            httpd.serve_forever()
    """)
    ok("serve.py (run: python serve.py)")


def scaffold_vite(target: Path, template: str, copy_models: list[str]) -> None:
    """Generate a full Vite project."""
    src_html = TEMPLATES_DIR / f"{template}.html"
    if not src_html.exists():
        fail(f"Template not found: {src_html}")

    full_html = src_html.read_text(encoding="utf-8")

    # Vite source — split index.html / src/main.js
    # Strip the inline <script type="module">…</script> block; that becomes src/main.js.
    import re

    script_match = re.search(
        r'<script type="module">([\s\S]*?)</script>',
        full_html,
    )
    if not script_match:
        fail(f"Could not extract <script type='module'> from {template}.html")

    main_js = script_match.group(1).strip()
    # In Vite, bare-specifier imports resolve via package.json — no importmap needed.
    # But our templates' importmap maps "three/addons/..." which Vite handles natively when
    # `three` is installed. We just need to drop the importmap from index.html.

    html_without_script = full_html.replace(script_match.group(0),
        '<script type="module" src="/src/main.js"></script>')
    html_without_script = re.sub(
        r'<script type="importmap">[\s\S]*?</script>',
        '', html_without_script
    )

    # Adjust GLB paths for Vite public/ folder convention
    main_js = main_js.replace("'../models/", "'/models/").replace('"../models/', '"/models/')
    main_js = main_js.replace("'https://unpkg.com/three@0.170.0/examples/jsm/libs/draco/'",
                              "'/draco/'")

    write(target / "index.html", html_without_script)
    write(target / "src" / "main.js", main_js)
    ok("index.html (importmap stripped, script extracted to src/main.js)")
    ok("src/main.js")

    # package.json
    write(target / "package.json", f"""
        {{
          "name": "{target.name}",
          "version": "0.1.0",
          "private": true,
          "type": "module",
          "scripts": {{
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
          }},
          "dependencies": {{
            "three": "{LOCKED_VERSIONS['three']}",
            "gsap": "{LOCKED_VERSIONS['gsap']}",
            "lenis": "{LOCKED_VERSIONS['lenis']}"
          }},
          "devDependencies": {{
            "vite": "^5.4.0"
          }}
        }}
    """)
    ok("package.json (three+gsap+lenis pinned)")

    # vite.config.js
    write(target / "vite.config.js", """
        import { defineConfig } from 'vite';
        export default defineConfig({
          server: { host: '127.0.0.1', port: 5173 },
          build: { target: 'esnext', sourcemap: true, assetsInlineLimit: 0 },
        });
    """)
    ok("vite.config.js")

    # Copy GLBs to public/
    if copy_models:
        public_models = target / "public" / "models"
        public_models.mkdir(parents=True, exist_ok=True)
        for m in copy_models:
            src_glb = MODELS_DIR / m
            if src_glb.exists():
                shutil.copy2(src_glb, public_models / m)
                ok(f"public/models/{m}")
            else:
                err(f"Missing GLB: {src_glb}")

    # Copy DRACO decoder so we don't depend on a CDN at runtime
    # (three's decoder lives in node_modules after npm install — copy on demand is fine)
    info("Run `npm install` then `npm run dev` to start.")


# ─────────────────────────────────────────────────────────────────────────────
# Common files (regardless of framework)
# ─────────────────────────────────────────────────────────────────────────────

def write_gitignore(target: Path) -> None:
    write(target / ".gitignore", """
        node_modules/
        dist/
        .vite/
        .DS_Store
        Thumbs.db
        *.log
        .env
        .env.local
        # Blender backup files
        *.blend1
        # Python
        __pycache__/
        *.pyc
    """)


def write_readme(target: Path, project_name: str, template: str, framework: str) -> None:
    if framework == "vite":
        run_cmd = "npm install && npm run dev"
        url = "http://127.0.0.1:5173"
    else:
        run_cmd = "python serve.py"
        url = "http://127.0.0.1:8765"

    write(target / "README.md", f"""
        # {project_name}

        Awwwards-style 3D site, scaffolded from the **{template}** template ({framework} setup).

        ## Run

        ```bash
        {run_cmd}
        ```

        Then open {url}

        ## Stack (locked versions)

        - three.js {LOCKED_VERSIONS['three']}
        - GSAP {LOCKED_VERSIONS['gsap']} (with ScrollTrigger)
        - Lenis {LOCKED_VERSIONS['lenis']}
        - Post-processing: three's built-in `EffectComposer`

        ## Built from skill

        This project was scaffolded from the **awwwards-3d** Claude Code skill.
        See the skill's `references/` folder for architecture, patterns, and post-processing recipes.
    """)
    ok("README.md")


def init_git(target: Path) -> None:
    try:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=target, check=True)
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Initial commit (awwwards-3d skill scaffold)"],
            cwd=target, check=True,
        )
        ok("git initialized + initial commit")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        err(f"git init failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project_name", help="Name of the new project (also used as folder name)")
    p.add_argument("--template", choices=VALID_TEMPLATES, default="minimal")
    p.add_argument("--framework", choices=VALID_FRAMEWORKS, default="vanilla")
    p.add_argument("--models", choices=VALID_MODELS_OPTS, default="matching",
                   help="Which GLBs to copy: matching (only what the template needs), "
                        "all (every GLB in models/), none.")
    p.add_argument("--force", action="store_true", help="Overwrite if target folder exists")
    p.add_argument("--no-git", action="store_true", help="Skip git init")
    args = p.parse_args()

    target = Path(args.project_name).resolve()

    # Pre-flight
    if not TEMPLATES_DIR.exists():
        fail(f"Templates folder missing: {TEMPLATES_DIR}\n"
             f"Run this script from inside the awwwards-3d skill repo.")

    if target.exists() and any(target.iterdir()):
        if not args.force:
            fail(f"Target folder is not empty: {target}\nUse --force to overwrite.")
        info(f"--force: clearing {target}")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    info(f"Project: {target}")
    info(f"Template: {args.template}  |  Framework: {args.framework}  |  Models: {args.models}")

    # Decide which GLBs to copy
    if args.models == "none":
        copy_models = []
    elif args.models == "all":
        copy_models = sorted(p.name for p in MODELS_DIR.glob("*.glb"))
    else:  # matching
        copy_models = TEMPLATE_MODELS.get(args.template, [])

    # Scaffold
    if args.framework == "vanilla":
        scaffold_vanilla(target, args.template, copy_models)
    elif args.framework == "vite":
        scaffold_vite(target, args.template, copy_models)

    # Common
    write_gitignore(target)
    write_readme(target, args.project_name, args.template, args.framework)

    if not args.no_git:
        init_git(target)

    print()
    ok(f"Done. cd {args.project_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
