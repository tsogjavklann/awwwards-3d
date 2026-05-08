# POST_PROCESSING — three built-in EffectComposer

This skill uses **three's built-in `EffectComposer`** from `three/addons/postprocessing/`. The standalone `postprocessing` npm library was rejected: at v6.36.0 it triggers `Material.onBeforeRender() has been removed` warnings on three r170, flooding the console once per material per frame.

Three built-in passes cover every Awwwards effect: bloom, DOF, vignette, chromatic aberration, grain, color grading. This file documents the canonical chain and recipes.

---

## The canonical chain

```
RenderPass(scene, camera)         # 1. draw the scene into HDR buffer
↓
UnrealBloomPass                   # 2. extract highlights, blur, add back
↓
ShaderPass(vignette)              # 3. corner darkening
↓
OutputPass                        # 4. tone-map (ACES) + sRGB conversion
↓
ShaderPass(grain)                 # 5. final film grain
```

Order matters. Bloom must run BEFORE tone mapping because it works in linear space. Vignette CAN go before or after tone mapping; before is cheaper (one less LDR conversion). Grain must run AFTER tone mapping so the noise sits on the final tone-mapped color, not the raw HDR values.

### Setup

```js
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

// Renderer must be configured for the chain to work correctly
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;   // OutputPass reads this
renderer.toneMappingExposure = 1.0;

// HDR render target — bloom needs > 1.0 luminance to produce real glow
const hdrTarget = new THREE.WebGLRenderTarget(
  window.innerWidth, window.innerHeight,
  { type: THREE.HalfFloatType },
);

const composer = new EffectComposer(renderer, hdrTarget);
composer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
composer.setSize(window.innerWidth, window.innerHeight);
```

**Why HDR (`HalfFloatType`):** without HDR, the framebuffer clamps colors at 1.0 (full white). Bloom can only blur "white" areas. With HDR, a sun or specular highlight can hit 5.0, 10.0, or higher — bloom samples that and the result feels like real light spilling. This is the difference between "Three.js demo" bloom and "Awwwards" bloom.

---

## Pass 1 — RenderPass

```js
composer.addPass(new RenderPass(scene, camera));
```

Always first. Draws the scene into the composer's read target. No options needed.

If you need different cameras per pass (e.g. UI overlay), create a second `RenderPass` with that camera and `clear: false`, but typically one is enough.

---

## Pass 2 — UnrealBloomPass

```js
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  0.45,    // strength    (0.0–2.0; 0.4–0.6 is "tasteful Awwwards")
  0.4,     // radius      (0.0–1.0; 0.4 is wide soft glow, 0.7 is hazy)
  0.82,    // threshold   (0.0–1.0; pixels above this contribute)
);
composer.addPass(bloomPass);
```

### Tweaks

| Parameter | Low | Awwwards default | High |
|---|---|---|---|
| `strength` | 0.2 (subtle sheen) | **0.45** | 1.2 (overpowering) |
| `radius` | 0.2 (sharp glow) | **0.4** | 0.85 (foggy) |
| `threshold` | 0.6 (everything bright glows) | **0.82** | 0.95 (only emissives) |

**Mobile budget:** drop `strength` to 0.3 and don't change radius. The blur passes are the cost; threshold is free.

### Resize

UnrealBloomPass holds its own internal render targets sized to the viewport. Update them on resize:

```js
function onResize() {
  // ...standard resize code...
  bloomPass.resolution.set(w, h);   // optional; setSize on composer covers this
}
```

`composer.setSize(w, h)` propagates to all passes, so this is usually automatic.

---

## Pass 3 — Vignette (custom ShaderPass)

Three has no built-in vignette. Use a `ShaderPass` with a small fragment shader.

