# ARCHITECTURE — Scene Structure, Lerp Loop, Scroll Loop, Render Order

This is the spine of every Awwwards 3D site. If you understand and apply the four sections below correctly, the rest is decoration. If you skip them, no amount of post-processing will save the result.

---

## 1. Scene Graph

The scene graph is **organized into named groups**, never a flat dump of meshes into `scene.add()`. Names matter — they let you `scene.getObjectByName()` later instead of holding refs.

### Canonical layout

```
scene
├── lighting             (Group, name: "lighting")
│   ├── hemi             (HemisphereLight, fallback before HDRI loads)
│   ├── key              (DirectionalLight, the shadow caster)
│   └── fill             (DirectionalLight, opposite side, intensity 0.3)
├── stage                (Group, name: "stage")  ← all hero content goes here
│   ├── hero             (the main 3D object/scene)
│   ├── particles        (Points, optional)
│   └── floor            (optional ground plane / shadow catcher)
├── helpers              (Group, name: "helpers", visible = DEBUG)
│   ├── axesHelper
│   └── gridHelper
└── camera               (PerspectiveCamera, attached to scene only if it has children)
```

### Why groups, not flat

1. You can `stage.rotation.y += delta * 0.05` to slowly rotate everything cinematically without touching individual objects.
2. You can hide debug helpers with one toggle: `helpers.visible = false`.
3. `scene.environment = hdriTexture` applies to materials in any group automatically.
4. Cleanup is a one-liner: `dispose(stage)` instead of remembering every mesh.

### HDRI environment, not background

```js
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

const pmrem = new THREE.PMREMGenerator(renderer);
pmrem.compileEquirectangularShader();

new RGBELoader().load('/hdri/studio.hdr', (tex) => {
  const envMap = pmrem.fromEquirectangular(tex).texture;
  scene.environment = envMap;       // affects materials
  // scene.background = envMap;     // ONLY if you want HDRI visible. Usually NOT.
  tex.dispose();
  pmrem.dispose();
});
```

Default: `scene.environment` is set, `scene.background` stays `null` (or a solid color / gradient). Awwwards sites rarely show the raw HDRI as background — they use it for lighting only and put a designed gradient or solid color behind.

### Camera setup

```js
const camera = new THREE.PerspectiveCamera(35, window.innerWidth / window.innerHeight, 0.1, 100);
//                                          ^FOV
// FOV 20–25 = extreme telephoto, used for "Vertigo / dolly zoom" effect (Lusion signature)
// FOV 35    = cinematic, narrow, default for product/object showcase
// FOV 50    = neutral, default for room walkthrough
// FOV 75    = wide, only for tunnels and immersive scenes
```

Wide FOV looks "video-gamey". Narrow FOV looks "filmic". Default to **35** unless the archetype is tunnel or VR-feel. Drop to **20–25** when you want to inversely animate FOV with camera Z (the Hitchcock dolly zoom — see `references/PATTERNS.md` § "Scroll-driven dolly zoom").

---

## 2. The Lerp Loop (the most important pattern in this skill)

Every property that changes during the experience flows through a damped state object. You never write `mesh.position.y = scrollProgress * 10`. You write to `state.cameraY.target` and the loop lerps `state.cameraY.current` toward it.

### The state container

```js
const state = {
  scrollProgress: { current: 0, target: 0, ease: 0.08 },
  cameraY:        { current: 0, target: 0, ease: 0.06 },
  cameraZ:        { current: 5, target: 5, ease: 0.06 },
  heroRotY:       { current: 0, target: 0, ease: 0.10 },
  mouseX:         { current: 0, target: 0, ease: 0.12 },
  mouseY:         { current: 0, target: 0, ease: 0.12 },
};
```

### The framerate-independent lerp

```js
function damp(state, delta) {
  const factor = 1 - Math.pow(1 - state.ease, delta * 60);
  state.current += (state.target - state.current) * factor;
}
```

Why `delta * 60`: the formula treats `ease` as the per-frame factor at 60Hz, then compensates for actual frame time. At 144Hz, factor is smaller per frame; at 30Hz, larger. The visual result is identical.

### The tick

```js
const clock = new THREE.Clock();

function tick() {
  const delta = Math.min(clock.getDelta(), 0.1);  // clamp big jumps (tab switch)

  for (const key in state) damp(state[key], delta);

  // Apply lerped state to the scene
  camera.position.y = state.cameraY.current;
  camera.position.z = state.cameraZ.current;
  hero.rotation.y   = state.heroRotY.current;

  // Subtle parallax from mouse
  camera.position.x = state.mouseX.current * 0.3;
  // (camera.lookAt is also lerp-driven — see § 3)

  composer.render();
  requestAnimationFrame(tick);
}
tick();
```

### Where targets get set

Targets are set by **inputs**:

