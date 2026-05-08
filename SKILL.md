---
name: awwwards-3d
description: Build production-grade Awwwards-style scroll-driven 3D websites in the visual language of Active Theory, Lusion, 14islands, Bonhomme, Resn, Studio Freight, Locomotive, and Igloo Inc. Use when the user asks for an "Awwwards-style", "scroll-driven 3D", "WebGL hero", "3D landing page", "interactive product showcase", "scroll storytelling site", "cinematic web experience", "creative dev portfolio", "premium 3D site", "Lusion-style", "Active Theory-style", "scroll 3D animation", or mentions Three.js + GSAP + Lenis together. Also triggers on Mongolian phrases like "3D вэб", "scroll-тэй 3D", "premium вэбсайт", "cinematic вэб", "Awwwards маягтай", "3D landing", "интерактив 3D". Locks tech stack to Three.js r170 + GSAP 3.12.5 + Lenis 1.1.0 with three's built-in `EffectComposer` for post-processing. Produces single-file HTML deliverables when possible. Do NOT use for: static marketing sites without 3D, plain React/Next.js apps, dashboards, admin UIs, or simple landing pages where 3D would be decorative noise.
license: MIT
---

# Awwwards-Style 3D Websites

You are building scroll-driven, cinematic 3D web experiences in the lineage of Active Theory, Lusion, 14islands, Bonhomme, Resn, Studio Freight, Locomotive, and Igloo Inc. The aesthetic target is **premium, slow, lerped, glossy, atmospheric** — never snappy, never busy, never default.

## Core Philosophy

Read these before touching code. They are the difference between "Three.js demo" and "Awwwards Site of the Day".

1. **Aesthetics > Geometry.** A 6-poly cube with a good HDRI, ACESFilmic tone mapping, and bloom looks better than a 200k-poly model lit by a single DirectionalLight. Spend budget on lighting/post-processing first, geometry last.
2. **Lerp everything.** No value should ever change instantly. Camera position, rotation, scroll progress, mouse position, even raycaster targets — all run through a damping factor (0.06–0.1 is the sweet spot). The world feels alive because nothing snaps.
3. **Single-file HTML when possible.** Default deliverable is one `.html` file using ESM imports from `unpkg` (and `esm.sh` for GSAP). No build step unless the user explicitly asks for one. This is what makes the work portable, reviewable, and shareable.
4. **Mobile first, performance always.** Cap `pixelRatio` at `Math.min(devicePixelRatio, 2)`. Frustum-cull. Halve post-processing on mobile. Test on a mid-tier Android in Chrome DevTools before declaring done.
5. **ACESFilmic tone mapping is non-negotiable.** `renderer.toneMapping = THREE.ACESFilmicToneMapping` and `renderer.outputColorSpace = THREE.SRGBColorSpace`. Without this, everything looks flat and "WebGL-ish".
6. **`metalness > 0` requires an environment map.** A metallic material with no envMap is a black blob. Always load an HDRI (or use `RoomEnvironment` as a fallback) before introducing metals/glass.
7. **60fps target on desktop, 30fps floor on mobile.** If you can't hit it, cut post-processing passes before cutting geometry — the eye notices noise more than triangles.

## Locked Tech Stack

These versions are tested together. Do not upgrade without asking.

```
three                       0.170.0
gsap                        3.12.5  (with ScrollTrigger)
lenis                       1.1.0   (NOT @studio-freight/lenis — that scope was retired)
```

Post-processing uses **three's built-in `EffectComposer`** from `three/addons/postprocessing/`. The standalone `postprocessing` library (v6.36.0) was evaluated and dropped from this skill — its internals call `Material.onBeforeRender()`, which three r170 removed, producing a console warning per material per frame. Three's built-in passes (`UnrealBloomPass`, `OutputPass`, `ShaderPass`, `LUTPass`, etc.) cover every effect we need with zero version drift.

