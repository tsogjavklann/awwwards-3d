# awwwards-3d

A Claude Code skill for building **Awwwards-style scroll-driven 3D websites** in the visual language of Active Theory, Lusion, 14islands, Bonhomme, Resn, Studio Freight, Locomotive, and Igloo Inc.

Stack: **Three.js r170** + **GSAP 3.12.5** (ScrollTrigger) + **Lenis 1.1** + three's built-in `EffectComposer`. Single-file HTML deliverables by default; Vite scaffold optional.

---

## What's inside

```
awwwards-3d/
├── SKILL.md                       The skill's "front door". Philosophy + the 5-step workflow.
├── references/
│   ├── ARCHITECTURE.md            Scene graph, lerp loop, scroll loop, render order, cleanup
│   ├── PATTERNS.md                33 copy-paste snippets (camera, materials, lighting, etc.)
│   ├── POST_PROCESSING.md         Canonical built-in EffectComposer chain
│   ├── SHADERS.md                 GLSL building blocks (noise, fresnel, dispersion, …)
│   ├── TRANSITIONS.md             Page transitions (View Transitions, Barba.js, custom GSAP)
│   ├── BLENDER_PIPELINE.md        Blender MCP recipes + GLB export config
│   └── ANTI_PATTERNS.md           20 "never do this" rules with code-review tells
├── assets/
│   ├── templates/
│   │   ├── minimal.html           Foundation — empty scene with full polish chain
│   │   ├── coin-scroll.html       Gold coin tumbles + falls on scroll (loads coin.glb)
│   │   ├── room-walkthrough.html  Camera follows spline through a low-poly interior
│   │   └── glass-product.html     Hero orb with MeshPhysicalMaterial transmission
│   ├── models/
│   │   ├── coin.glb               6 KB Draco-compressed gold coin
│   │   ├── glass_orb.glb          12 KB UV sphere for transmission
│   │   ├── blob.glb               6 KB displaced icosphere
│   │   └── room.glb               5 KB low-poly box room (floor + 3 walls + ceiling + sofa)
│   └── hdri/
│       └── README.md              Where to download HDRIs (Polyhaven, etc.)
└── scripts/
    ├── init_project.py            Scaffold a new project (vanilla or Vite)
    └── export_glb.py              Headless Blender → optimized GLB
```

## Quick start

### Run a template directly

```bash
cd assets
python -m http.server 8766
# open http://localhost:8766/templates/coin-scroll.html
```

### Scaffold a new project from a template

```bash
# Self-contained vanilla folder (single .html + GLBs + serve.py)
python scripts/init_project.py my-site --template coin-scroll --framework vanilla

# Or a full Vite project with package.json + vite.config.js
python scripts/init_project.py my-site --template glass-product --framework vite
cd my-site
npm install
npm run dev
```

### Build new GLB assets in Blender

```bash
# Headless export with Draco compression
python scripts/export_glb.py my-source.blend --output dist/hero.glb

# Add Meshopt post-pass for max compression
python scripts/export_glb.py my-source.blend --output dist/hero.glb --meshopt
```

## Locked tech stack

These versions are tested together. Don't bump silently.

| Package | Version | Why locked |
|---|---|---|
| three | 0.170.0 | Has `dispersion` (r166+) for chromatic glass; built-in addon paths stable |
| gsap (with ScrollTrigger) | 3.12.5 | ESM-friendly, plays well with Lenis |
| lenis | 1.1.0 | The `prevent` API requires explicit function, fixed across templates |

**Not used** (and why):
- `postprocessing` npm library — incompatible with three r170 (`Material.onBeforeRender` removed)
- `@studio-freight/lenis` — scope retired at v1.0.42; use `lenis` instead
- `@pmndrs/drei-vanilla` `MeshTransmissionMaterial` — built-in `MeshPhysicalMaterial` + `dispersion` covers ~95% of cases

## Skill activation

Triggered by phrases like:
- "Awwwards-style 3D site"
- "scroll-driven 3D"
- "WebGL hero"
- "creative dev portfolio"
- "premium 3D landing"
- Mongolian: "3D вэб", "scroll-тэй 3D", "Awwwards маягтай", "интерактив 3D"
- Mention of Three.js + GSAP + Lenis together

See `SKILL.md` for the full description and trigger list.

## Verification

Templates were verified end-to-end in Playwright (Chrome) on the developer's machine:
- minimal.html — 0 console errors
- coin-scroll.html — 0 console errors, GLB loaded via DRACOLoader
- room-walkthrough.html — 0 console errors, spline camera path
- glass-product.html — 0 console errors (1 harmless three.js HLSL compiler warning)

Blender recipes (BLENDER_PIPELINE.md) were verified end-to-end in Blender 5.1.1 via the `blender-mcp` MCP server. All four recipes produce the GLBs in `assets/models/` exactly as documented.

## License

MIT — see [LICENSE](LICENSE).

## Credits

Inspired by the work of:
- [Active Theory](https://activetheory.net) — WebGL flair, GLSL distortions
- [Lusion](https://lusion.co) — surreal product showcases, transmissive materials
- [14islands](https://14islands.com) — playful 3D + page transitions
- [Bonhomme](https://bonhomme.lol) — typography meets 3D, cursors
- [Resn](https://resn.co.nz) — atmospheric particle work
- [Studio Freight](https://studiofreight.com) — authors of Lenis
- [Locomotive](https://locomotive.ca) — scroll choreography
- [Igloo Inc.](https://igloo.inc) — landscape flyovers, narrative pacing
