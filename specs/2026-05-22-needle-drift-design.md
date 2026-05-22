# needle-drift.html — Design Spec

**Date:** 2026-05-22
**Author:** brainstorming session
**Status:** Approved — ready for implementation plan
**Target file:** `assets/templates/needle-drift.html` (mirrored to `docs/templates/needle-drift.html`)

---

## 1. Summary

A 5th template for the `awwwards-3d` skill, filling the **Tunnel** archetype gap from `SKILL.md` Step 1 (the existing 4 templates cover only Object Showcase and Room Walkthrough).

The template renders a scroll-driven flight through a fog-saturated cloud of ~6,000 thin needles arranged in a random-scatter cylindrical volume. Density and palette **breathe** across a 4-section scroll arc (Enter → Drift → Bloom → Vanish), peaking in section 3. The aesthetic target is **dreamlike Resn fog** — desaturated lavender ↔ dusty teal, low contrast, soft volumetric haze, bloom catching needle tips through the mist.

Stack is the project's locked: `three@0.170.0` + `gsap@3.12.5` (ScrollTrigger) + `lenis@1.1.0` + three's built-in `EffectComposer`. Deliverable is a single `.html` file, ESM via importmap, no build step, no new GLB asset.

---

## 2. Goals & Non-Goals

### Goals

- Fill the **Tunnel** archetype slot in the skill's template set
- Demonstrate **InstancedMesh at scale** (~6k instances, single draw call) — currently no template demos this
- Demonstrate **`onBeforeCompile` shader patching** with custom uniforms + per-instance attributes — a pattern not shown in existing templates
- Demonstrate **fog as a first-class atmospheric tool** (color shift via uniform-bound fog color)
- Stay within the project's conventions: single-file, importmap, ~500-line ceiling, same typography/preloader/error-handling shape as existing templates
- 60fps desktop, 30fps mid-tier Android

### Non-Goals

- **No new GLB asset.** Pure procedural geometry. `assets/models/` is not modified.
- **No new external dependency.** Importmap stays identical to existing templates.
- **No audio.** Audio is optional per SKILL.md; deferring keeps the template focused.
- **No drei / postprocessing library.** Three's built-in passes only, per SKILL.md hard constraint.
- **No screenshot generation in this spec.** Hero PNG capture is left as a follow-up TODO (handled by `e2e-runner` or manual).

---

## 3. Decisions Log

Each decision below was settled in the brainstorming session before this spec was written.

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Which uncovered archetype | **Tunnel** | User selection from the 4 missing archetypes. |
| 2 | Tunnel form | **Strut forest** | User selection — Active Theory experiments territory. |
| 3 | Strut arrangement | **Random scatter** (organic, cave-like, with edge-density falloff) | User selection. Pairs naturally with atmospheric fog. |
| 4 | Palette / mood | **Dreamlike fog** — lavender ↔ dusty teal | Most distinct from the existing 4 templates' palettes. Fog hides scatter repetition. |
| 5 | Per-strut shape | **Thin needles** (`BoxGeometry(0.02, 1.5, 0.02)`) | Cheapest at high count. Reads cleanest as 'particles in volume'. Catches bloom on tips. |
| 6 | Scroll modulation | **Density pulse + color shift** | Most cinematic; maps cleanly to a GSAP timeline. Lowest implementation risk. |
| 7 | Section arc | **4 sections, build-to-peak** (Enter / Drift / Bloom / Vanish) | Matches existing template length. Clean place for hero beat in section 3. |
| 8 | Filename | `needle-drift.html` | Descriptive; sibling-named to `coin-scroll.html`, `room-walkthrough.html`, `glass-product.html`. |
| 9 | Spec location | `specs/` at project root (not `docs/superpowers/specs/`) | `docs/` is the GitHub Pages publish root; spec must not leak to deployed site. |

---

## 4. Visual Specification