Glass uses **three's built-in `MeshPhysicalMaterial`** with `transmission: 1.0` + `dispersion: 1.2` (r166+ feature — chromatic refraction without external libs). The drei-vanilla `MeshTransmissionMaterial` is NOT in three core/addons; reach for it only when you need temporal distortion or per-object backbuffer sampling (then add `drei-vanilla` and `three-mesh-bvh@0.7.8` to your importmap). See PATTERNS.md #5 for both paths.

CDN imports use this importmap pattern (see `assets/templates/minimal.html` for the canonical example):

```html
<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.170.0/build/three.module.js",
    "three/addons/": "https://unpkg.com/three@0.170.0/examples/jsm/",
    "gsap": "https://esm.sh/gsap@3.12.5",
    "gsap/ScrollTrigger": "https://esm.sh/gsap@3.12.5/ScrollTrigger",
    "lenis": "https://unpkg.com/lenis@1.1.0/dist/lenis.mjs"
  }
}
</script>
```

> **Composer choice — settled:** This skill uses three's built-in `EffectComposer` from `three/addons/postprocessing/`. The standalone `postprocessing` npm library was tested and rejected: `postprocessing@6.36.0` flags `Material.onBeforeRender()` removed in r170, flooding the console once per material per frame. Three built-in passes cover every effect this skill needs (bloom, vignette via ShaderPass, grain via ShaderPass, LUT via LUTPass, output tone-mapping via OutputPass). See `references/POST_PROCESSING.md` for the canonical pass chain.

> **CDN reliability:** Default to `unpkg.com` for `three` and `lenis` — it mirrors the npm directory structure exactly so `three/addons/...` resolves cleanly. `cdn.jsdelivr.net` was tested and intermittently failed to serve `three@0.170.0/examples/jsm/postprocessing/*` files (`ERR_CONNECTION_CLOSED`) from some networks. Use `esm.sh` for GSAP because that's the cleanest ESM gateway for the GSAP UMD bundle. If unpkg is unreachable, fallback order: unpkg → esm.sh → cdn.skypack.dev. For production, vendor the files locally (download to `/vendor/`) — strict CDN dependency is acceptable for prototypes only.

> **Update policy:** Versions are locked because they were tested together. To upgrade: (1) bump in `assets/templates/minimal.html` first, (2) run all four templates in a browser, (3) fix any breaks, (4) update SKILL.md and PATTERNS.md. Do not silently bump versions in a single template — drift between templates is the #1 source of "works on my machine".

## The 5-Step Workflow

Follow this order. Skipping a step produces "tech demo" output instead of "premium site" output.

### Step 1 — Identify the Experience Archetype

Every Awwwards 3D site fits one of these. Pick one and commit:

| Archetype | Pattern | Reference |
|---|---|---|
| **Object showcase** | Single hero object, camera orbits/zooms on scroll | Bonhomme product pages, Apple AirPods Pro |
| **Room walkthrough** | Camera path through 3D interior | Igloo Inc., Bruno Simon portfolio |
| **Tunnel** | Camera flies forward through endless geometry | Active Theory experiments |
| **Vertical descent** | Scroll = falling/rising through layers | 14islands case studies |
| **Flyover** | Camera traverses a landscape | Lusion case studies |
| **Particle field** | Thousands of points reacting to scroll/mouse | Resn experiments |

Ask the user which archetype if they haven't said. Do not invent a new one — these are proven.

### Step 2 — Plan Assets

Choose the cheapest source that meets the bar:

1. **Three.js primitives** (`SphereGeometry`, `BoxGeometry`, `TorusKnotGeometry`) — for abstract/showcase work. Most Awwwards sites use these. Don't overlook them.
2. **Blender via MCP** — when you need a custom shape. See `references/BLENDER_PIPELINE.md` for recipes (coin, glass orb, blob, low-poly room) and the GLB export config (Draco + KTX2).
3. **Polyhaven** — HDRIs and textures, free, CC0. The HDRI is more important than the model.
4. **Sketchfab** — last resort for ready-made models. Always check polycount.

### Step 3 — Pick a Template

Start from `assets/templates/`:

