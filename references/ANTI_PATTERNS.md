# ANTI_PATTERNS — what kills the aesthetic

Long-form expansion of the Hard Rules in `SKILL.md`. Each entry: **the mistake**, **why it kills the look**, **what to do instead**, **how to spot it in code review**.

The Awwwards aesthetic is fragile. Twenty things have to be right; one thing wrong and the work feels "WebGL demo" instead of "premium site". Most of these come from new Three.js developers shipping their first iteration without iterating.

---

## 1. Snap animation (anything without lerp)

### The mistake

```js
// In response to scroll
mesh.position.y = scrollY * 0.01;
mesh.rotation.y = scrollY * 0.005;
```

### Why it kills the look

Native scroll has 1px granularity and is event-driven. The mesh inherits that granularity → motion looks like it's clicking through positions, not flowing through them. Even at 60fps, the eye reads "stepped".

### Do this instead

Route through a lerp loop. See `ARCHITECTURE.md` § 2:

```js
// Set the target on scroll
state.heroY.target = scrollY * 0.01;

// In tick(), damp toward target
damp(state.heroY, delta);
mesh.position.y = state.heroY.current;
```

### Code-review tell

`mesh.* = scrollY *` or `mesh.* = e.client* /` anywhere in the scroll/mouse handlers. Should never touch the mesh directly.

---

## 2. `metalness > 0` without an environment map

### The mistake

```js
const material = new THREE.MeshStandardMaterial({
  color: 0x88ccff,
  metalness: 1.0,
  roughness: 0.2,
});
// scene.environment is null
```

### Why it kills the look

Metals are 100% reflective. With no environment to reflect, they reflect black. The result is a near-black blob that you "fix" by cranking ambient light, which produces a flat, plastic-looking material.

### Do this instead

Always load an HDRI or use `RoomEnvironment` as a fallback:

```js
// Fastest path — no asset needed
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
pmrem.dispose();
```

See `references/PATTERNS.md` #9 (HDRI) and #11 (RoomEnvironment).

### Code-review tell

Search the codebase for `metalness:` and verify `scene.environment` is set somewhere before any metal mesh is rendered.

---

## 3. Uncapped pixel ratio

### The mistake

```js
renderer.setPixelRatio(window.devicePixelRatio);
```

### Why it kills the look

A 4K monitor at DPR 2 means the renderer draws **4× the pixels** of an HD monitor. A user with a fancy display gets 15fps; a user with a budget laptop gets 60. The user with the fancy display assumes your site is broken and leaves.

### Do this instead

```js
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
```

Cap at 2. The visual quality difference between DPR 2 and DPR 3 is invisible to the human eye on most content; the performance difference is 2.25× more pixels.

Apply the cap in **both** initial setup AND `onResize` (a user dragging between monitors of different DPR triggers resize).

### Code-review tell

Search for `setPixelRatio(window.devicePixelRatio)` without a `Math.min` guard.

---

## 4. Uncompressed GLB

### The mistake

Drag-drop export from Blender → 12 MB file → ship it.

### Why it kills the look

Mobile users on 4G see a 4-second blank canvas before the model loads. They leave at second 2.

### Do this instead

Use Draco + Meshopt (see `references/BLENDER_PIPELINE.md`):

```bash
gltf-transform draco model.glb model-compressed.glb
gltf-transform meshopt model-compressed.glb model-final.glb
```

Typical: 12 MB → 800 KB. With Meshopt → 400 KB.

In the loader:

```js
loader.setDRACOLoader(draco);
loader.setMeshoptDecoder(MeshoptDecoder);
```

### Code-review tell

Inspect `.glb` file sizes in `assets/`. Anything over 2 MB on a single hero object is suspect.

---

## 5. Auto-play audio

### The mistake

```js
const audio = new Audio('/ambient.mp3');
audio.loop = true;
audio.play();   // browsers block this; user never hears it anyway
```

### Why it kills the look

1. Browsers block autoplay → silent failure (or worse, console error).
2. Even if it worked: users hate sites that talk to them unprovoked.

### Do this instead

Gate behind a user gesture, default to muted, persist user choice:

```js
// Read previous choice. First-time visitors get null → muted = true (safe default).
const stored = localStorage.getItem('audio-muted');   // 'true' | 'false' | null
const muted = stored !== 'false';                     // default to muted
audio.muted = muted;
muteToggle.checked = !muted;

// First user gesture unlocks playback (browsers require this)
document.addEventListener('click', () => {
  audio.play();
}, { once: true });

// Toggle persists across sessions
muteToggle.addEventListener('change', () => {
  audio.muted = !muteToggle.checked;
  localStorage.setItem('audio-muted', String(audio.muted));
});
```