| Input | Sets |
|---|---|
| Lenis scroll | `state.scrollProgress.target`, then maps to `cameraY.target`, `cameraZ.target`, etc. |
| Mouse move | `state.mouseX.target`, `state.mouseY.target` |
| GSAP timeline | sets multiple targets across keyframes |
| Click/tap | sets a target then resets it |

Inputs are noisy. The lerp loop is the buffer that makes them feel cinematic.

### Lerp ease values — proven defaults

| Property | ease | Why |
|---|---|---|
| Scroll progress | 0.08 | Lenis already smooths input; this is the second pass |
| Camera position | 0.06 | Camera moves are the most visible — slowest lerp |
| Camera rotation / lookAt | 0.05 | Rotation is even more sensitive than position |
| Object rotation | 0.10 | Hero objects can react slightly faster |
| Mouse parallax | 0.12 | Faster than camera so it feels responsive |
| Hover effects (scale, color) | 0.15 | Direct user feedback — faster |

**Below 0.04**: feels broken, "is this animating?".
**Above 0.20**: feels like no smoothing, snappy.
**Tune by feel.** Start at the table values, then nudge.

---

## 3. The Scroll Loop (Lenis → ScrollTrigger → camera)

Awwwards scroll always feels different from native scroll because **three things cooperate**:

1. **Lenis** intercepts native scroll, smooths it, and writes a virtual scroll value.
2. **GSAP ScrollTrigger** reads from Lenis (not from `window.scrollY`) and updates timelines.
3. **The lerp loop** receives `state.scrollProgress.target` from ScrollTrigger and lerps `current`.

That's three layers of smoothing. It's why it feels like silk.

### Wiring

```js
import Lenis from 'lenis';
import gsap from 'gsap';
import ScrollTrigger from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// 1. Init Lenis
const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  smoothWheel: true,
  prevent: () => false,   // Lenis 1.1 requires this to be a function (default not auto-applied)
});

// Override note: in Lenis 1.1+, the equivalent of the old `smoothTouch: true`
// is `syncTouch: true`. Use it ONLY when the design specifically requires lerped
// touch (cinematic landscape flyover, slow narrative). Default omitted because
// iOS momentum scroll fights smoothing and feels broken on mid-tier Android.
//
// Lenis 1.1 also requires `prevent` to be a function. Without an explicit
// `prevent: () => false`, internal Array.find iterations crash on wheel events
// with "this.options.prevent is not a function".

// 2. Bridge Lenis ↔ ScrollTrigger
lenis.on('scroll', ScrollTrigger.update);

// 3. Drive Lenis via gsap.ticker (single source of truth for animation time)
gsap.ticker.add((time) => {
  lenis.raf(time * 1000);
});
gsap.ticker.lagSmoothing(0);  // critical: prevents GSAP from "catching up" after tab switch
```

### Critical CSS

```css
html, body {
  overscroll-behavior: none;     /* no rubber-band on macOS */
  scroll-behavior: auto;         /* MUST NOT be 'smooth' — fights Lenis */
}
html.lenis { height: auto; }
.lenis.lenis-smooth { scroll-behavior: auto !important; }
.lenis.lenis-smooth [data-lenis-prevent] { overscroll-behavior: contain; }
.lenis.lenis-stopped { overflow: hidden; }
```

> **Lenis 1.1.0 class names:** Verify these classes are still applied by Lenis 1.1 in your template. If they are not, fall back to attribute-based scoping: `[data-lenis-prevent]` on any inner-scrolling element (modal, dropdown, code block) and read the `lenis.isStopped` flag from JS instead of relying on the `.lenis-stopped` class. Templates in `assets/templates/` are the authoritative tested CSS.

### Driving the camera with ScrollTrigger

```js
// A timeline that maps scroll progress → state targets
const tl = gsap.timeline({
  scrollTrigger: {
    trigger: '.scroll-container',
    start: 'top top',
    end: 'bottom bottom',
    scrub: true,           // ties timeline progress to scroll position
  },
});

tl.to(state.cameraY,  { target: -10, ease: 'none' }, 0)
  .to(state.cameraZ,  { target:  3,  ease: 'none' }, 0)
  .to(state.heroRotY, { target: Math.PI * 2, ease: 'none' }, 0);
```

**Note:** `ease: 'none'` on the GSAP timeline because the lerp loop is the easing. Double-easing produces a sluggish "molasses" feel.

**Why `scrub: true` and not a number:** with `scrub: true`, target updates are immediate (every scroll event). With `scrub: 0.5`, GSAP adds its own smoothing — and you already have two lerp layers. Three is too many.

### HTML scaffold for scroll-driven scenes

```html
<canvas id="webgl"></canvas>          <!-- fixed, full viewport -->
<main class="scroll-container">
  <section class="vh-100"></section>  <!-- 100vh sections drive timeline -->
  <section class="vh-100"></section>
  <section class="vh-100"></section>
  <section class="vh-100"></section>
</main>
```