### Palette (sRGB, will be converted to linear by three on assign)

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#16121d` | Body, scene clear color, near-fog tint |
| `--fg` | `#d8d3e8` | Typography (muted off-white) |
| `--lavender` | `#9d93c4` | Cool palette pole, also fog tint at Enter/Vanish |
| `--teal` | `#7faaa6` | Warm palette pole, fog tint at Bloom |
| `--needle-base` | `#c8c0e4` | Needle MeshStandardMaterial base color (lavender-leaning) |
| `--accent` | `#e8d8c2` | Section meta labels (warm grey, low opacity) |

All palette colors are mid-saturation, low contrast. **Avoid pure white / pure black** — flat saturation kills the dreamlike read.

### Typography

Reuse coin-scroll's system stack and clamp scales verbatim:

```css
font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
section h1, section h2 {
  font-weight: 600;
  font-size: clamp(2rem, 6vw, 5rem);
  line-height: 0.95;
  letter-spacing: -0.04em;
  max-width: 18ch;
}
```

### Section copy (typographic placeholder, intentionally atmospheric)

| # | Meta | Headline |
|---|---|---|
| 01 | `01 — Enter` | `Step into the haze` |
| 02 | `02 — Drift` | `Let it carry you` |
| 03 | `03 — Bloom` | `Everything brightens at once` |
| 04 | `04 — Vanish` | `And softly thins to nothing` |

Title: `<title>Awwwards 3D — needle drift</title>`.
Favicon: 16×16 SVG circle, lavender (`#9d93c4`).

---

## 5. Scene Composition

### Structure

```
scene
├── lighting (Group)
│   ├── DirectionalLight (key, lavender-tinted, intensity 0.6) — soft grade
│   └── DirectionalLight (rim, cool white, intensity 0.4, from -z)
├── stage (Group)
│   └── needleField (InstancedMesh) — the hero
└── (scene.environment from RoomEnvironment, intensity 0.3)
```

No floor mesh. No shadow catcher. No GLB. Fog (`FogExp2`) is the entire background.

### Needle field — parameters

| Param | Value | Note |
|---|---|---|
| Geometry | `BoxGeometry(0.02, 1.5, 0.02)` | 8 verts. Trivial cost. |
| Material | `MeshStandardMaterial({ color: '#c8c0e4', roughness: 0.55, metalness: 0.0, transparent: true })` | Patched via `onBeforeCompile` (see §6). `transparent:true` enables alpha modulation. |
| Instance count | **6000** | Tested sweet spot; lower if mobile FPS dips. |
| Volume | Cylinder along +z, **radius 3.5**, **length 80**, centered at z=40 (so camera at z=0 sees the volume ahead) | |
| Position seed | Deterministic — see distribution algorithm below | Same seed every load. |
| Rotation | Random Euler per instance | Locked at init. |
| Scale variance | per-axis-Y multiplier in `[0.7, 1.3]` | Length variance; XZ thickness stays fixed. |
| `aBand` attribute | Float in `[0, 1)` per instance — assigned monotonically as `i / INSTANCE_COUNT` at init | Used by shader to stagger fade-in / fade-out across the scroll arc. Monotonic is intentional: since instance positions are already randomly scattered in xyz, sweeping band-phase reveals instances in spatially-random order, giving the breathing effect for free. |

### Distribution algorithm (random scatter with edge falloff)

```
for i in 0..6000:
  r = TUBE_RADIUS * sqrt(rand())^1.4    // ^1.4 biases toward edges-thinning
  theta = rand() * 2*PI
  z = lerp(0, TUBE_LENGTH, rand())
  pos = (r*cos(theta), r*sin(theta) * Y_SQUASH, z)
  // Y_SQUASH = 0.7 — slight vertical flattening reads as 'horizon-friendly'
  rot = (rand()*PI, rand()*PI, rand()*PI)
  scaleY = lerp(0.7, 1.3, rand())
  aBand = i / 6000   // monotonic; shader uses this for staggered fade
```