- `minimal.html` — empty scene with HDRI, tone mapping, Lenis, post-processing wired up. Use as the foundation for anything custom.
- `coin-scroll.html` — coin rotates and falls on scroll (object showcase).
- `room-walkthrough.html` — camera moves along a spline through a room (room walkthrough).
- `glass-product.html` — single product with `MeshPhysicalMaterial` transmission + dispersion (r166+), HDRI, gentle bloom (object showcase, glass).

Templates are starting points, not final work. Strip what you don't need, layer what you do.

### Step 4 — Layer the Polish (in this order)

The order matters. Each layer assumes the previous is in place.

1. **HDRI** loaded and applied as `scene.environment`
2. **Tone mapping** — `ACESFilmicToneMapping`, exposure `1.0`–`1.2`
3. **Lighting** — even with HDRI, add one `DirectionalLight` for shadow direction
4. **Post-processing** — three built-in `EffectComposer` with HDR target → `RenderPass` → `UnrealBloomPass` (strength ~0.45, radius 0.4, threshold 0.82) → vignette `ShaderPass` → `OutputPass` (applies `renderer.toneMapping = ACESFilmic`) → grain `ShaderPass` last
5. **Lenis** smooth scroll wired to GSAP `ScrollTrigger.update`
6. **Custom cursor** (optional, but a Bonhomme/Lusion signature)
7. **Scroll timeline** — GSAP timeline driven by `ScrollTrigger`, lerping camera/object properties
8. **Film grain** as the final composite layer — custom `ShaderPass` with a time-driven noise fragment, intensity ~0.05 (see `references/POST_PROCESSING.md` § "Pass 5 — Film grain")

### Step 5 — Performance Audit

Before declaring done:

- [ ] Lighthouse Performance ≥ 85 on desktop, ≥ 70 on mobile
- [ ] FCP < 1.8s, LCP < 2.5s
- [ ] 60fps on desktop, 30fps minimum on mid-tier Android
- [ ] `pixelRatio` capped at 2
- [ ] GLB files Draco-compressed, textures KTX2 where possible
- [ ] No `console.log` inside `requestAnimationFrame` loops (kills perf in DevTools)
- [ ] All animations driven by `delta` time, not frame count

## Hard Rules — Never Do These

These ship broken work. See `references/ANTI_PATTERNS.md` for the long form.

1. **No snap animations.** Every property change goes through lerp or GSAP `ease`.
2. **No `metalness > 0` without an environment map.** Result: black blobs.
3. **No uncapped `pixelRatio`.** A 4K monitor with `devicePixelRatio = 2` will tank to 15fps.
4. **No uncompressed GLB.** Draco compression is mandatory (see `BLENDER_PIPELINE.md`).
5. **No auto-play audio.** Browsers block it; users hate it.
6. **No `console.log` in the animation loop.** Even one per frame destroys DevTools.
7. **No mixing CSS-driven and JS-driven scroll.** Lenis owns scroll. ScrollTrigger reads from Lenis. CSS `scroll-behavior: smooth` must be removed.
8. **No `OrbitControls` in production.** It's for prototyping. Real sites use scroll-driven cameras.
9. **No `ShaderMaterial` without precision declaration.** Mobile GPUs need `precision mediump float;`.
10. **No raycasting against the whole scene every frame.** Filter to a small array of interactable meshes.
11. **No frame-count-based animation.** All motion must be driven by `delta` from `clock.getDelta()` and multiplied by it. A 144Hz monitor and a 30Hz monitor must produce visually identical motion. For lerp, use a framerate-independent formula: `factor = 1 - Math.pow(1 - ease, delta * 60)` instead of raw `ease`.

## Reference Files

Load these on demand — do not read all of them at start.

- `references/ARCHITECTURE.md` — scene structure, the lerp/scroll loop, render order
- `references/PATTERNS.md` — 33 copy-paste code snippets for common needs
- `references/PROCEDURAL_GEOMETRY.md` — code-only geometry generation; primitives, math-driven shapes, vertex displacement, hybrid Blender patterns. The default path before reaching for AI 3D generators.
- `references/BLENDER_PIPELINE.md` — Blender MCP recipes + GLB export config
- `references/SHADERS.md` — GLSL building blocks (noise, fresnel, dispersion, custom materials)
- `references/POST_PROCESSING.md` — bloom, DOF, grain, chromatic aberration recipes
- `references/TRANSITIONS.md` — Barba.js page transitions, View Transitions API
- `references/ANTI_PATTERNS.md` — long-form list of what kills the aesthetic and why

