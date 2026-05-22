# needle-drift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `assets/templates/needle-drift.html` — a 5th Awwwards-style scroll-driven 3D template covering the Tunnel archetype, with ~6,000 InstancedMesh needles in a dreamlike fog. Mirror to `docs/`, update README/SKILL.md.

**Architecture:** Single-file HTML, ESM via importmap, three r170 + GSAP 3.12.5 + Lenis 1.1, three's built-in EffectComposer. Scaffolded from `assets/templates/minimal.html` (the project's canonical foundation). Hero is a single InstancedMesh with `onBeforeCompile`-patched MeshStandardMaterial — adds 6 uniforms + 1 per-instance attribute for scroll-modulated alpha/color/band-phase. A single GSAP timeline (scrubbed by ScrollTrigger via Lenis) drives lerp targets across 4 scroll beats.

**Tech Stack:** three@0.170.0, gsap@3.12.5 (ScrollTrigger), lenis@1.1.0, three built-in EffectComposer chain (RenderPass → UnrealBloomPass → vignette ShaderPass → OutputPass → grain ShaderPass).

**Spec:** `specs/2026-05-22-needle-drift-design.md` (commit `8d327ac`). Read it before starting — the plan does not repeat the spec's rationale.

**Local server (assumed running by harness):** `python -m http.server 8766` from `assets/`. Target URL throughout: `http://localhost:8766/templates/needle-drift.html`.

---

## Verification Approach

This project has **no unit-test framework** for visual templates. Each task's verification is one of:
- **Page-load check** — open the URL in a fresh tab; the preloader hides, no `[awwwards-3d]` console errors.
- **DevTools console probe** — set a uniform value or evaluate a JS expression, observe visual change.
- **Visual diff** — described intended visual state ("needles in fog", "bloom on tips"), engineer eyeballs against description.
- **File diff** — `git diff` or `git diff --no-index` returns expected lines.

After every code-modifying task, run this two-line check before commit:

```powershell
# In any shell — replace the URL probe
curl.exe -sI http://localhost:8766/templates/needle-drift.html
# Expect: HTTP/1.0 200 OK
```

Open the URL in a browser, open DevTools Console, hard-reload (Ctrl+Shift+R). If the console has no red errors and the visual matches the task's expected state, proceed.

---

## File Structure (locked from spec §9)