Use a tiny deterministic PRNG (e.g. mulberry32 seeded at `0xDEAD`) so the scatter is reproducible across reloads. **Do not use `Math.random()` directly** — non-deterministic = harder to art-direct.

### Camera

- `PerspectiveCamera(40, aspect, 0.1, 120)` — slightly wider FOV than coin-scroll (32) to enhance tunnel depth perception
- Starts at `(0, 0, -5)` looking down +z
- Scroll drives `camera.position.z` from `-5` to `+85` (the camera *enters* the volume and exits the far end)
- Mouse parallax: ±0.05 on `camera.rotation.x` (pitch) and `camera.rotation.y` (yaw), lerped via `damp()` with `ease: 0.12`
- Section 3 ("Bloom") adds a subtle scroll-progress-driven `camera.rotation.z` roll, max ±0.04 radians

### Fog

- `scene.fog = new THREE.FogExp2(<dynamic color>, 0.022)`
- Density holds at 0.022 except in section 4 where it climbs to 0.045 (the "vanish thickens")
- Color is uniform-bound — see §6 timeline

---

## 6. Shader Patch (the technical core)

Standard `MeshStandardMaterial` patched via `onBeforeCompile`. Adds:

### New uniforms

| Uniform | Type | Default | Purpose |
|---|---|---|---|
| `uDensity` | float | 0.30 | Global alpha multiplier (0..1) — scroll-driven |
| `uColorMix` | float | 0.0 | Lerp factor between `uColorA` and `uColorB` — scroll-driven |
| `uColorA` | vec3 | lavender (`#9d93c4` linear) | Cool palette pole |
| `uColorB` | vec3 | dusty teal (`#7faaa6` linear) | Warm palette pole |
| `uBandPhase` | float | 0.0 | Scrolls through `[0,1]` — controls *which* instances are currently faded in |
| `uBandWidth` | float | 0.35 | Width of the active band — wider = more instances visible at once |
| `uTime` | float | 0.0 | Animation clock; tiny per-needle alpha shimmer |

### New per-instance attribute

`aBand` (float, one per instance) — assigned at init, range `[0, 1)`.

### Patch logic (pseudo-GLSL)

```glsl
// In vertex shader — pass aBand to fragment
attribute float aBand;
varying float vBand;
// ... existing code ...
vBand = aBand;

// In fragment shader — modulate diffuse color + alpha
varying float vBand;
// ... existing diffuse computation up to gl_FragColor ...

// Color mix between palette poles
vec3 paletteColor = mix(uColorA, uColorB, uColorMix);
diffuseColor.rgb *= paletteColor;

// Band visibility: instances whose aBand is near uBandPhase are visible
float bandDist = abs(vBand - uBandPhase);
bandDist = min(bandDist, 1.0 - bandDist);   // wrap (uBandPhase loops 0..1)
float bandVis = 1.0 - smoothstep(0.0, uBandWidth, bandDist);

// Tiny temporal shimmer so still frames don't feel dead
float shimmer = 0.9 + 0.1 * sin(uTime * 0.6 + vBand * 40.0);

gl_FragColor.a *= uDensity * bandVis * shimmer;
```

### Why this approach

- **One material, one draw call.** No per-instance material switching.
- **No full custom shader.** Reuses three's PBR lighting (so the needles still respond to the directional lights and env).
- **Per-instance staggered fade** via `aBand` + `uBandPhase` gives the "breathing density" effect without computing 6000 individual alpha targets on CPU.
- **Patch is reviewable.** ~20 lines of GLSL appended via standard string replacement on `material.onBeforeCompile`.

---

## 7. Scroll Choreography

### Lenis + ScrollTrigger wiring

Identical to coin-scroll.html (see lines 371-379 of that file). Lenis owns scroll; `lenis.on('scroll', ScrollTrigger.update)`; `gsap.ticker.add((t) => lenis.raf(t * 1000))`; `gsap.ticker.lagSmoothing(0)`.