The `stored !== 'false'` line is the key bit: `null !== 'false'` is `true` (so first-time visitors get muted), `'true' !== 'false'` is `true` (returning user previously muted), `'false' !== 'false'` is `false` (returning user previously unmuted).

See `SKILL.md` § Audio.

### Code-review tell

`audio.play()` not preceded by a user-gesture handler. Audio elements without an `<audio>` mute toggle in the UI.

---

## 6. `console.log` in the animation loop

### The mistake

```js
function tick() {
  console.log('hero rotation:', hero.rotation.y);
  // ...
  requestAnimationFrame(tick);
}
```

### Why it kills the look

DevTools serializes every console arg. With DevTools open, that single line drops you from 60fps to 8fps. With DevTools closed, the cost is small but real (~0.05ms per call). Users sometimes browse with DevTools open (devs, journalists, your boss).

### Do this instead

Remove all logs from the tick. Use breakpoints, not logs, when debugging:

```js
function tick() {
  // ❌ console.log(hero.rotation.y);
  // ✅ Pause in DevTools, inspect `hero` directly
  // ...
}
```

If you really need a log, gate it behind a counter:

```js
if (frameCount % 120 === 0) console.log(...);   // once every 2 seconds
```

### Code-review tell

`grep -n "console\." inside any function ending in `requestAnimationFrame`.

---

## 7. CSS `scroll-behavior: smooth` + Lenis

### The mistake

```css
html { scroll-behavior: smooth; }
```

with Lenis active.

### Why it kills the look

Two scroll engines fight. CSS smooth tries to ease scroll position; Lenis simultaneously writes its own value. Result: scroll feels "drunk" — sometimes smooth, sometimes laggy, sometimes overshooting.

### Do this instead

```css
html, body { scroll-behavior: auto; }
```

Lenis is the only scroll engine. See `references/ARCHITECTURE.md` § 3.

### Code-review tell

`scroll-behavior: smooth` anywhere in CSS while Lenis is initialized in JS.

---

## 8. `OrbitControls` in production

### The mistake

```js
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const controls = new OrbitControls(camera, renderer.domElement);
```

shipped to production.

### Why it kills the look

OrbitControls is a prototyping tool. It hijacks the wheel event (so Lenis can't scroll), it lets users zoom into the inside of objects, it has no concept of scroll-driven camera. The result is a site users get "lost" in.

### Do this instead

Drive the camera from scroll progress (Pattern #1, #2 in PATTERNS.md). For a "hero spin" feel, use the touch-friendly drag rotate (Pattern #21) — but don't tie it to the camera; tie it to a hero object.

### Code-review tell

Any `OrbitControls` import that's reached in production code paths (vs dev-only debug toggle).

---

## 9. `ShaderMaterial` without precision declaration

### The mistake

```glsl
varying vec2 vUv;
void main() {
  // missing: precision mediump float;
  gl_FragColor = vec4(vUv, 0.0, 1.0);
}
```

### Why it kills the look

Mobile GPUs default to `lowp` (low precision) when no declaration is given. `lowp` gives you ~9 bits per component. Gradients band, time-driven shaders strobe. Looks broken on Android.

### Do this instead

Always declare:

```glsl
precision mediump float;
// or
precision highp float;   // when you need it (e.g. world-position math)
```

Three.js auto-injects this in built-in materials but NOT in raw `ShaderMaterial`.

### Code-review tell

`fragmentShader: \`` immediately followed by something other than `precision`.

---

## 10. Raycasting against the whole scene every frame

### The mistake

```js
function tick() {
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(scene.children, true);   // ❌ recursive on all
}
```

### Why it kills the look

For a scene with 50+ meshes (or instanced meshes with many children), this is O(n × triangles). Frame time spikes whenever the cursor moves over busy areas.

### Do this instead

Maintain an explicit `interactive` array of just the meshes the user can hover/click:

```js
const interactive = [hero, button1, button2];
const hits = raycaster.intersectObjects(interactive, false);
```