## Inspiration Archive

When the user is undecided about direction, point them here. Open these in a browser, do not screenshot or scrape.

- **Active Theory** — https://activetheory.net — masters of WebGL flair, GLSL distortions, hand-crafted bloom and dispersion
- **Lusion** — https://lusion.co — surreal product showcases, transmissive materials, perfect color grading
- **14islands** — https://14islands.com — playful 3D, signature page transitions, tasteful typography over scenes
- **Bonhomme** — https://bonhomme.lol — bold typography meets 3D, distinctive cursors, art-direction-led
- **Resn** — https://resn.co.nz — atmospheric particle work, dreamlike palettes, slow camera moves
- **Studio Freight** — https://studiofreight.com — authors of Lenis; minimalism + perfectly tuned smoothness
- **Locomotive** — https://locomotive.ca — original Locomotive Scroll authors; scroll choreography mastery
- **Igloo Inc.** — https://igloo.inc — landscape flyovers, narrative pacing, Pixar-grade lighting
- **Awwwards Sites of the Day** — https://www.awwwards.com/websites/sites_of_the_day/ — daily curated archive for current trends

## Audio (Optional but Signature)

~70% of Awwwards 3D winners include subtle audio: ambient drones, hover ticks, scroll whooshes. Done well, audio is the difference between "site" and "experience". Done badly, it's the reason users close the tab in the first 2 seconds.

**Rules:**
- Use Howler.js (`https://esm.sh/howler@2.2.4`) or the Web Audio API. No `<audio>` tag for ambient.
- **Always** gate playback behind a user gesture (button click, scroll-into-view past first viewport). Browsers block autoplay anyway, but the UX rule is stricter: never start sound the user didn't ask for.
- Provide a persistent mute toggle in the UI corner. Default: **OFF on mobile**, **OFF on first visit** (use `localStorage` to remember the user's choice on return).
- Loop ambient at -18 dB to -24 dB. UI sounds at -12 dB to -18 dB.
- Preload short SFX, lazy-load ambient (it's the bigger file).
- Pause audio on `document.visibilitychange` when the tab is hidden.

**File format:** Always include both `.webm` (Opus) and `.mp3` for compatibility. Howler picks the best one automatically.

## Output Format

Default deliverable: a **single `.html` file** that includes all CSS, JS, and importmap inline — portable, reviewable, fork-able by pasting one file.

> **Important — `file://` limitation:** these templates use ESM imports from CDNs via `<script type="importmap">`. Browsers block CDN fetches from `file://` origins (treated as unique security origins). **Double-clicking the .html will fail.** The user must serve it over HTTP:
>
> ```powershell
> cd <folder containing the .html>
> python -m http.server 8765
> # then open: http://localhost:8765/<filename>.html
> ```
>
> Always include this two-line instruction at the top of any template you ship to the user. Do not assume they know.

If the user asks for a multi-file build (Vite, Next.js), ask which framework before scaffolding. Then run `scripts/init_project.py` to generate the project skeleton — that path produces a `package.json` so `npm run dev` handles the server automatically.

## When You Get Stuck

- Camera/object behavior wrong → re-read `references/ARCHITECTURE.md` (the lerp loop section).
- Material looks flat or black → HDRI not loaded, or tone mapping not set. Check `Step 4 — Layer the Polish`.
- Performance bad → cut post-processing passes first, geometry last. See `references/POST_PROCESSING.md`.
- Scroll feels janky → Lenis not wired to ScrollTrigger. See `references/PATTERNS.md` § "Lenis + ScrollTrigger".
- "It works but doesn't feel premium" → you skipped Step 4. Go back and layer in order.