### DOM

```html
<main class="scroll-container">
  <section><span class="meta">01 — Enter</span><h1>Step into the haze</h1></section>
  <section><span class="meta">02 — Drift</span><h2>Let it carry you</h2></section>
  <section><span class="meta">03 — Bloom</span><h2>Everything brightens at once</h2></section>
  <section><span class="meta">04 — Vanish</span><h2>And softly thins to nothing</h2></section>
</main>
```

Each `section { height: 100vh }` per coin-scroll convention. Total scroll = 400vh.

### Single GSAP timeline, scrubbed by one ScrollTrigger

```js
const tl = gsap.timeline({
  scrollTrigger: {
    trigger: '.scroll-container',
    start: 'top top',
    end: 'bottom bottom',
    scrub: 1.2,     // matches coin-scroll smoothness
  },
});

// State targets that the lerp loop will damp toward.
// (We target state.* not the live values, so motion stays buttery.)

tl.to(state.cameraZ,    { target: 18,  duration: 1 }, 0)     // Enter → Drift
  .to(state.uDensity,   { target: 0.55, duration: 1 }, 0)
  .to(state.uColorMix,  { target: 0.20, duration: 1 }, 0)
  .to(state.uBandPhase, { target: 0.25, duration: 1 }, 0)

  .to(state.cameraZ,    { target: 42,  duration: 1 }, 1)     // Drift → Bloom
  .to(state.uDensity,   { target: 1.00, duration: 1 }, 1)
  .to(state.uColorMix,  { target: 1.00, duration: 1 }, 1)
  .to(state.uBandPhase, { target: 0.55, duration: 1 }, 1)
  .to(state.cameraRollZ,{ target: 0.04, duration: 1 }, 1)    // peak roll

  .to(state.cameraZ,    { target: 70,  duration: 1 }, 2)     // Bloom → Vanish
  .to(state.uDensity,   { target: 0.10, duration: 1 }, 2)
  .to(state.uColorMix,  { target: 0.00, duration: 1 }, 2)
  .to(state.uBandPhase, { target: 0.95, duration: 1 }, 2)
  .to(state.cameraRollZ,{ target: 0.0,  duration: 1 }, 2)
  .to(state.fogDensity, { target: 0.045, duration: 1 }, 2);  // fog thickens
```

### State object shape

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

`damp(s, dt)` is the framerate-independent formula already used by coin-scroll (lines 365-368) — copy verbatim.

### Tick loop (per-frame)

1. `damp()` every state slot
2. Apply `state.cameraZ.current` → `camera.position.z`
3. Apply mouse parallax → `camera.rotation.{x,y}`
4. Apply `state.cameraRollZ.current` → `camera.rotation.z`
5. Push uniform updates: `material.uniforms.uDensity.value = state.uDensity.current` (etc.)
6. Update fog: `scene.fog.density = state.fogDensity.current; scene.fog.color = lerp(lavender, teal, state.uColorMix.current)`
7. Advance `uTime.value += delta`
8. `grainPass.uniforms.uTime.value = clock.elapsed`
9. `composer.render()`

---

## 8. Polish Chain (per SKILL.md Step 4)

| Layer | Setting | Note |
|---|---|---|
| Environment | `RoomEnvironment` via PMREM, intensity 0.3 | No HDRI fetch — needles don't need strong reflections; faster initial paint |
| Tone mapping | `ACESFilmicToneMapping`, exposure **0.95** | Slightly under coin's 1.05 — fog scenes look better slightly underexposed |
| Color space | `SRGBColorSpace` output | Mandatory |
| Lighting | 1× DirectionalLight (key, lavender `#cab8e8`, intensity 0.6, from +y/+x) + 1× DirectionalLight (rim, cool white, intensity 0.4, from -z) | No shadow casting |
| Shadow map | **Disabled** | Fog hides shadows; saves a pass |
| Composer target | `WebGLRenderTarget` with `HalfFloatType` | HDR target, same as coin-scroll line 296 |
| RenderPass | scene + camera | |
| UnrealBloomPass | strength **0.65**, radius **0.55**, threshold **0.55** | Higher strength than coin (0.55) — needles benefit from soft glow on tips. Lower threshold so mid-bright needles bloom slightly. |
| Vignette ShaderPass | offset 0.5, darkness 0.55 | Slightly less dark than coin (0.6) — preserves fog depth |
| OutputPass | applies tone mapping | |
| Grain ShaderPass | intensity **0.06** | Slightly heavier than coin (0.045) — grain reinforces the dreamlike read |