For very many interactive objects, switch to GPU picking (PATTERNS.md #20).

### Code-review tell

`intersectObjects(scene.children, true)`. The `true` is the smell.

---

## 11. Frame-count-based animation

### The mistake

```js
let frame = 0;
function tick() {
  frame++;
  hero.rotation.y = frame * 0.01;
  requestAnimationFrame(tick);
}
```

### Why it kills the look

A 144Hz monitor runs `tick()` 2.4× as often as a 60Hz one. The hero rotates at different speeds on different displays. Users with fancy monitors see your animation as "fast"; users with budget displays see "slow".

### Do this instead

Multiply by `delta` (real seconds elapsed):

```js
const clock = new THREE.Clock();
function tick() {
  const delta = Math.min(clock.getDelta(), 0.1);   // clamp pause-spikes
  hero.rotation.y += delta * 0.6;   // 0.6 rad/sec, regardless of FPS
  requestAnimationFrame(tick);
}
```

For lerp specifically, use the framerate-independent formula from ARCHITECTURE.md § 2:

```js
factor = 1 - Math.pow(1 - ease, delta * 60)
```

### Code-review tell

`+= 0.01`, `+= 0.005` etc. without a `delta *` next to them. `frame++` counters used for animation.

---

## 12. Render targets without explicit dispose

### The mistake

You build a glass effect, ship it, navigate to another page in your SPA. The user's GPU memory steadily grows; after 10 page navigations, the tab crashes.

### Why it kills the look

Three.js doesn't garbage-collect GPU resources. Every `WebGLRenderTarget`, `Texture`, `BufferGeometry`, `Material` holds GPU memory until `.dispose()` is called.

### Do this instead

Explicit cleanup. See `ARCHITECTURE.md` § 5 for the full pattern. The bare minimum:

```js
function destroy() {
  scene.traverse((obj) => {
    obj.geometry?.dispose();
    if (obj.material) {
      const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
      for (const m of mats) {
        for (const k in m) if (m[k]?.isTexture) m[k].dispose();
        m.dispose();
      }
    }
  });
  composer.dispose?.();
  renderer.dispose();
  renderer.forceContextLoss();
}
```

### Code-review tell

No `dispose()` calls anywhere in the codebase. No teardown function. SPA route changes that don't reach a cleanup path.

---

## 13. Mixing tone mapping settings

### The mistake

```js
renderer.toneMapping = THREE.ACESFilmicToneMapping;
// ... and also
composer.addPass(new ToneMappingEffect({ mode: ACES_FILMIC }));
```

OR

```js
renderer.toneMapping = THREE.NoToneMapping;
// ... but no OutputPass in the composer chain
```

### Why it kills the look

Double tone mapping → washed-out, low-contrast image. No tone mapping → blown highlights, weirdly dark midtones (HDR values rendered linearly).

### Do this instead

**Either** set tone mapping on the renderer AND include `OutputPass` in the chain (the canonical setup), **or** apply tone mapping only at the post-processing layer with `renderer.toneMapping = NoToneMapping`. Never both.

This skill defaults to the first: renderer's tone mapping + `OutputPass`. See `POST_PROCESSING.md`.

### Code-review tell

Search for `ToneMapping` in two places. If both renderer config AND a composer pass touch tone mapping, audit.

---

## 14. Reusing geometry in `dispose` calls

### The mistake

```js
const sharedGeom = new THREE.SphereGeometry(1, 32, 32);
const a = new THREE.Mesh(sharedGeom, mat1);
const b = new THREE.Mesh(sharedGeom, mat2);
// later...
a.geometry.dispose();   // disposes sharedGeom
b.geometry.dispose();   // tries to dispose disposed geometry → silent error or weird behavior
```

### Why it kills the look

Doesn't kill it visually but causes warnings and intermittent black meshes when geometry is re-disposed.

### Do this instead

Track shared geometries explicitly and dispose ONCE:

```js
const shared = new THREE.SphereGeometry(1, 32, 32);
// ... use it for many meshes ...
shared.dispose();   // dispose the shared instance once at teardown, not per-mesh
```

OR clone per mesh: `new THREE.Mesh(sharedGeom.clone(), ...)`.

### Code-review tell

`new SomeGeometry(...)` assigned to a variable, then used by 2+ meshes. Audit the dispose path.

---

## 15. Animating layout-affecting CSS during scroll

### The mistake

```js
// On scroll
heroSection.style.height = `${100 - scrollProgress * 50}vh`;
```

### Why it kills the look

`height` triggers layout reflow. Changing it 60 times per second tanks performance and ScrollTrigger recalculates document height every frame.

### Do this instead

Animate transforms and opacity only. They composite on the GPU without reflow:

```js
heroSection.style.transform = `scale(${1 - scrollProgress * 0.5})`;
heroSection.style.opacity = `${1 - scrollProgress}`;
```

### Code-review tell

`element.style.height`, `width`, `top`, `left`, `padding`, `margin` set inside scroll handlers or animation loops.

---

## 16. Parallax on touch devices

### The mistake

```js
window.addEventListener('mousemove', (e) => {
  state.mouseX.target = ...;
});
// no touch-device check
```

### Why it kills the look

On touch devices, mousemove fires only when fingers tap+drag, which produces sudden parallax jumps that look broken. Better: disable parallax entirely on coarse pointers.

### Do this instead

```js
if (!window.matchMedia('(pointer: coarse)').matches) {
  window.addEventListener('mousemove', /* ... */);
}
```

### Code-review tell

`mousemove` listener that drives camera position, with no `pointer: coarse` guard.

---

## 17. Loading 4K HDRIs

### The mistake

```js
new RGBELoader().load('/hdri/photo_studio_4k.hdr', /* 28 MB */, ...);
```

### Why it kills the look

28 MB on a hero load → users see a black scene for 8 seconds on 3G. The HDRI is for **lighting calculation**, not for direct viewing — 1K is indistinguishable from 4K once it's PMREM-convolved.

### Do this instead

Always download the **1K** variant from polyhaven.com. Result: 2-3 MB.

### Code-review tell

HDR files in assets folder larger than 5 MB. File names containing `4k` or `8k`.

---

## 18. Missing `frustumCulled = false` on ScrollTrigger-driven scenes

### The mistake

You scroll past a section. The hero mesh's bounding box leaves the camera frustum mid-animation. Three.js culls it. The user scrolls back; the mesh is invisible until another frame triggers re-evaluation.

### Why it kills the look

Brief disappearance during scroll, especially on hero objects with non-standard pivots or that have been scaled to 0 in the intro.

### Do this instead

For hero objects whose bounding boxes change at runtime (morphing, animated scale, custom shaders that displace vertices):

```js
hero.frustumCulled = false;
```

For static meshes that are always near the camera, leave culling on (it's a perf win).

### Code-review tell

Hero objects with vertex shaders or morph targets that don't have `frustumCulled = false`.

---

## 19. Forgetting `colorSpace` on textures

### The mistake

```js
const tex = await loader.loadAsync('/textures/diffuse.jpg');
material.map = tex;
// tex.colorSpace stays at default LinearSRGBColorSpace
```

### Why it kills the look

Albedo (diffuse) textures from JPEG/PNG are in sRGB color space. If you don't tag them, three reads them as linear → colors look pale and washed.

### Do this instead

```js
tex.colorSpace = THREE.SRGBColorSpace;   // for albedo only
```

**NOT** for normal maps, roughness maps, AO maps — those are data, not color, and stay `LinearSRGBColorSpace`.

### Code-review tell

`material.map = ` set without a preceding `tex.colorSpace = SRGBColorSpace`. (GLTFLoader handles this for you, but TextureLoader doesn't.)

---

## 20. Mixing CSS-driven and JS-driven scroll position

### The mistake

```js
window.scrollTo({ top: 1000, behavior: 'smooth' });   // browser scroll
```

while Lenis is active.

### Why it kills the look

Lenis is the source of truth. `window.scrollTo` writes directly past it; ScrollTrigger sees a sudden jump; camera animations skip frames.

### Do this instead

Use Lenis's API:

```js
lenis.scrollTo(1000, { duration: 1.5 });
```

For "scroll to anchor" links, intercept clicks and route through `lenis.scrollTo()`.

### Code-review tell

`window.scrollTo`, `element.scrollIntoView`, anchor link `href="#section"` without a Lenis interceptor.

---

## Reading order

When debugging a "feels broken" complaint, scan these in order:

1. **§ 1 (Snap)** — the most common cause of "doesn't feel premium"
2. **§ 11 (Frame-count)** — explains "fast on my machine, slow on yours"
3. **§ 13 (Tone mapping)** — explains "looks washed out"
4. **§ 2 (No HDRI)** — explains "metals look black/plastic"
5. **§ 7 (CSS scroll)** — explains "scroll feels weird"
6. **§ 12 (No dispose)** — explains "tab crashes after navigation"

The other 14 are situational; lean on this list when the symptom matches.