```js
const vignettePass = new ShaderPass({
  uniforms: {
    tDiffuse:  { value: null },
    uOffset:   { value: 0.4 },     // 0.0–1.0; lower = darker corners
    uDarkness: { value: 0.55 },    // 0.0–1.0; how dark the corners go
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float uOffset;
    uniform float uDarkness;
    varying vec2 vUv;
    void main() {
      vec4 c = texture2D(tDiffuse, vUv);
      vec2 uv = vUv - 0.5;
      float v = smoothstep(0.8, uOffset, length(uv));
      gl_FragColor = vec4(mix(c.rgb * (1.0 - uDarkness), c.rgb, v), c.a);
    }
  `,
});
composer.addPass(vignettePass);
```

`tDiffuse` is the convention name for the input texture — `ShaderPass` automatically wires the previous pass's output to this uniform. Don't rename it.

### Tweaks

- `uOffset 0.4 / uDarkness 0.55` is the Awwwards default — present but not heavy-handed.
- `uOffset 0.6 / uDarkness 0.3` is the Apple-style subtle vignette.
- `uOffset 0.2 / uDarkness 0.8` is dramatic; only for cinematic / dark scenes.

---

## Pass 4 — OutputPass

```js
composer.addPass(new OutputPass());
```

This pass:
1. Applies the renderer's `toneMapping` (we set `ACESFilmicToneMapping`)
2. Converts from linear to `outputColorSpace` (we set `SRGBColorSpace`)

Without it, the HDR buffer outputs raw linear values that look washed out and gray. **Always include OutputPass** when you pass an `HalfFloatType` render target to `EffectComposer` (the canonical setup at the top of this file).

If you choose a different tone mapping (Reinhard, Cineon, AgXToneMapping, NeutralToneMapping), set it on `renderer.toneMapping` and OutputPass picks it up automatically.

---

## Pass 5 — Film grain (custom ShaderPass)

Grain on the final tone-mapped output gives the "shot on film" feel. Cheap and effective.

```js
const grainPass = new ShaderPass({
  uniforms: {
    tDiffuse:   { value: null },
    uTime:      { value: 0 },
    uIntensity: { value: 0.05 },   // 0.02 subtle, 0.08 heavy
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float uTime;
    uniform float uIntensity;
    varying vec2 vUv;
    float rand(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main() {
      vec4 c = texture2D(tDiffuse, vUv);
      float n = rand(vUv + uTime) - 0.5;
      gl_FragColor = vec4(c.rgb + n * uIntensity, c.a);
    }
  `,
});
composer.addPass(grainPass);

// In tick():
grainPass.uniforms.uTime.value = clock.elapsedTime;
```

**Why time-driven:** static grain looks like a TV freeze-frame. Time-driven grain dances and feels filmic.

**Why this AFTER OutputPass:** if grain were applied in linear HDR space, the random offset would look uneven (a +0.05 nudge on a value of 5.0 is invisible; on a value of 0.2 it's huge). After tone mapping, all values are in [0, 1] and grain is uniform.

---

## Optional passes

Add these only when the design calls for them. Each adds ~0.5–1.0ms on a mid-tier desktop GPU.

### Depth of field — `BokehPass`

`BokehPass` re-renders the scene with depth-aware blur. It needs the raw scene + camera, not a downstream image. Use it as the **first** pass — it replaces `RenderPass` rather than chaining after it.

```js
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';

const dof = new BokehPass(scene, camera, {
  focus: 5.0,        // distance to focus point (world units)
  aperture: 0.0008,  // smaller = sharper, larger = more blur
  maxblur: 0.01,
  width: window.innerWidth,
  height: window.innerHeight,
});

// Replace your RenderPass with BokehPass — it does the rendering itself.
composer.addPass(dof);
composer.addPass(bloomPass);
composer.addPass(vignettePass);
composer.addPass(new OutputPass());
composer.addPass(grainPass);
```

**Use when:** product showcase where the user clearly focuses on one item and background should melt away. Don't use for full scenes — DOF on architecture or busy hero scenes looks artificial.

**Animate focus on scroll:**

```js
gsap.to(dof.uniforms['focus'], {
  value: 12.0,
  scrollTrigger: { trigger: '#section', start: 'top center', scrub: true },
});
```

### Chromatic aberration — `ShaderPass`

```js
const caPass = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uAmount: { value: 0.003 } },
  vertexShader: `
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float uAmount;
    varying vec2 vUv;
    void main() {
      vec2 dir = vUv - 0.5;
      float r = texture2D(tDiffuse, vUv + dir * uAmount).r;
      float g = texture2D(tDiffuse, vUv).g;
      float b = texture2D(tDiffuse, vUv - dir * uAmount).b;
      gl_FragColor = vec4(r, g, b, 1.0);
    }
  `,
});
// Place between vignette and OutputPass for "lens" feel
```

`uAmount 0.001` is an LCD-edge whisper; `0.005` is glass distortion; `0.02` looks broken.

### LUT color grading — `LUTPass` + `LUTCubeLoader`

See `references/PATTERNS.md` § #33 — already documented as built-in three path. Insert `LUTPass` AFTER OutputPass (LUTs are designed for sRGB input).

### SMAA antialiasing — `SMAAPass`

```js
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
composer.addPass(new SMAAPass(window.innerWidth, window.innerHeight));
```

Add as the very last pass when `renderer.antialias = false`. SMAA is cheaper than MSAA in a post pipeline and looks ~as good. Skip if you set `antialias: true` on the renderer (but that fights the HDR buffer in some cases).

---

## Glass + bloom interaction

`MeshTransmissionMaterial` + bloom is the Awwwards "glass orb" combo, but they fight:
- Glass refraction tone-maps the scene behind it independently
- Bloom may then pick up bright refracted highlights and over-glow them

**Fix:** lower `bloom.threshold` to 0.9+ and `bloom.strength` to 0.3. Test with the actual glass object in the scene; tweak by eye.

---

## Performance budget

These are **rough estimates** for orientation, not guarantees — actual cost varies by scene complexity, GPU, browser, and OS. Profile in Chrome DevTools' Performance tab against your real scene before optimizing.

Approximate cost per frame at 1080p on a mid-tier desktop GPU (think M1, GTX 1060, RTX 3050):

| Pass | Typical cost (ms) |
|---|---|
| RenderPass (single hero mesh + HDRI) | 0.5–1.5 |
| RenderPass (full scene + shadows + 10+ meshes) | 3–8 |
| UnrealBloomPass | 1.0–2.0 |
| Vignette ShaderPass | < 0.1 |
| OutputPass | < 0.1 |
| Grain ShaderPass | < 0.1 |
| **Total post (no extras)** | **~2 ms** |

On mid-tier mobile (Snapdragon 7+ Gen 2 / A15 Bionic) the same chain runs ~6–8 ms. If you can't hit 30 fps:

1. Cut `composer.setPixelRatio(1)` first (biggest perf win, smallest visual cost)
2. Disable bloom or drop `strength` to 0.25
3. Drop optional passes (DOF, CA, SMAA)
4. Last resort: skip the composer entirely on mobile — render directly with `renderer.render(scene, camera)`

```js
const isMobile = window.matchMedia('(max-width: 768px)').matches;
if (isMobile) {
  composer.setPixelRatio(1);
  bloomPass.strength = 0.25;
}
```

---

## Background pass ordering

If you're using Pattern #30 (background gradient mesh), insert it as a FIRST RenderPass before the main scene's RenderPass. **Critical:** the second RenderPass MUST have `.clear = false`, otherwise it wipes the background.

```js
const bgPass = new RenderPass(bgScene, new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1));
const mainPass = new RenderPass(scene, camera);
mainPass.clear = false;            // do NOT clear the bg drawn by bgPass
mainPass.clearDepth = true;        // but DO clear depth so foreground renders correctly

composer.addPass(bgPass);
composer.addPass(mainPass);
// ... rest of chain (bloom, vignette, output, grain)
```

`RenderPass.clear` defaults to `true`. Without explicitly setting it `false` on `mainPass`, the second pass clears whatever the bgPass just drew. This is a common silent bug — the user sees only the main scene over a black background, never the gradient.

For most projects, prefer Option 1 from PATTERNS.md #30 (bake gradient into a mesh inside the main scene with `renderOrder = -1`) — simpler and post-processed identically to everything else, no two-pass juggling.

---

## Disposal

```js
function destroyComposer() {
  // Three's EffectComposer doesn't dispose internal targets automatically.
  composer.renderTarget1?.dispose();
  composer.renderTarget2?.dispose();
  hdrTarget.dispose();
  bloomPass.dispose?.();
  vignettePass.dispose?.();
  grainPass.dispose?.();
}
```

Call before `renderer.dispose()` in your teardown. See `ARCHITECTURE.md` § 5 for the full cleanup sequence.

---

## TL;DR — the recipe

```js
const hdr = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType });
const composer = new EffectComposer(renderer, hdr);
composer.setPixelRatio(Math.min(devicePixelRatio, 2));
composer.setSize(W, H);

composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), 0.45, 0.4, 0.82));
composer.addPass(vignettePass);   // custom ShaderPass
composer.addPass(new OutputPass());
composer.addPass(grainPass);      // custom ShaderPass

renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.outputColorSpace = THREE.SRGBColorSpace;
```

This is the chain in `assets/templates/minimal.html`. Verified to produce zero console warnings on three@0.170.