All shader passes are inline, same shape as coin-scroll.html lines 312-353. Do not extract to a shared file — that would break the single-file deliverable contract.

---

## 9. File Structure & Deliverables

### Files created

| Path | Purpose |
|---|---|
| `assets/templates/needle-drift.html` | The template itself (~500 lines) |
| `docs/templates/needle-drift.html` | Mirror for GitHub Pages publish |

### Files modified

| Path | Change |
|---|---|
| `README.md` | Add row to template table (with screenshot reference); update file tree under "What's inside" |
| `SKILL.md` | Add `needle-drift.html` to Step 3 template list with one-line description; expand any reference to "the four templates" → "the five templates" |
| `docs/index.html` | Add link to needle-drift in the GitHub Pages landing list (verify pattern first — read the file before editing) |

### Files NOT modified

- `assets/models/*` — no new GLB
- `references/*.md` — patterns are unchanged; no new pattern is introduced (the `onBeforeCompile` patch could be added to PATTERNS.md as a follow-up but it's out of scope for this spec)
- `scripts/*` — init scripts don't reference templates by name
- `LICENSE`, `.gitignore` — untouched

### Screenshot

`docs/screenshots/needle-drift-hero.png` — left as **TODO**. To be captured after the implementation lands by running the served template, navigating to the Bloom section (~50% scroll), and capturing the viewport. Either manual or via `e2e-runner` agent in a follow-up task.

---

## 10. Performance Budget

| Metric | Target | Notes |
|---|---|---|
| FCP | < 1.8s | Single HTML, ESM imports — measured on desktop chrome over loopback |
| LCP | < 2.5s | Preloader hides until needle field is ready |
| Desktop FPS | 60 sustained | 6000 instances × 8 verts = 48k verts is trivial |
| Mid-tier Android FPS | 30 minimum | If below, halve instance count to 3000 (single-line constant) |
| Draw calls | ≤ 8 | 1 needles + ~4 composer passes + 1 lighting helpers (if any) |
| `pixelRatio` | `Math.min(devicePixelRatio, 2)` | Mandatory per SKILL.md hard rule #3 |
| Bundle / HTML size | < 80kb (no compression) | Inline CSS+JS, no embedded assets |

### Mobile downgrade switches (deferred — implement if FPS budget fails)

- Halve `INSTANCE_COUNT` to 3000
- Drop `UnrealBloomPass` (single biggest cost)
- Drop grain pass
- Cap fog density adjustment so the alpha-fog overlap doesn't double-cost fragments

---

## 11. Test Plan

### Local verification (manual, against the existing `python -m http.server 8766` on `assets/`)

- [ ] Open `http://localhost:8766/templates/needle-drift.html` — page loads, preloader hides
- [ ] No console errors at idle
- [ ] Scrolling through all 4 sections shows density + color modulation
- [ ] Camera reaches z≈70 at scroll end (verify with `console.log(camera.position.z)` removed before commit)
- [ ] Mouse parallax visible but subtle
- [ ] Bloom is present but not blown out
- [ ] Resize window: no scene break, no console error
- [ ] `lighthouse` against the page: Performance ≥ 85 desktop
- [ ] DevTools mobile emulation (Pixel 7 / mid-tier Android): FPS ≥ 30

### Cross-browser (per `web/testing.md`)

- [ ] Chrome 120+ (primary)
- [ ] Firefox 130+ (verify ShaderPass shader compiles — known historical Firefox quirks)
- [ ] Safari 17+ (verify fog color updates apply — Safari can lag on uniform pushes)

### Regression check against existing templates

- [ ] All 4 existing templates still load and run (the new template must not modify shared files in a way that breaks them — confirm by re-loading each)

### Determinism

- [ ] Reload the page — needle positions identical across reloads (seeded PRNG)

---

## 12. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Transparent InstancedMesh causes Z-fighting / order issues | Medium | Set `material.depthWrite = false` AND `transparent: true`. Test in Bloom section where density is highest. Acceptable if a small amount of soft overlap is visible — that *is* the dreamlike read. |
| `onBeforeCompile` patch breaks on r170 minor diff | Low | The patch only uses well-documented insertion points (`#include <output_fragment>` adjacent). Same technique used in three.js examples. |
| 6000 instances × `transparent: true` blows mobile fill rate | Medium | Already documented mobile downgrade (halve count). Worst case: drop to opaque + cutout (`alphaTest`) — simpler but kills the soft fade. |
| Fog color uniform binding via `scene.fog.color.lerpColors(...)` allocates per frame | Low | Use two pre-allocated `THREE.Color` instances, `lerp` in place to a third pre-allocated instance — same pattern as coin-scroll's lerp loop. |
| Bloom + transparent fog combo over-blooms in section 3 | Medium | Threshold tuning. If Bloom section reads "blown", raise threshold from 0.55 → 0.65 and re-test. |
| `aBand` instance attribute not propagated to fragment shader | Low | Use `flat varying` if interpolation is unnecessary; otherwise standard `varying float` — interpolated across the box's 8 verts is fine for a thin needle. |

### Out-of-scope (deferred to follow-up issues if desired)

- Screenshot capture for README hero table
- Adding the `onBeforeCompile` patch as a reusable snippet in `references/PATTERNS.md`
- Mobile-specific quality tier auto-detection
- Audio layer (deferred per §2 non-goals)

---

## 13. Implementation Order (preview for writing-plans)

A concrete build sequence the implementation plan will expand:

1. Scaffold the file from `minimal.html` (already has preloader, importmap, error handlers, lerp loop) — strip what minimal does that needle-drift doesn't need
2. Replace the hero geometry with InstancedMesh + 6000 procedural positions (no shader patch yet — just verify scatter looks right with solid color)
3. Apply the `onBeforeCompile` patch — verify uniforms update in DevTools, alpha modulation works
4. Wire fog color + density to state lerp
5. Build the GSAP timeline with placeholder values, scrub through it manually to validate visual beats
6. Tune palette, bloom, grain, vignette to match the spec
7. Add 4 sections of typographic copy, verify they layer correctly above the canvas
8. Mirror to `docs/templates/`, update `README.md` and `SKILL.md`
9. Test pass per §11
10. Capture screenshot, commit

---

## 14. Acceptance Criteria

This template is **done** when:

- [ ] `assets/templates/needle-drift.html` runs cleanly served from `python -m http.server`
- [ ] All 4 scroll beats (Enter / Drift / Bloom / Vanish) are visually distinct
- [ ] No console errors in Chrome desktop or Chrome mobile emulation
- [ ] FPS budget met (60 desktop, 30 Android emulation)
- [ ] `docs/templates/needle-drift.html` is identical to the assets copy
- [ ] `README.md` template table has a needle-drift row
- [ ] `SKILL.md` Step 3 lists needle-drift with a one-line description
- [ ] Existing 4 templates still load and run unchanged (regression check)
- [ ] Code is reviewable: no commented-out blocks, no `console.log` inside the tick loop
- [ ] Spec-to-code traceability: the implementation matches §6 (shader patch) and §7 (timeline) — not improvised

---

*End of spec.*