| Path | Action | Final size |
|---|---|---|
| `assets/templates/needle-drift.html` | Create | ~600 lines (will exceed spec's "~500" estimate by ~20% — shader patch + scatter loop add real weight; siblings are 499–576) |
| `docs/templates/needle-drift.html` | Create (mirror) | identical |
| `README.md` | Modify | +6 lines (table row + tree entry) |
| `SKILL.md` | Modify | +1 line (Step 3 list) |

No other files touched. `assets/models/*` unchanged. `references/*.md` unchanged. `scripts/*` unchanged.

---

## Pre-flight

- [ ] **Step 0.1: Confirm working directory and branch**

```powershell
cd C:\Users\Ben\Documents\GitHub\awwwards-3d
git status
git log --oneline -3
```

Expected: working tree clean (or only this plan file untracked); HEAD at `8d327ac docs: add needle-drift template design spec` or descendant.

- [ ] **Step 0.2: Confirm server is reachable**

```powershell
curl.exe -sI http://localhost:8766/templates/minimal.html
```

Expected: `HTTP/1.0 200 OK`. If not, start it: `cd assets ; python -m http.server 8766`.

- [ ] **Step 0.3: Open the spec in a side pane**

`specs/2026-05-22-needle-drift-design.md` — sections §4 (palette), §5 (scene), §6 (shader patch), §7 (timeline), §8 (polish chain) will be referenced repeatedly.

---

## Task 1: Scaffold needle-drift.html from minimal.html with new identity

Smallest possible first commit. Copy the canonical scaffold; change ONLY the things that identify the file (title, header comment, palette CSS, section copy). The 3D scene is still the icosahedron from minimal — that's fine, we'll replace it in Task 4.

**Files:**
- Create: `assets/templates/needle-drift.html` (copy of `minimal.html`)

- [ ] **Step 1.1: Copy minimal.html → needle-drift.html**

```powershell
Copy-Item assets\templates\minimal.html assets\templates\needle-drift.html
```

- [ ] **Step 1.2: Replace the header comment block (lines 2–15)**

Open `assets/templates/needle-drift.html`. Replace lines 2–15 with:

```html
<!--
  ┌──────────────────────────────────────────────────────────────────┐
  │ HOW TO RUN — DO NOT double-click this file.                      │
  │                                                                  │
  │ This template is pure procedural (no GLB). Serve it over HTTP    │
  │ because the importmap fetches three/gsap/lenis from CDNs and     │
  │ browsers block CDN fetches from file:// origins:                 │
  │                                                                  │
  │   cd assets                                                      │
  │   python -m http.server 8766                                     │
  │   → open http://localhost:8766/templates/needle-drift.html       │
  │                                                                  │
  │ Archetype: Tunnel (per SKILL.md Step 1).                         │
  │ Hero: ~6000 instanced needles in dreamlike lavender/teal fog.    │
  └──────────────────────────────────────────────────────────────────┘
-->
```

- [ ] **Step 1.3: Replace `<title>` and favicon**

Find `<title>Awwwards 3D — minimal foundation</title>` and replace with:

```html
<title>Awwwards 3D — needle drift</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6' fill='%239d93c4'/%3E%3C/svg%3E">
```

(Lavender favicon `#9d93c4` replaces minimal's white `#ffffff`.)

- [ ] **Step 1.4: Replace the body-background and color CSS**

In the `<style>` block, find:

```css
html, body {
  overscroll-behavior: none;
  scroll-behavior: auto;
  background: #0a0a0e;
  color: #fff;
}
```

Replace with:

```css
html, body {
  overscroll-behavior: none;
  scroll-behavior: auto;            /* MUST NOT be 'smooth' — fights Lenis */
  background: #16121d;
  color: #d8d3e8;
}
```

Then find `#preloader { ... background: #0a0a0e; color: #fff; ... }` and change to:

```css
#preloader {
  position: fixed; inset: 0;
  background: #16121d;
  color: #d8d3e8;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  z-index: 9000;
  transition: opacity 0.6s ease, visibility 0.6s;
  gap: 1rem;
}
```

Then change the preloader-bar / preloader-fill colors. Find:

```css
.preloader-bar { width: clamp(160px, 30vw, 280px); height: 1px; background: rgba(255,255,255,0.12); }
.preloader-fill { height: 100%; width: 0%; background: #fff; transition: width 0.2s ease; }
```

Replace with:

```css
.preloader-bar { width: clamp(160px, 30vw, 280px); height: 1px; background: rgba(216,211,232,0.16); }
.preloader-fill { height: 100%; width: 0%; background: #d8d3e8; transition: width 0.2s ease; }
```

Then update the `.meta` opacity for the warmer palette. Find:

```css
section .meta {
  position: absolute; top: clamp(1.5rem, 5vw, 4rem); left: clamp(1.5rem, 5vw, 4rem);
  font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase;
  opacity: 0.6;
}
```

Replace `opacity: 0.6;` with `opacity: 0.55; color: #e8d8c2;` (warm-grey accent per spec §4 palette).

- [ ] **Step 1.5: Replace the four sections of copy**

Find the `<main class="scroll-container">` block and replace it with:

```html
<main class="scroll-container">
  <section><span class="meta">01 — Enter</span><h1>Step into the haze</h1></section>
  <section><span class="meta">02 — Drift</span><h2>Let it carry you</h2></section>
  <section><span class="meta">03 — Bloom</span><h2>Everything brightens at once</h2></section>
  <section><span class="meta">04 — Vanish</span><h2>And softly thins to nothing</h2></section>
</main>
```

- [ ] **Step 1.6: Update the script's leading comment**

Find the `// ── Awwwards 3D — minimal foundation template` block (around line 154–157 in the original) and replace with:

```js
// ─────────────────────────────────────────────────────────────────────────
// Awwwards 3D — needle drift template
// Three.js r170 + GSAP 3.12.5 + Lenis 1.1.0 + three built-in EffectComposer
// Archetype: Tunnel. Hero: ~6000 instanced needles, dreamlike fog.
// See specs/2026-05-22-needle-drift-design.md for the design rationale.
// ─────────────────────────────────────────────────────────────────────────
```

- [ ] **Step 1.7: Verify the page loads**

```powershell
curl.exe -sI http://localhost:8766/templates/needle-drift.html
```

Expected: `HTTP/1.0 200 OK`.

Open `http://localhost:8766/templates/needle-drift.html` in a browser. Hard-reload (Ctrl+Shift+R). Expected visual:
- Browser tab title: `Awwwards 3D — needle drift`
- Page background: deep plum (`#16121d`)
- Chrome icosahedron still floats (placeholder from minimal — we'll replace in Task 4)
- 4 sections of new copy ("Step into the haze", etc.) appear as you scroll
- DevTools Console: no `[awwwards-3d]` errors

- [ ] **Step 1.8: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat: scaffold needle-drift template (identity only, scene still placeholder)"
```

---

## Task 2: Replace scene/camera/fog with tunnel framing

The icosahedron stage is still there — we just rebuild the scene's *backdrop* (fog + camera) to match the tunnel framing in spec §5. The placeholder icosahedron will look strange (it'll drift into fog) — that's expected. Tasks 3–4 remove it.

**Files:**
- Modify: `assets/templates/needle-drift.html` — the "scene & camera" block

- [ ] **Step 2.1: Replace the scene+camera setup**

Find this block (currently sourced from `minimal.html` lines 207–212):

```js
// ── scene & camera ──────────────────────────────────────────────────────
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0a0e);

const camera = new THREE.PerspectiveCamera(35, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 1.2, 6);
```

Replace with:

```js
// ── scene & camera ──────────────────────────────────────────────────────
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x16121d);
// FogExp2 — color is mutated per frame by the lerp loop (see tick()).
// Density also gets scrolled (thickens in section 4).
scene.fog = new THREE.FogExp2(0x16121d, 0.022);

const camera = new THREE.PerspectiveCamera(
  40,                                // slightly wider than minimal (35) for tunnel depth
  window.innerWidth / window.innerHeight,
  0.1,
  120,
);
camera.position.set(0, 0, -5);       // starts behind the tube origin
```

- [ ] **Step 2.2: Lower the exposure**

Find `renderer.toneMappingExposure = 1.0;` and change to:

```js
renderer.toneMappingExposure = 0.95;
```

(Fog scenes look better slightly underexposed — per spec §8.)

- [ ] **Step 2.3: Verify**

Reload. Expected:
- Backdrop is now lavender-tinted dark (`#16121d`) with exponential fog
- Icosahedron is still visible but drifts into fog quickly (camera now at z=-5 instead of z=6, and the icosahedron is at origin)
- No console errors

- [ ] **Step 2.4: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat(needle-drift): scene background + FogExp2 + tunnel camera framing"
```

---

## Task 3: Replace lighting and remove the icosahedron/floor stage

Strip the placeholder. After this task the scene will be *empty* (fog only) — that's correct and intentional. Task 4 fills it.

**Files:**
- Modify: `assets/templates/needle-drift.html` — lighting block + stage block + renderer shadow settings

- [ ] **Step 3.1: Disable shadow map (fog hides shadows; no needles cast them)**

Find:

```js
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.VSMShadowMap;
```

Replace with:

```js
// Shadows disabled — fog hides them anyway, and needles don't cast.
renderer.shadowMap.enabled = false;
```

- [ ] **Step 3.2: Replace the lighting block**

Find the `// ── lighting ──` block (currently the 3-light setup from minimal). Replace the entire block with:

```js
// ── lighting (subtle directional grade — fog does most of the atmosphere work) ──
const lighting = new THREE.Group(); lighting.name = 'lighting';

const keyLight = new THREE.DirectionalLight(0xcab8e8, 0.6);     // lavender-tinted key
keyLight.position.set(4, 8, 4);

const rimLight = new THREE.DirectionalLight(0xddeef0, 0.4);    // cool white rim from behind
rimLight.position.set(0, 2, -10);

lighting.add(keyLight, rimLight);
scene.add(lighting);
```

- [ ] **Step 3.3: Replace the stage block (drop icosahedron + floor)**

Find the `// ── stage ──` block (containing `heroGeom`, `heroMat`, `hero`, `floor`, `stage.add(...)`). Replace the *entire* block with:

```js
// ── stage (needle field is built in next task) ──────────────────────────
const stage = new THREE.Group(); stage.name = 'stage';
scene.add(stage);
```

- [ ] **Step 3.4: Remove references to deleted symbols**

The `playIntro()` function (near the bottom) references `hero.scale`. Find:

```js
function playIntro() {
  preloader.classList.add('done');
  // pre-warm shader compile so the first frame doesn't hitch
  renderer.compile(scene, camera);
  composer.render(0.016);

  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
  tl.from(camera.position, { z: 14, duration: 2.2 }, 0)
    .from(camera, { fov: 55, duration: 2.2,
      onUpdate: () => camera.updateProjectionMatrix() }, 0)
    .from(hero.scale, { x: 0, y: 0, z: 0, duration: 1.4, ease: 'back.out(1.4)' }, 0.25);
}
```

Replace with:

```js
function playIntro() {
  preloader.classList.add('done');
  // pre-warm shader compile so the first frame doesn't hitch
  renderer.compile(scene, camera);
  composer.render(0.016);

  // Subtle intro: camera dollies in slightly (no scale pop — needles fade in
  // naturally because uDensity starts at 0.30, ramps via scroll).
  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
  tl.from(camera.position, { z: -12, duration: 2.4 }, 0)
    .from(camera, { fov: 60, duration: 2.4,
      onUpdate: () => camera.updateProjectionMatrix() }, 0);
}
```

Also find the `tick()` function and remove the two lines that reference `hero`:

```js
  hero.rotation.y = state.heroRotY.current;
  hero.position.y = Math.sin(t * 0.6) * 0.1;     // gentle hover
```

Delete both lines. (We'll add needle uniform pushes in Task 9.)

Also find and remove the line `.to(state.heroRotY, { target: Math.PI * 2, ease: 'none' }, 0);` inside the scroll timeline — `heroRotY` no longer exists. (Don't worry about the full timeline rewrite yet; Task 8 replaces it.)

- [ ] **Step 3.5: Verify**

Reload. Expected:
- Scene is now empty fog. Just a lavender-plum void.
- DevTools Console: **no errors** (the hero/heroRotY references should all be gone)
- The page may scroll without visual change (timeline still references the old state keys for cameraY/cameraZ — that's fine; Task 7+8 fix this)

If you see `ReferenceError: hero is not defined`, you missed a reference. Grep the file:

```powershell
Select-String -Path assets\templates\needle-drift.html -Pattern '\bhero\b'
```

Expected: zero matches (or matches only in comments).

- [ ] **Step 3.6: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat(needle-drift): strip placeholder hero, fog-only scene with tunnel lighting"
```

---

## Task 4: Add deterministic PRNG + InstancedMesh of 6000 needles

The hero arrives. After this task the scene shows ~6000 thin needles in a cylindrical scatter, no shader patch yet — they'll be a flat lavender color, fully opaque, no scroll modulation.

**Files:**
- Modify: `assets/templates/needle-drift.html` — add PRNG helper near top of module; populate stage block

- [ ] **Step 4.1: Add deterministic PRNG helper**

Find this block (immediately after the imports and `gsap.registerPlugin(ScrollTrigger);`):

```js
gsap.registerPlugin(ScrollTrigger);

// ── renderer ────────────────────────────────────────────────────────────
```

Insert this between the two:

```js
gsap.registerPlugin(ScrollTrigger);

// ── deterministic PRNG (mulberry32) ─────────────────────────────────────
// Why not Math.random: we want identical needle scatter on every reload so
// the scene is art-directable and reproducible across machines.
function mulberry32(seed) {
  let a = seed >>> 0;
  return function() {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(0xDEAD);

// ── renderer ────────────────────────────────────────────────────────────
```

- [ ] **Step 4.2: Replace the stage block with the needle field**

Find this from Task 3:

```js
// ── stage (needle field is built in next task) ──────────────────────────
const stage = new THREE.Group(); stage.name = 'stage';
scene.add(stage);
```

Replace with:

```js
// ── needle field ────────────────────────────────────────────────────────
const stage = new THREE.Group(); stage.name = 'stage';

const INSTANCE_COUNT = 6000;
const TUBE_RADIUS = 3.5;
const TUBE_LENGTH = 80;
const Y_SQUASH = 0.7;       // vertical flatten — reads horizon-friendly

const needleGeom = new THREE.BoxGeometry(0.02, 1.5, 0.02);
const needleMat = new THREE.MeshStandardMaterial({
  color: 0xc8c0e4,          // lavender-leaning base; gets palette-multiplied in shader patch (Task 5)
  roughness: 0.55,
  metalness: 0.0,
  transparent: true,
  depthWrite: false,        // critical: prevents transparent-on-transparent z-fighting
  envMapIntensity: 0.3,
});

const needles = new THREE.InstancedMesh(needleGeom, needleMat, INSTANCE_COUNT);
needles.instanceMatrix.setUsage(THREE.StaticDrawUsage);
needles.frustumCulled = false;   // the cluster is huge; frustum check on bbox misleads

// Build per-instance transforms + aBand attribute.
const dummy = new THREE.Object3D();
const aBand = new Float32Array(INSTANCE_COUNT);
for (let i = 0; i < INSTANCE_COUNT; i++) {
  const r = TUBE_RADIUS * Math.pow(rand(), 1.4);         // ^1.4 biases toward thinning at edges
  const theta = rand() * Math.PI * 2;
  const z = rand() * TUBE_LENGTH;
  dummy.position.set(
    r * Math.cos(theta),
    r * Math.sin(theta) * Y_SQUASH,
    z,
  );
  dummy.rotation.set(rand() * Math.PI, rand() * Math.PI, rand() * Math.PI);
  const sy = 0.7 + rand() * 0.6;                          // 0.7 to 1.3 length variance
  dummy.scale.set(1, sy, 1);
  dummy.updateMatrix();
  needles.setMatrixAt(i, dummy.matrix);
  aBand[i] = i / INSTANCE_COUNT;                          // monotonic — instance order is already spatially random
}
needles.instanceMatrix.needsUpdate = true;
needleGeom.setAttribute('aBand', new THREE.InstancedBufferAttribute(aBand, 1));

stage.add(needles);
scene.add(stage);
```

- [ ] **Step 4.3: Verify visual + determinism**

Reload. Expected:
- A cluster of ~6000 thin lavender needles is visible in the fog, scattered in front of and around the camera. (Camera is at z=-5; needles are at z=0..80, so most are *ahead* of you.)
- Console clean
- Move/zoom the browser viewport — needles do NOT pop in/out at edges (frustumCulled=false)

Determinism check: hard-reload twice. The first needle's position should be identical both times. Add this temporary probe right after the loop (`needles.setMatrixAt(...)` line):

```js
// TEMP probe — remove before commit
const m = new THREE.Matrix4();
needles.getMatrixAt(0, m);
console.log('[needle-drift] needle 0 matrix elements:', m.elements.slice(0, 4));
```

Reload twice. Console should print identical 4-tuples both times. **Remove the probe** after confirming, then proceed.

- [ ] **Step 4.4: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat(needle-drift): 6000 instanced needles, deterministic scatter, edge falloff"
```

---

## Task 5: Apply the onBeforeCompile shader patch

This wires the spec §6 patch onto `needleMat`. After this task, needles will look *faded* (uDensity=0.30 default → 30% alpha). DevTools-driven uniform tweaks should change their look without reload.

**Files:**
- Modify: `assets/templates/needle-drift.html` — extend the needle material setup

- [ ] **Step 5.1: Add palette colors and uniforms object BEFORE the InstancedMesh creation**

Find the line `const needleMat = new THREE.MeshStandardMaterial({` and INSERT this block immediately above it:

```js
// Palette colors (specified in sRGB hex; convert to linear so shader math is correct).
const colorLavender = new THREE.Color(0x9d93c4).convertSRGBToLinear();
const colorTeal     = new THREE.Color(0x7faaa6).convertSRGBToLinear();
const fogColorA = new THREE.Color(0x16121d);                  // near-lavender fog (Enter / Vanish)
const fogColorB = new THREE.Color(0x1b1e22);                  // teal-leaning fog (Bloom)
const fogColorScratch = new THREE.Color();                    // pre-allocated for per-frame lerp

// Uniforms that the lerp loop will mutate. Bound to needleMat via onBeforeCompile below.
const needleUniforms = {
  uDensity:    { value: 0.30 },
  uColorMix:   { value: 0.0  },
  uColorA:     { value: new THREE.Vector3(colorLavender.r, colorLavender.g, colorLavender.b) },
  uColorB:     { value: new THREE.Vector3(colorTeal.r,     colorTeal.g,     colorTeal.b)     },
  uBandPhase:  { value: 0.0  },
  uBandWidth:  { value: 0.35 },
  uTime:       { value: 0.0  },
};
```

- [ ] **Step 5.2: Attach the onBeforeCompile patch AFTER needleMat is created**

Find `const needleMat = new THREE.MeshStandardMaterial({ ... });` (the existing material block from Task 4). Immediately AFTER its closing `});`, insert:

```js

// Shader patch: add uDensity / uColorMix / uBandPhase / aBand to the standard
// MeshStandardMaterial. We modify diffuseColor BEFORE lighting (so the warm
// shift propagates through bloom) and modulate alpha at the very end (so it
// composes with the normal alpha pipeline).
needleMat.onBeforeCompile = (shader) => {
  Object.assign(shader.uniforms, needleUniforms);

  // VERTEX SHADER: declare aBand attribute, pass through to fragment as vBand.
  shader.vertexShader = shader.vertexShader.replace(
    '#include <common>',
    `#include <common>
attribute float aBand;
varying float vBand;`,
  );
  shader.vertexShader = shader.vertexShader.replace(
    '#include <begin_vertex>',
    `#include <begin_vertex>
vBand = aBand;`,
  );

  // FRAGMENT SHADER: declare uniforms.
  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <common>',
    `#include <common>
uniform float uDensity;
uniform float uColorMix;
uniform vec3  uColorA;
uniform vec3  uColorB;
uniform float uBandPhase;
uniform float uBandWidth;
uniform float uTime;
varying float vBand;`,
  );

  // Color tint: insert right after diffuseColor is initialized from material.color.
  // Inserting here means lighting (which reads diffuseColor.rgb) sees the tinted color,
  // so the warm shift propagates through bloom naturally.
  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <color_fragment>',
    `#include <color_fragment>
{
  vec3 paletteColor = mix(uColorA, uColorB, uColorMix);
  diffuseColor.rgb *= paletteColor;
}`,
  );

  // Alpha modulation: insert at the very tail, just before dithering.
  // aBand-based band visibility + per-instance shimmer + global density multiplier.
  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <dithering_fragment>',
    `#include <dithering_fragment>
{
  float bandDist = abs(vBand - uBandPhase);
  bandDist = min(bandDist, 1.0 - bandDist);          // wrap (uBandPhase loops 0..1)
  float bandVis = 1.0 - smoothstep(0.0, uBandWidth, bandDist);
  float shimmer = 0.9 + 0.1 * sin(uTime * 0.6 + vBand * 40.0);
  gl_FragColor.a *= uDensity * bandVis * shimmer;
}`,
  );
};
```

- [ ] **Step 5.3: Verify shader patch compiles**

Reload. Expected:
- Needles are now MUCH more faded (uDensity=0.30 → 30% opacity, AND only the band near uBandPhase=0.0 is visible AND has a slight shimmer).
- Console clean (no GLSL compile errors). If you see a GLSL error like `'#include <color_fragment>' not found`, you may be on a three version where that include name changed — open `node_modules/three/src/renderers/shaders/ShaderLib/meshphysical.glsl.js` to confirm, but on `three@0.170.0` from the importmap this works.

- [ ] **Step 5.4: Verify uniforms can be modulated**

Change the default values in source to confirm the patch responds:

1. Edit `uDensity: { value: 0.30 }` → `uDensity: { value: 1.0 }`. Reload. Expected: needles much denser/more opaque.
2. Edit `uColorMix: { value: 0.0 }` → `uColorMix: { value: 1.0 }`. Reload. Expected: needles shift toward teal.
3. Edit `uBandPhase: { value: 0.0 }` → `uBandPhase: { value: 0.5 }`. Reload. Expected: a *different subset* of needles is visible (the band has moved).
4. **Revert all three to their original values** (0.30, 0.0, 0.0). The scroll timeline (Task 8) will animate them.

- [ ] **Step 5.5: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat(needle-drift): onBeforeCompile patch for density + color + band-phase uniforms"
```

---

## Task 6: Tune the composer chain to spec §8 values

The composer chain is structurally correct (inherited from minimal.html). We change the *values* to match spec §8: bloom strength 0.65 / radius 0.55 / threshold 0.55, vignette offset 0.5 / darkness 0.55, grain 0.06.

**Files:**
- Modify: `assets/templates/needle-drift.html` — composer block

- [ ] **Step 6.1: Update UnrealBloomPass values**

Find:

```js
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  0.45,    // strength
  0.4,     // radius
  0.82,    // threshold
);
```

Replace with:

```js
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  0.65,    // strength — needles benefit from soft glow on tips
  0.55,    // radius
  0.55,    // threshold — lower so mid-bright needles bloom slightly
);
```

- [ ] **Step 6.2: Update vignette uniforms**

Find the vignette `ShaderPass` definition. Its `uniforms` block currently has:

```js
uniforms: {
  tDiffuse:  { value: null },
  uOffset:   { value: 0.4 },
  uDarkness: { value: 0.55 },
},
```

Change `uOffset` to `0.5` and leave `uDarkness` at `0.55`:

```js
uniforms: {
  tDiffuse:  { value: null },
  uOffset:   { value: 0.5 },
  uDarkness: { value: 0.55 },
},
```

(If the values were different — minimal uses 0.4/0.55 — make them exactly 0.5/0.55. The spec asks for offset 0.5.)

- [ ] **Step 6.3: Update grain intensity**

Find the grain `ShaderPass`. Its uniforms have:

```js
uniforms: {
  tDiffuse:    { value: null },
  uTime:       { value: 0 },
  uIntensity:  { value: 0.05 },
},
```

Change `uIntensity` from `0.05` to `0.06`:

```js
uniforms: {
  tDiffuse:    { value: null },
  uTime:       { value: 0 },
  uIntensity:  { value: 0.06 },
},
```

- [ ] **Step 6.4: Verify**

Reload. Expected:
- Bloom is slightly stronger — needle tips have a small glow.
- Vignette is mild but present at corners.
- Subtle grain on the full image.

- [ ] **Step 6.5: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat(needle-drift): tune composer chain values to dreamlike-fog spec"
```

---

## Task 7: Replace the state object with the needle-drift shape

Spec §7 has a fully specified state object. Replace minimal's state with this verbatim.

**Files:**
- Modify: `assets/templates/needle-drift.html` — the `state` object and any stale `state.heroRotY` / `state.cameraY` references

- [ ] **Step 7.1: Replace the state object**

Find:

```js
const state = {
  cameraY:  { current: 1.2, target: 1.2, ease: 0.06 },
  cameraZ:  { current: 6,   target: 6,   ease: 0.06 },
  heroRotY: { current: 0,   target: 0,   ease: 0.10 },
  mouseX:   { current: 0,   target: 0,   ease: 0.12 },
  mouseY:   { current: 0,   target: 0,   ease: 0.12 },
};
```

Replace with:

```js
const state = {
  cameraZ:     { current: -5,    target: -5,    ease: 0.06 },
  cameraRollZ: { current:  0,    target:  0,    ease: 0.08 },
  uDensity:    { current:  0.30, target:  0.30, ease: 0.08 },
  uColorMix:   { current:  0.0,  target:  0.0,  ease: 0.05 },
  uBandPhase:  { current:  0.0,  target:  0.0,  ease: 0.04 },
  fogDensity:  { current:  0.022, target: 0.022, ease: 0.05 },
  mouseX:      { current:  0,    target:  0,    ease: 0.12 },
  mouseY:      { current:  0,    target:  0,    ease: 0.12 },
};
```

- [ ] **Step 7.2: Verify no stale state-key references**

```powershell
Select-String -Path assets\templates\needle-drift.html -Pattern 'state\.(cameraY|heroRotY)'
```

Expected: zero matches. If any appear, they're in the existing minimal-derived scroll timeline or tick — Tasks 8 and 9 rewrite both, but for now any leftover references would throw. If matches exist, delete the lines that reference them (Task 8 puts in the correct timeline shortly).

- [ ] **Step 7.3: Verify page still loads**

Reload. Expected: same visual as Task 6 (needles in fog, faded). No errors.

- [ ] **Step 7.4: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat(needle-drift): scroll-state object per spec §7"
```

---

## Task 8: Build the GSAP scroll timeline (4-section keyframes)

Replace the minimal-inherited 2-line timeline with the spec §7 timeline. After this task, scrolling visibly changes density + color + camera-z.

**Files:**
- Modify: `assets/templates/needle-drift.html` — the `gsap.timeline({ scrollTrigger: ... })` block

- [ ] **Step 8.1: Replace the scroll timeline**

Find the existing timeline (minimal puts it after the lenis wiring, near the comment `// ── scroll timeline ──`):

```js
gsap.timeline({
  scrollTrigger: {
    trigger: '.scroll-container',
    start: 'top top',
    end: 'bottom bottom',
    scrub: true,
  },
})
.to(state.cameraY,  { target: -1.5, ease: 'none' }, 0)
.to(state.cameraZ,  { target:  4,   ease: 'none' }, 0);
```

(The `.to(state.heroRotY, ...)` should already have been removed in Task 3 — if not, delete it now.)

Replace the whole `gsap.timeline({...}).to(...).to(...);` block with:

```js
// ── scroll timeline ─────────────────────────────────────────────────────
// Single GSAP timeline scrubbed by ScrollTrigger via Lenis. 4 beats:
//   01 Enter   (scroll 0.00 → 0.25)
//   02 Drift   (scroll 0.25 → 0.50)
//   03 Bloom   (scroll 0.50 → 0.75)  — peak
//   04 Vanish  (scroll 0.75 → 1.00)
// Targets `state.*.target`; the lerp loop damps `current` toward `target`,
// giving two-stage smoothing (scrub + lerp) that reads as "buttery".
const tl = gsap.timeline({
  scrollTrigger: {
    trigger: '.scroll-container',
    start: 'top top',
    end: 'bottom bottom',
    scrub: 1.2,
  },
  defaults: { ease: 'none', duration: 1 },
});

// Beat 1 → 2 (Enter → Drift): camera advances, density builds gently
tl.to(state.cameraZ,    { target: 18   }, 0)
  .to(state.uDensity,   { target: 0.55 }, 0)
  .to(state.uColorMix,  { target: 0.20 }, 0)
  .to(state.uBandPhase, { target: 0.25 }, 0)

// Beat 2 → 3 (Drift → Bloom): peak density, full warm shift, subtle roll
  .to(state.cameraZ,    { target: 42   }, 1)
  .to(state.uDensity,   { target: 1.00 }, 1)
  .to(state.uColorMix,  { target: 1.00 }, 1)
  .to(state.uBandPhase, { target: 0.55 }, 1)
  .to(state.cameraRollZ,{ target: 0.04 }, 1)

// Beat 3 → 4 (Bloom → Vanish): density crashes, fog thickens, color returns cool
  .to(state.cameraZ,    { target: 70    }, 2)
  .to(state.uDensity,   { target: 0.10  }, 2)
  .to(state.uColorMix,  { target: 0.0   }, 2)
  .to(state.uBandPhase, { target: 0.95  }, 2)
  .to(state.cameraRollZ,{ target: 0.0   }, 2)
  .to(state.fogDensity, { target: 0.045 }, 2);
```

- [ ] **Step 8.2: Verify**

Reload. Scroll slowly from top to bottom. Expected:
- Camera z position visibly increases (you fly forward through the needle cluster). It should feel like you're entering the scatter.
- Around 50% scroll: needles look densest and color is warmest (teal-leaning).
- At 100% scroll: needles thin out, fog thickens, color returns lavender.
- Camera tilts very slightly around section 3 (the 0.04 radian roll).

If camera dz doesn't change: open DevTools Console and check `state.cameraZ.target` — should not be `-5` at scroll bottom. If it IS -5, the timeline didn't bind — verify the script order and that `.scroll-container` exists in the DOM.

- [ ] **Step 8.3: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat(needle-drift): 4-beat GSAP scroll timeline per spec §7"
```

---

## Task 9: Update the tick loop — push state to uniforms, fog, camera

State is being scrolled, but the tick loop doesn't apply most of it yet. Wire it all.

**Files:**
- Modify: `assets/templates/needle-drift.html` — the `tick()` function and the mousemove handler

- [ ] **Step 9.1: Update the mousemove handler**

Find:

```js
window.addEventListener('mousemove', (e) => {
  state.mouseX.target = (e.clientX / window.innerWidth) * 2 - 1;
  state.mouseY.target = -((e.clientY / window.innerHeight) * 2 - 1);
});
```

Leave it as is — same shape works.

- [ ] **Step 9.2: Replace the tick() function body**

Find:

```js
function tick() {
  if (!running) return;
  const delta = Math.min(clock.getDelta(), 0.1);
  const t = clock.elapsedTime;

  // 1. damp every state
  for (const k in state) damp(state[k], delta);

  // 2. apply state
  camera.position.x = state.mouseX.current * 0.30;
  camera.position.y = state.cameraY.current + state.mouseY.current * 0.20;
  camera.position.z = state.cameraZ.current;
  camera.lookAt(0, 0, 0);

  // 3. update post uniforms
  grainPass.uniforms.uTime.value = t;

  // 4. render
  composer.render();
  rafId = requestAnimationFrame(tick);
}
```

Replace the entire function with:

```js
function tick() {
  if (!running) return;
  const delta = Math.min(clock.getDelta(), 0.1);
  const t = clock.elapsedTime;

  // 1. damp every state
  for (const k in state) damp(state[k], delta);

  // 2. apply state → camera (forward dolly + mouse parallax + subtle roll)
  camera.position.set(0, 0, state.cameraZ.current);
  camera.rotation.set(
    state.mouseY.current * 0.05,    // pitch (mouse Y → pitch up/down)
    state.mouseX.current * 0.05,    // yaw   (mouse X → yaw left/right)
    state.cameraRollZ.current,      // roll  (scroll-driven, peaks at beat 3)
  );

  // 3. apply state → needle uniforms
  needleUniforms.uDensity.value   = state.uDensity.current;
  needleUniforms.uColorMix.value  = state.uColorMix.current;
  needleUniforms.uBandPhase.value = state.uBandPhase.current;
  needleUniforms.uTime.value      = t;

  // 4. apply state → fog (density + color lerped between fogColorA/fogColorB)
  scene.fog.density = state.fogDensity.current;
  fogColorScratch.copy(fogColorA).lerp(fogColorB, state.uColorMix.current);
  scene.fog.color.copy(fogColorScratch);
  scene.background = scene.fog.color;       // background tracks fog so the void blends seamlessly

  // 5. update post uniforms
  grainPass.uniforms.uTime.value = t;

  // 6. render
  composer.render();
  rafId = requestAnimationFrame(tick);
}
```

- [ ] **Step 9.3: Verify the full experience**

Reload. Slowly scroll through all 4 sections. Expected:
- **Enter (0–25%):** sparse needles, cool lavender, slow camera drift
- **Drift (25–50%):** density builds, gentle color warm-shift
- **Bloom (50–75%):** peak density, warmest color (teal-tinted), subtle camera roll, fog visibly tinted
- **Vanish (75–100%):** needles thin out dramatically, fog thickens, returns cool

Move mouse without scrolling — camera should subtly tilt (±0.05 rad). Returns to neutral when mouse leaves the viewport (won't return automatically — that's fine, the lerp eventually settles).

Console should be clean across the whole scroll.

- [ ] **Step 9.4: Commit**

```powershell
git add assets/templates/needle-drift.html
git commit -m "feat(needle-drift): tick loop pushes scroll state to uniforms, fog, camera"
```

---

## Task 10: Visual polish pass

Final tuning round against spec §4 + §8. This task changes nothing structural — it adjusts values to taste based on visual review.

**Files:**
- Modify: `assets/templates/needle-drift.html` — any numeric tuning identified

- [ ] **Step 10.1: Visual review checklist**

Open the page. For each beat below, scroll to roughly the indicated position and verify:

| Beat | Scroll % | Expected look | If not, adjust |
|---|---|---|---|
| Enter | 5% | Sparse needles, mostly fog, low-contrast lavender | If too dark: bump `state.uDensity.current` start to 0.35. If too bright: drop bloom strength to 0.55. |
| Drift | 35% | Medium density, faint warm tint emerging | If color shift isn't visible: bump `state.uColorMix` at beat 1 target from 0.20 to 0.30. |
| Bloom | 60% | Peak density, warm teal tint, slight roll, fog visibly tinted | If overblown bloom: raise UnrealBloomPass threshold from 0.55 to 0.65. |
| Vanish | 95% | Needles nearly gone, fog dense, cool again | If fog isn't thick enough: bump `state.fogDensity` final target from 0.045 to 0.055. |

Make adjustments as needed. Each adjustment is a single-line edit.

- [ ] **Step 10.2: Mouse-parallax amplitude check**

Without scrolling, move the mouse to the four corners of the viewport. Camera should tilt subtly — NOT vertigo-inducing. If too much: reduce both `* 0.05` factors in tick() to `* 0.03`. If too little: bump to `* 0.07`.

- [ ] **Step 10.3: Mobile emulation check**

DevTools → Toggle device toolbar (Ctrl+Shift+M) → Pixel 7. Reload. Look at the Performance Monitor (DevTools → More tools → Performance monitor). Expected: ≥30 FPS during scroll.

If below 30: drop `INSTANCE_COUNT` from 6000 to 3000 — one line edit, single biggest perf lever.

- [ ] **Step 10.4: Commit (if any tuning was applied)**

If you made any changes:

```powershell
git add assets/templates/needle-drift.html
git commit -m "polish(needle-drift): visual tuning pass against spec §4 §8"
```

If no changes were needed, skip the commit and continue.

---

## Task 11: Remove dev artifacts, scan for forbidden patterns

Last cleanliness pass before mirroring + docs.

**Files:**
- Modify: `assets/templates/needle-drift.html` — remove temp probes, dev globals, per-frame logs

- [ ] **Step 11.1: Scan for forbidden patterns**

Run all three checks:

```powershell
# 1. No console.log anywhere (per SKILL.md hard rule #6)
Select-String -Path assets\templates\needle-drift.html -Pattern 'console\.log'
```

Expected: zero matches. The `[awwwards-3d]` console.error in the error handlers is fine — that's only an error path.

```powershell
# 2. No window.__ dev globals (temporary debug helpers)
Select-String -Path assets\templates\needle-drift.html -Pattern 'window\.__'
```

Expected: ONE match — `window.__awwwards3d_destroy` (the cleanup function inherited from minimal). That's intentional. Anything else (like `window.__needleUniforms`) must be removed.

```powershell
# 3. No TODO/FIXME/XXX (in case any debug notes leaked in)
Select-String -Path assets\templates\needle-drift.html -Pattern '(TODO|FIXME|XXX):'
```

Expected: zero matches.

- [ ] **Step 11.2: Verify __awwwards3d_destroy still works**

Open DevTools console on the page. Run:

```js
window.__awwwards3d_destroy()
```

The scene should freeze (rAF cancelled, lenis destroyed). Reload the page after testing.

- [ ] **Step 11.3: Sanity check line count**

```powershell
(Get-Content assets\templates\needle-drift.html).Length
```

Expected: 580–680 lines. Existing siblings are 499–576; needle-drift is slightly larger due to the shader patch and scatter loop. If significantly above 700: review for accidental duplication.

- [ ] **Step 11.4: Commit (if anything was removed)**

```powershell
git add assets/templates/needle-drift.html
git commit -m "chore(needle-drift): remove dev probes and unused references"
```

If no changes: skip the commit, continue.

---

## Task 12: Mirror to docs/templates/

The `docs/` folder is the GitHub Pages publish root. It mirrors `assets/templates/` (without the `models/` and `hdri/`). One file copy.

**Files:**
- Create: `docs/templates/needle-drift.html` (exact copy of `assets/templates/needle-drift.html`)

- [ ] **Step 12.1: Copy the file**

```powershell
Copy-Item assets\templates\needle-drift.html docs\templates\needle-drift.html
```

- [ ] **Step 12.2: Verify the two files are identical**

```powershell
git diff --no-index --stat assets\templates\needle-drift.html docs\templates\needle-drift.html
```

Expected: `0 files changed` (or no output — git treats identical files as no diff).

Cross-check the mirror is reachable. Since the server serves from `assets/`, the docs copy isn't served by *this* server. Verify with a file diff instead:

```powershell
Compare-Object (Get-Content assets\templates\needle-drift.html) (Get-Content docs\templates\needle-drift.html)
```

Expected: no output (no diff).

- [ ] **Step 12.3: Commit**

```powershell
git add docs/templates/needle-drift.html
git commit -m "docs: mirror needle-drift template to docs/ for GitHub Pages"
```

---

## Task 13: Update README.md (template table row + file-tree entry)

Two surgical edits. Open `README.md` in an editor.

**Files:**
- Modify: `README.md`

- [ ] **Step 13.1: Add row to the template table**

Find the `<table>` near the top of the README (after "## The four templates"). It contains four `<tr>` rows. The HTML structure (from inspection of `README.md` lines ~9–26):

```html
<table>
<tr>
<td width="50%"><b>minimal.html</b>...</td>
<td width="50%"><b>coin-scroll.html</b>...</td>
</tr>
<tr>
<td><img src="docs/screenshots/minimal-hero.png" alt="minimal.html"></td>
<td><img src="docs/screenshots/coin-hero.png" alt="coin-scroll.html"></td>
</tr>
<tr>
<td><b>room-walkthrough.html</b>...</td>
<td><b>glass-product.html</b>...</td>
</tr>
<tr>
<td><img src="docs/screenshots/room-hero.png" alt="room-walkthrough.html"></td>
<td><img src="docs/screenshots/glass-hero.png" alt="glass-product.html"></td>
</tr>
</table>
```

Immediately AFTER the closing `</table>` of the existing 4-template table, add:

```html

<table>
<tr>
<td width="50%"><b>needle-drift.html</b><br><sub>Tunnel archetype — ~6000 instanced needles in a dreamlike lavender/teal fog. Density + color breathe across 4 scroll beats (Enter / Drift / Bloom / Vanish). Pure procedural — no GLB.</sub></td>
<td width="50%"></td>
</tr>
<tr>
<td><img src="docs/screenshots/needle-drift-hero.png" alt="needle-drift.html"></td>
<td></td>
</tr>
</table>
```

(The empty right column is intentional — when a 6th template is added later, the row fills up. The screenshot file doesn't exist yet; it's left as a follow-up TODO. GitHub will render a broken-image icon until then — acceptable.)

Then update the heading just before that block. Find:

```markdown
## The four templates
```

Replace with:

```markdown
## The five templates
```

- [ ] **Step 13.2: Update the file tree under "What's inside"**

Find this block in README.md (currently lists 4 templates):

```
│   ├── templates/
│   │   ├── minimal.html           Foundation — empty scene with full polish chain
│   │   ├── coin-scroll.html       Gold coin tumbles + falls on scroll (loads coin.glb)
│   │   ├── room-walkthrough.html  Camera follows spline through a low-poly interior
│   │   └── glass-product.html     Hero orb with MeshPhysicalMaterial transmission
```

Add a 5th line. The tree-art uses `└──` for the last entry; move it down. New version:

```
│   ├── templates/
│   │   ├── minimal.html           Foundation — empty scene with full polish chain
│   │   ├── coin-scroll.html       Gold coin tumbles + falls on scroll (loads coin.glb)
│   │   ├── room-walkthrough.html  Camera follows spline through a low-poly interior
│   │   ├── glass-product.html     Hero orb with MeshPhysicalMaterial transmission
│   │   └── needle-drift.html      Tunnel — ~6000 instanced needles in dreamlike fog (no GLB)
```

- [ ] **Step 13.3: Verify**

```powershell
# Headings present
Select-String -Path README.md -Pattern 'The five templates'
# Template tree entry
Select-String -Path README.md -Pattern 'needle-drift\.html'
```

First match: exactly one. Second match: at least two (table row + tree entry).

- [ ] **Step 13.4: Commit**

```powershell
git add README.md
git commit -m "docs: add needle-drift to README template table and file tree"
```

---

## Task 14: Update SKILL.md Step 3 template list

One-line addition under "Step 3 — Pick a Template" in SKILL.md.

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 14.1: Add the needle-drift entry**

Find this block in SKILL.md (around line 87–94 — under "### Step 3 — Pick a Template"):

```markdown
Start from `assets/templates/`:

- `minimal.html` — empty scene with HDRI, tone mapping, Lenis, post-processing wired up. Use as the foundation for anything custom.
- `coin-scroll.html` — coin rotates and falls on scroll (object showcase).
- `room-walkthrough.html` — camera moves along a spline through a room (room walkthrough).
- `glass-product.html` — single product with `MeshPhysicalMaterial` transmission + dispersion (r166+), HDRI, gentle bloom (object showcase, glass).

Templates are starting points, not final work. Strip what you don't need, layer what you do.
```

Add a 5th bullet between `glass-product.html` and the closing paragraph:

```markdown
Start from `assets/templates/`:

- `minimal.html` — empty scene with HDRI, tone mapping, Lenis, post-processing wired up. Use as the foundation for anything custom.
- `coin-scroll.html` — coin rotates and falls on scroll (object showcase).
- `room-walkthrough.html` — camera moves along a spline through a room (room walkthrough).
- `glass-product.html` — single product with `MeshPhysicalMaterial` transmission + dispersion (r166+), HDRI, gentle bloom (object showcase, glass).
- `needle-drift.html` — ~6000 instanced needles scattered through dreamlike fog; density + color breathe across 4 scroll beats (tunnel archetype, pure procedural).

Templates are starting points, not final work. Strip what you don't need, layer what you do.
```

- [ ] **Step 14.2: Verify**

```powershell
Select-String -Path SKILL.md -Pattern 'needle-drift'
```

Expected: exactly one match (the new bullet).

- [ ] **Step 14.3: Commit**

```powershell
git add SKILL.md
git commit -m "docs: add needle-drift to SKILL.md Step 3 template list"
```

---

## Task 15: Final regression + acceptance pass

No code changes — verification only. This is the spec §11 + §14 acceptance check.

- [ ] **Step 15.1: All 5 templates load**

For each URL, open in a fresh tab, confirm preloader hides, confirm no console errors:

```
http://localhost:8766/templates/minimal.html
http://localhost:8766/templates/coin-scroll.html
http://localhost:8766/templates/room-walkthrough.html
http://localhost:8766/templates/glass-product.html
http://localhost:8766/templates/needle-drift.html
```

- [ ] **Step 15.2: Needle-drift scroll-arc visual check**

Open needle-drift.html. Slowly scroll top → bottom. Verify all 4 beats from Task 9.3 are distinct (Enter sparse cool, Drift building, Bloom peak warm, Vanish thinning cool).

- [ ] **Step 15.3: Determinism check**

Hard-reload needle-drift.html three times. The needle positions in your view should be identical each time (the scatter is seeded).

- [ ] **Step 15.4: Mobile emulation FPS**

DevTools → Pixel 7 emulation → Performance Monitor → scroll through the page. Expected ≥30 FPS sustained.

If below: drop `INSTANCE_COUNT` to 3000 in `assets/templates/needle-drift.html` (also mirror that change to `docs/templates/needle-drift.html`), commit:

```powershell
git add assets/templates/needle-drift.html docs/templates/needle-drift.html
git commit -m "perf(needle-drift): halve instance count to maintain 30fps on mid-tier mobile"
```

- [ ] **Step 15.5: No-regression check on existing templates**

For each of the 4 pre-existing templates, scroll top → bottom once. Confirm no visual or console regression. (No file in those templates was touched, but the README/SKILL.md changes could theoretically introduce a markdown link error — check the README on GitHub once pushed.)

- [ ] **Step 15.6: Final git log review**

```powershell
git log --oneline -15
```

Expected to see (in some order, working back from HEAD):
1. `docs: add needle-drift to SKILL.md Step 3 template list`
2. `docs: add needle-drift to README template table and file tree`
3. `docs: mirror needle-drift template to docs/ for GitHub Pages`
4. (optional) `chore(needle-drift): remove dev probes and unused references`
5. (optional) `polish(needle-drift): visual tuning pass against spec §4 §8`
6. `feat(needle-drift): tick loop pushes scroll state to uniforms, fog, camera`
7. `feat(needle-drift): 4-beat GSAP scroll timeline per spec §7`
8. `feat(needle-drift): scroll-state object per spec §7`
9. `feat(needle-drift): tune composer chain values to dreamlike-fog spec`
10. `feat(needle-drift): onBeforeCompile patch for density + color + band-phase uniforms`
11. `feat(needle-drift): 6000 instanced needles, deterministic scatter, edge falloff`
12. `feat(needle-drift): strip placeholder hero, fog-only scene with tunnel lighting`
13. `feat(needle-drift): scene background + FogExp2 + tunnel camera framing`
14. `feat: scaffold needle-drift template (identity only, scene still placeholder)`
15. (existing) `docs: add needle-drift template design spec`

12–14 task commits + 1 spec commit. If a critical step is missing a commit, recover with a focused commit at this point — do NOT amend earlier work.

- [ ] **Step 15.7: Acceptance checklist (spec §14)**

Confirm all of:

- [ ] `assets/templates/needle-drift.html` runs cleanly served from `python -m http.server`
- [ ] All 4 scroll beats are visually distinct
- [ ] No console errors in Chrome desktop
- [ ] No console errors in Chrome mobile emulation
- [ ] FPS ≥ 30 in Pixel 7 emulation
- [ ] `docs/templates/needle-drift.html` is identical to `assets/templates/needle-drift.html`
- [ ] `README.md` has a needle-drift row + tree entry
- [ ] `SKILL.md` Step 3 lists needle-drift
- [ ] All 4 pre-existing templates load and run unchanged
- [ ] No `console.log` in the tick loop
- [ ] Code matches spec §6 (shader patch) and §7 (timeline)

If ALL of the above are checked: the template is **done**. The screenshot (`docs/screenshots/needle-drift-hero.png`) remains as documented follow-up — out of scope for this plan per spec §9.

---

## Out-of-scope (deferred follow-ups)

- `docs/screenshots/needle-drift-hero.png` capture (manual or via e2e-runner)
- Adding the `onBeforeCompile` patch as a reusable snippet in `references/PATTERNS.md`
- Mobile-specific quality-tier auto-detection (manual `INSTANCE_COUNT` halving in Task 15.4 is the manual workaround)
- Audio layer (spec §2 non-goal)

---

*End of plan.*