```css
#webgl { position: fixed; inset: 0; pointer-events: none; }
.scroll-container { position: relative; z-index: 1; }
.vh-100 { height: 100vh; }
```

The canvas is fixed; the document scrolls behind it; ScrollTrigger reads document scroll; the camera moves through the 3D scene to match.

---

## 4. Render Order (per frame)

Order matters. Doing these out of order causes the symptoms listed below.

```
1. clock.getDelta()           → delta for this frame
2. damp every state entry     → state.current values updated
3. apply state to objects     → camera.position, mesh.rotation, etc.
4. update controls (if any)   → e.g. mixer.update(delta) for animations
5. update post-processing uniforms (e.g. time-based shader effects)
6. composer.render(delta)     → final draw
7. requestAnimationFrame(tick)
```

### Symptoms of wrong order

| Symptom | Cause |
|---|---|
| Camera jitters by 1 frame | applied state before damping (step 3 before step 2) |
| Post-processing one frame stale | composer.render before applying state (step 6 before step 3) |
| Animation hitches after tab switch | not clamping `delta` (no `Math.min(delta, 0.1)`) |
| 144Hz monitor runs 2x faster | not multiplying by `delta` somewhere |
| Lenis and camera out of sync | calling `lenis.raf()` outside `gsap.ticker` |

---

## 5. Cleanup (when navigating away or hot-reloading)

Three.js does not garbage-collect GPU resources. You must dispose explicitly.

### The dispose helper

```js
function disposeObject(obj) {
  obj.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      for (const mat of materials) {
        for (const key of Object.keys(mat)) {
          const value = mat[key];
          if (value && value.isTexture) {
            value.dispose();  // covers Texture, DataTexture, CompressedTexture, CubeTexture, etc.
          }
        }
        mat.dispose();
      }
    }
  });
}
```

### Full teardown

```js
function destroy() {
  // Stop the loop
  cancelAnimationFrame(rafId);

  // Stop Lenis + GSAP
  lenis.destroy();
  ScrollTrigger.getAll().forEach((t) => t.kill());
  gsap.ticker.remove(lenisTickerCb);

  // Dispose scene
  disposeObject(scene);

  // Dispose post-processing
  composer.dispose();

  // Dispose renderer last
  renderer.dispose();
  renderer.forceContextLoss();
  renderer.domElement.remove();

  // Remove listeners
  window.removeEventListener('resize', onResize);
  window.removeEventListener('mousemove', onMouseMove);
}
```

### When to call destroy

- Single-page app navigating to a non-3D page
- Hot module reload during development
- React `useEffect` cleanup return value
- `pagehide` event for safety

If you skip cleanup, every navigation leaks ~50–200 MB of GPU memory until the tab crashes. This is the single most common production bug in Three.js sites.

---

## 6. Resize

The browser fires `resize` 60+ times per second during a drag-resize. Doing a full `composer.setSize()` on every event causes frame hitches and, with PMREM regeneration, can cause GPU memory pressure. Always debounce or rAF-coalesce.

```js
let resizePending = false;

function onResize() {
  if (resizePending) return;
  resizePending = true;
  requestAnimationFrame(() => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));  // CAP HERE
    composer.setSize(w, h);
    resizePending = false;
  });
}
window.addEventListener('resize', onResize);
```

The pixelRatio cap belongs inside the rAF callback, not just initial setup, because users dragging a window between displays of different DPR (e.g. external monitor → laptop retina) trigger resize events as the window crosses the boundary.

**Why rAF-coalesce, not `setTimeout` debounce:** `setTimeout(..., 100)` makes the canvas visibly stretch for 100ms before snapping. `requestAnimationFrame` updates on the very next paint and feels instant. Only fall back to `setTimeout` if you also need to defer expensive work like PMREM regeneration on env-map change.

---

## 7. Mental model — the data flow

> **One-liner to memorize:** Inputs write to `state.*.target`. The loop lerps `state.*.current` toward `target`. Render reads `state.*.current`. Three layers, never more.

```
User scrolls / moves mouse
        │
        ▼
   Lenis (scroll) / mousemove handler
        │
        ▼
   GSAP ScrollTrigger timeline   ← writes state.*.target
        │
        ▼
   Lerp loop (every frame)        ← updates state.*.current
        │
        ▼
   Apply state to camera/meshes
        │
        ▼
   composer.render()
        │
        ▼
   Pixels on screen
```

Inputs write **targets**. The loop reads targets and updates **current**. Rendering reads **current**. This separation is what makes the experience feel composed and intentional — a design, not a reaction.

---

## Reading order for newcomers to this skill

1. § 2 (Lerp loop) — read first, internalize before anything else
2. § 3 (Scroll loop) — read second
3. § 1 (Scene graph) — read when starting your first scene
4. § 4–6 (Render order, cleanup, resize) — reference as you implement
5. § 7 (Mental model) — re-read whenever the architecture feels confusing
