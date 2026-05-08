# PATTERNS — 33 Copy-Paste Snippets

Each pattern follows the same shape: **Use when / Cost / Dependencies / Code / How it works / Tweaks / See also**. Read the metadata first to decide if a pattern fits, then copy the code.

All snippets are written for `three@0.170.0`, `gsap@3.12.5`, `lenis@1.1.0`, plus `three-mesh-bvh@0.7.8` (when MeshTransmissionMaterial is used). Post-processing uses three's built-in `EffectComposer` from `three/addons/postprocessing/` — see `POST_PROCESSING.md`. Snippets assume the importmap and lerp loop from `ARCHITECTURE.md` are in place.

---

## Quick Index

### Camera (4)
- [#1 Scroll-driven dolly zoom](#1--scroll-driven-dolly-zoom)
- [#2 Spline-following camera](#2--spline-following-camera)
- [#3 Mouse parallax (depth-aware)](#3--mouse-parallax-depth-aware)
- [#4 Cinematic intro reveal](#4--cinematic-intro-reveal)

### Materials (4)
- [#5 Glass / MeshTransmissionMaterial](#5--glass--meshtransmissionmaterial-setup)
- [#6 Iridescent metal](#6--iridescent-metal)
- [#7 Holographic / fresnel rim](#7--holographic--fresnel-rim)
- [#8 Animated UV scroll](#8--animated-uv-scroll)

### Lighting (4)
- [#9 HDRI loader (RGBELoader + PMREM)](#9--hdri-loader-rgbeloader--pmrem)
- [#10 Three-point cinematic lighting](#10--three-point-cinematic-lighting)
- [#11 RoomEnvironment fallback](#11--roomenvironment-fallback)
- [#12 Soft shadow catcher](#12--soft-shadow-catcher)

### Geometry / Mesh (5)
- [#13 Instanced mesh (10k objects)](#13--instanced-mesh-10k-objects)
- [#14 Particle field with custom shader](#14--particle-field-with-custom-shader)
- [#15 GLB loader + Draco + Meshopt](#15--glb-loader--draco--meshopt)
- [#16 KTX2 texture loader](#16--ktx2-texture-loader)
- [#17 Mesh morphing on scroll (two approaches)](#17--mesh-morphing-on-scroll-two-approaches)

### Interaction (4)
- [#18 Lerped custom cursor element](#18--lerped-custom-cursor-element)
- [#19 Magnetic hover (3D button attract)](#19--magnetic-hover-3d-button-attract)
- [#20 Raycaster + GPU picking alternative](#20--raycaster--gpu-picking-alternative)
- [#21 Touch-friendly drag rotate](#21--touch-friendly-drag-rotate)

### Scroll (4)
- [#22 Lenis init + ScrollTrigger bridge](#22--lenis-init--scrolltrigger-bridge)
- [#23 Scroll-pinned section](#23--scroll-pinned-section)
- [#24 Horizontal scroll section](#24--horizontal-scroll-section)
- [#25 Reveal-on-scroll fade-in (text)](#25--reveal-on-scroll-fade-in-text)

### Performance (4)
- [#26 requestIdleCallback warmup](#26--requestidlecallback-warmup)
- [#27 Visibility API pause loop](#27--visibility-api-pause-loop)
- [#28 Debounced / coalesced resize](#28--debounced--coalesced-resize)
- [#29 WebGL feature detection](#29--webgl-feature-detection)

### Bonus (4)
- [#30 Background gradient mesh](#30--background-gradient-mesh)
- [#31 CSS3DRenderer text in 3D space](#31--css3drenderer-text-in-3d-space)
- [#32 Loading screen + asset preloader](#32--loading-screen--asset-preloader)
- [#33 LUT color grading](#33--lut-color-grading)

---

## #1 — Scroll-driven dolly zoom

**Use when:** Hero section, "Vertigo / Hitchcock" effect, dramatic reveal where the subject stays the same size while the background warps.
**Cost:** Low (changes two scalars per frame).
**Dependencies:** Lerp loop, ScrollTrigger.

### The code

```js
// Initial values
const initialZ = 5;
const initialFov = 25;       // start narrow (telephoto)
const subjectSize = 1;       // approx world-units the subject occupies on screen

// State entries
state.cameraZ.target = initialZ;
state.cameraFov = { current: initialFov, target: initialFov, ease: 0.06 };

// On scroll, GSAP animates ONLY camera Z (target). FOV is derived from current Z
// inside tick() — it can't live in GSAP because it depends on the lerped value.
gsap.timeline({
  scrollTrigger: { trigger: '#hero', start: 'top top', end: '+=100%', scrub: true },
}).to(state.cameraZ, { target: 15, ease: 'none' }, 0);

// In tick(), AFTER the lerp loop has updated state.*.current:
const z = state.cameraZ.current;
state.cameraFov.target = 2 * Math.atan(subjectSize / (2 * z)) * (180 / Math.PI);
camera.fov = state.cameraFov.current;
camera.updateProjectionMatrix();
camera.position.z = z;
```

### How it works

When camera Z grows, the projection naturally shrinks the subject. To keep it the same screen size, FOV must widen by the inverse trig relationship `2 * atan(size / (2 * distance))`. The background, having a different distance, distorts visibly — that's the dolly zoom signature.

### Tweaks

- `subjectSize` larger → effect more aggressive (more background warp).
- Scroll range shorter (e.g. `+=50%`) → faster, more nauseating. Tune to your audience.

### See also

- Pattern #4 for a similar but non-scrolled cinematic move.
- `references/SHADERS.md` § "Background warp" if you want extra distortion.

---

## #2 — Spline-following camera

**Use when:** Room walkthrough, flyover, narrative path. Camera traces a designed curve.
**Cost:** Low (one `getPointAt` per frame).
**Dependencies:** Lerp loop, ScrollTrigger.

### The code

```js
const path = new THREE.CatmullRomCurve3([
  new THREE.Vector3( 0, 1.6,  8),
  new THREE.Vector3( 4, 1.6,  4),
  new THREE.Vector3( 4, 1.6, -2),
  new THREE.Vector3(-2, 1.6, -6),
  new THREE.Vector3(-2, 1.6, -10),
], false, 'catmullrom', 0.5);  // tension 0.5 = smooth

const lookAhead = 0.02;        // sample slightly ahead for tangent

// In tick(), drive `t` from scroll progress (0..1)
const t = THREE.MathUtils.clamp(state.scrollProgress.current, 0, 1);
const pos = path.getPointAt(t);
const aim = path.getPointAt(Math.min(t + lookAhead, 1));

camera.position.copy(pos);
camera.lookAt(aim);
```

### How it works

`CatmullRomCurve3` builds a smooth spline through the control points. `getPointAt(t)` is **arc-length parameterized** (constant speed regardless of point spacing) when you call `getPointAt`, vs `getPoint(t)` which is faster but uneven. Always use `getPointAt` for camera paths.

### Tweaks

- Add a third path for `up` vectors if you need tilt: `camera.up.copy(upPath.getPointAt(t))`.
- Visualize the path during dev: `scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(path.getPoints(100)), new THREE.LineBasicMaterial({ color: 0xff00ff })));`. Remove before shipping.

### See also

- Pattern #3 for adding mouse-driven micro-movement on top of the spline.

---

## #3 — Mouse parallax (depth-aware)

**Use when:** Adding life to a hero scene. Different depth layers should drift different amounts.
**Cost:** Trivial.
**Dependencies:** Lerp loop, mousemove listener.

### The code

```js
// Mousemove handler (NDC-style: -1..1 on each axis)
window.addEventListener('mousemove', (e) => {
  state.mouseX.target = (e.clientX / window.innerWidth) * 2 - 1;
  state.mouseY.target = -((e.clientY / window.innerHeight) * 2 - 1);
});

// In tick(): apply parallax. The strength multiplier is the "depth weight".
camera.position.x = baseX + state.mouseX.current * 0.30;
camera.position.y = baseY + state.mouseY.current * 0.20;

// For OBJECTS that should react in opposite direction (foreground feels closer):
foregroundObj.position.x = -state.mouseX.current * 0.5;
backgroundObj.position.x = -state.mouseX.current * 0.1;
```

### How it works

Mouse position normalized to [-1, 1]. The lerp loop dampens. Multipliers express how strongly each element responds — closer objects use larger multipliers, distant ones use smaller. The opposing sign on object position creates a parallax that mimics looking through a window.

### Tweaks

- Multiplier `0.30` for camera is gentle — bump to `0.6` for more drama.
- Disable on touch: `if (window.matchMedia('(pointer: coarse)').matches) return;`.

### See also

- Pattern #19 for hover-specific magnetic effects on individual elements.

---

## #4 — Cinematic intro reveal

**Use when:** First load. Camera dollies in, subject scales up, fog clears. The opening shot.
**Cost:** Runs once.
**Dependencies:** GSAP.

### The code

```js
// Set initial state
camera.position.set(0, 5, 25);
camera.fov = 60;
camera.updateProjectionMatrix();
hero.scale.setScalar(0);
scene.fog = new THREE.FogExp2(0x000000, 0.15);

// Wait for first asset load + first paint, then play
function playIntro() {
  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

  tl.to(camera.position, { x: 0, y: 1.2, z: 5, duration: 2.4 }, 0)
    .to(camera, { fov: 35, duration: 2.4, onUpdate: () => camera.updateProjectionMatrix() }, 0)
    .to(hero.scale, { x: 1, y: 1, z: 1, duration: 1.6, ease: 'back.out(1.4)' }, 0.3)
    .to(scene.fog, { density: 0.02, duration: 2.4 }, 0)
    .add(() => document.body.classList.add('intro-done'));  // unlock UI

  return tl;
}
```

### How it works

GSAP runs a one-shot timeline that mutates camera, hero scale, and fog density together. `power3.out` is the cinematic standard — fast at first, slow at the end. `back.out(1.4)` overshoots slightly for the hero, giving a "settle" feel. CSS class flip at the end gates UI from appearing too early.

### Tweaks

- Total duration `2.4s` is the upper bound for "engaging". Below `1.5s` feels rushed; above `3s` users tab away.
- Disable for users who scrolled before intro finished: `if (window.scrollY > 0) tl.progress(1);`.

### See also

- Pattern #32 for gating intro behind preload completion.

---

## #5 — Glass with `MeshPhysicalMaterial` (built-in, r170)

**Use when:** Glass orbs, refractive products, "premium" hero objects.
**Cost:** **Medium** — transmission re-samples scene behind the object once per frame.
**Dependencies:** None — three.js core. (Does NOT use `MeshTransmissionMaterial` — that material is from `@pmndrs/drei-vanilla`, not three core.)

### The code

```js
const glass = new THREE.MeshPhysicalMaterial({
  color: 0xffffff,
  transmission: 1.0,                              // 0..1
  thickness: 0.6,                                 // refraction strength
  roughness: 0.05,                                // surface polish
  ior: 1.5,                                       // glass=1.5, water=1.33, diamond=2.4
  dispersion: 1.2,                                // r166+ — chromatic edge (per-wavelength IOR)
  attenuationColor: new THREE.Color(0xeaf2ff),    // tint applied through thickness
  attenuationDistance: 1.6,
  metalness: 0.0,
  envMapIntensity: 1.3,
});

const orb = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 64), glass);
scene.add(orb);

// REQUIRED: needs scene.environment (HDRI or RoomEnvironment). See pattern #9.
```

### How it works

`MeshPhysicalMaterial` extends `MeshStandardMaterial` with transmission (rendering the scene behind the object into a buffer and refracting it through the surface) and `dispersion` (r166+) which varies the IOR slightly per RGB channel — the prism / chromatic-edge look that drei's `MeshTransmissionMaterial` made famous, now built into three.

### Tweaks

- `thickness 0.1` → thin glass, `thickness 2.0` → thick crystal.
- `roughness 0.05` → polished, `0.3` → frosted.
- `dispersion 0.5` → subtle edge color, `2.0` → strong prism. Above 3.0 looks unrealistic.
- Mobile: set `dispersion: 0` (saves three samples) and downscale `thickness`.
- Multiple glass objects → use `material.thickness` and `material.transmission` separately per material instance to avoid shared state issues.

### When you actually need `MeshTransmissionMaterial` (drei-vanilla)

Three built-in covers ~95% of cases. Reach for drei's `MeshTransmissionMaterial` only when you need:
- `temporalDistortion` (animated IOR drift for "alive" glass feel)
- `distortion` + `distortionScale` (surface-level vertex distortion)
- Per-mesh real backbuffer textures (built-in transmission samples once per frame; drei can sample per-object)

To use drei: `npm i drei-vanilla three-mesh-bvh` and import `MeshTransmissionMaterial` from `drei-vanilla`. Add both to your importmap. The skill's templates use built-in only.

### See also

- Pattern #9 for HDRI (mandatory for any `metalness > 0` or `transmission > 0`).
- `references/POST_PROCESSING.md` § "Glass + bloom interaction" — bloom can wash glass out; tune `bloom.threshold` to 0.9+ when the scene has glass.

---

## #6 — Iridescent metal

**Use when:** Soap-bubble sheen, oil-slick metals, modern phone showcases.
**Cost:** Low.
**Dependencies:** None (uses built-in `MeshPhysicalMaterial`).

### The code

```js
const iridescent = new THREE.MeshPhysicalMaterial({
  color: 0xffffff,
  metalness: 1.0,
  roughness: 0.2,
  iridescence: 1.0,
  iridescenceIOR: 1.3,
  iridescenceThicknessRange: [100, 800],   // nm
  envMapIntensity: 1.2,
});

// REQUIRED: needs HDRI (metalness > 0). See pattern #9.
```

### How it works

`iridescence` enables thin-film interference shading. The thickness range is in **nanometers** — visible light is 380–750 nm. Going outside `[100, 1200]` produces colors that don't exist in real iridescence and look fake.

### Tweaks

- `iridescenceIOR 1.3` → soap bubble. `1.5` → oil slick. `2.4` → diamond-ish.
- Animate `iridescenceThicknessRange` for a shimmering effect: `material.iridescenceThicknessRange = [100, 200 + Math.sin(t) * 600]`.

### See also

- Pattern #7 for cheaper fresnel-only alternative.
- Pattern #9 for HDRI.

---

## #7 — Holographic / fresnel rim

**Use when:** Sci-fi panels, "holographic" UI, character outlines, edge-glow on hero objects.
**Cost:** Trivial (one extra dot product in shader).
**Dependencies:** Custom shader (`onBeforeCompile` patch).

### The code

```js
const baseMat = new THREE.MeshStandardMaterial({ color: 0x000000, metalness: 0.5, roughness: 0.4 });

baseMat.onBeforeCompile = (shader) => {
  shader.uniforms.uRimColor = { value: new THREE.Color(0x66ccff) };
  shader.uniforms.uRimPower = { value: 2.5 };
  shader.uniforms.uRimIntensity = { value: 1.5 };

  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <output_fragment>',
    `
    vec3 viewDir = normalize(vViewPosition);
    float fresnel = pow(1.0 - max(dot(normalize(vNormal), viewDir), 0.0), uRimPower);
    gl_FragColor.rgb += uRimColor * fresnel * uRimIntensity;
    #include <output_fragment>
    `,
  );
  baseMat.userData.shader = shader;  // keep reference for live tweaks
};
```

### How it works

Fresnel: `pow(1 - dot(N, V), p)` — when the surface normal points away from the camera (rim), the dot product approaches 0 and the term approaches 1. Powering it sharpens the falloff. Adding it to `gl_FragColor` after lighting gives an additive edge glow.

### Tweaks

- `uRimPower 1.0` → soft halo. `5.0` → razor edge.
- Animate `uRimIntensity` over time for breathing effect.
- For "scan line" holographic, multiply by `sin(uTime + vWorldPosition.y * 30.0)`.

### See also

- `references/SHADERS.md` § "Fresnel" for the standalone GLSL function.

---

## #8 — Animated UV scroll

**Use when:** Flowing water, conveyor belts, energy beams, stream-of-light effects.
**Cost:** Trivial.
**Dependencies:** Texture with `wrapS = wrapT = THREE.RepeatWrapping`.

### The code

```js
const tex = await new THREE.TextureLoader().loadAsync('/textures/stripe.png');
tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
tex.repeat.set(4, 1);

const flow = new THREE.MeshBasicMaterial({ map: tex, transparent: true });

// In tick():
tex.offset.x -= delta * 0.5;   // negative = left-to-right flow
```

### How it works

`offset.x -= delta * speed` advances the texture sampling origin every frame. Combined with `RepeatWrapping`, it scrolls indefinitely without seams. Multiplying by `delta` is essential for framerate independence.

### Tweaks

- Diagonal: change `tex.offset.y` too.
- Pulse: `tex.offset.x = Math.sin(time) * 0.5`.
- For non-tiling textures, use a shader uniform `uTime` and offset in the fragment instead.

### See also

- `references/SHADERS.md` § "Time-driven UV" for the shader-based version that doesn't need a texture file.

---

## #9 — HDRI loader (RGBELoader + PMREM)

**Use when:** Always. Any scene with `metalness > 0`, glass, or polished plastic needs this.
**Cost:** One-time at load (PMREM convolution is ~50–200ms).
**Dependencies:** `RGBELoader`, `PMREMGenerator`.

### The code

```js
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

async function loadHDRI(renderer, scene, url) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();

  const tex = await new RGBELoader().setDataType(THREE.HalfFloatType).loadAsync(url);
  const envMap = pmrem.fromEquirectangular(tex).texture;

  scene.environment = envMap;
  // scene.background = envMap;     // optional; usually leave null and use a designed background

  tex.dispose();
  pmrem.dispose();

  return envMap;
}

// Usage
await loadHDRI(renderer, scene, 'https://example.com/hdri/studio_small_03_1k.hdr');
```

### How it works

`.hdr` is an equirectangular high-dynamic-range image. PMREM (Pre-filtered Mipmapped Radiance Environment Map) pre-convolves it at multiple roughness levels so any material can sample the right blur for its roughness. Without PMREM, materials look noisy or banded.

### Tweaks

- 1K HDRI = ~2–3 MB, fine for web. Don't ship 4K (~30+ MB).
- `HalfFloatType` is the right balance of quality/memory. `FloatType` doubles VRAM for negligible quality gain.
- For known camera angles, you can rotate the env: `scene.environmentRotation = new THREE.Euler(0, Math.PI / 2, 0)` (three r167+).

### See also

- `assets/hdri/README.md` for free HDRI sources.
- Pattern #11 for the synthetic fallback when you can't ship a file.

---

## #10 — Three-point cinematic lighting

**Use when:** Even with HDRI, you often want directional shadows and color separation. Always layer this on top of HDRI.
**Cost:** Three lights; shadows from key only.

### The code

```js
const lighting = new THREE.Group();
lighting.name = 'lighting';

const key = new THREE.DirectionalLight(0xffeedd, 1.5);
key.position.set(5, 8, 5);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 0.5;
key.shadow.camera.far = 25;
key.shadow.bias = -0.0001;
const d = 8;
key.shadow.camera.left = -d;
key.shadow.camera.right = d;
key.shadow.camera.top = d;
key.shadow.camera.bottom = -d;

const fill = new THREE.DirectionalLight(0x88aaff, 0.4);  // cool fill
fill.position.set(-5, 3, 4);

const rim = new THREE.DirectionalLight(0xffffff, 0.8);   // backlight
rim.position.set(0, 6, -8);

lighting.add(key, fill, rim);
scene.add(lighting);
```

### How it works

Cinema convention: warm key (sun-like), cool fill (sky-like), rim from behind (separation). The intensity ratios `1.5 : 0.4 : 0.8` produce a recognizable studio look. Color contrast (warm key vs cool fill) is more important than absolute color values.

### Tweaks

- Drop `fill` for harsh / dramatic. Keep all three for "product photography".
- `key.shadow.bias` of `-0.0001` is a safe default. If you see shadow acne, push to `-0.001`.

### See also

- Pattern #12 for the matching shadow catcher under the subject.

---

## #11 — RoomEnvironment fallback

**Use when:** You can't ship an HDRI file (offline demo, weight budget) but still need believable PBR shading.
**Cost:** One-time at boot.
**Dependencies:** `three/addons/environments/RoomEnvironment.js`.

### The code

```js
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
pmrem.dispose();
```

### How it works

`RoomEnvironment` is a synthetic procedural scene of colored panels approximating a photo studio. PMREM convolves it the same way as a real HDRI. Result is ~80% as good as a real HDRI, with zero file weight.

### Tweaks

- The `0.04` second arg is sigma blur — keep low for crisper reflections.
- For dark/moody scenes, fall back to a custom mini-scene with one or two emissive planes instead.

### See also

- Pattern #9 for the real HDRI version.

---

## #12 — Soft shadow catcher

**Use when:** Hero object floating against a designed background — you want a contact shadow without a visible plane.
**Cost:** One additional draw.
**Dependencies:** `ShadowMaterial`.

### The code

```js
const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(20, 20),
  new THREE.ShadowMaterial({ opacity: 0.35 }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -1;
floor.receiveShadow = true;
scene.add(floor);

// Renderer setup (do once at boot):
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.VSMShadowMap;  // softest type
```

### How it works

`ShadowMaterial` is invisible except where shadows fall. With `VSMShadowMap` (Variance Shadow Map), shadows are softened naturally without needing PCF samples. The `0.35` opacity prevents a hard black blob and matches realistic ambient occlusion strength.

### Tweaks

- `opacity 0.5+` looks fake / cartoony.
- For colored shadows (e.g. blue under a glass orb): use `MeshBasicMaterial({ color, transparent: true, opacity })` and a separate shadow-only render pass (advanced).

### See also

- Pattern #10 for the directional light that casts onto this catcher.

---

## #13 — Instanced mesh (10k objects)

**Use when:** Repeating geometry — debris, asteroids, crowds, particle-like 3D.
**Cost:** One draw call regardless of count. Memory ~80 bytes per instance.

### The code

```js
const geom = new THREE.IcosahedronGeometry(0.1, 0);
const mat = new THREE.MeshStandardMaterial({ color: 0x99aaff, roughness: 0.6 });
const COUNT = 10_000;
const mesh = new THREE.InstancedMesh(geom, mat, COUNT);
mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

const dummy = new THREE.Object3D();
for (let i = 0; i < COUNT; i++) {
  dummy.position.set(
    (Math.random() - 0.5) * 50,
    (Math.random() - 0.5) * 50,
    (Math.random() - 0.5) * 50,
  );
  dummy.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
  dummy.scale.setScalar(0.5 + Math.random() * 1.5);
  dummy.updateMatrix();
  mesh.setMatrixAt(i, dummy.matrix);
}
mesh.instanceMatrix.needsUpdate = true;
scene.add(mesh);

// Per-instance color (optional)
mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(COUNT * 3), 3);
for (let i = 0; i < COUNT; i++) {
  mesh.instanceColor.setXYZ(i, Math.random(), Math.random(), Math.random());
}
mesh.instanceColor.needsUpdate = true;
```

### How it works

The GPU draws all instances in one call. Each instance has a unique 4x4 matrix (and optional color). For large counts, this is the only viable approach — naive `for (let i = 0; i < 10_000; i++) scene.add(...)` causes the JS-side overhead of 10k draw calls and crashes mobile browsers.

### Tweaks

- For animated instances: update `dummy.position`, recompute `matrix`, `setMatrixAt(i, matrix)`, set `instanceMatrix.needsUpdate = true` after the loop.
- Beyond ~50k instances, consider GPGPU compute (`GPUComputationRenderer` or transform feedback).

### See also

- Pattern #14 for points (cheaper than instanced mesh when you only need a dot).

---

## #14 — Particle field with custom shader

**Use when:** Atmospheric dust, dreamlike fields, scroll-reactive star/dust scenes.
**Cost:** Very low for points + custom shader.

### The code

```js
const COUNT = 5000;
const positions = new Float32Array(COUNT * 3);
const sizes = new Float32Array(COUNT);
for (let i = 0; i < COUNT; i++) {
  positions[i * 3 + 0] = (Math.random() - 0.5) * 30;
  positions[i * 3 + 1] = (Math.random() - 0.5) * 30;
  positions[i * 3 + 2] = (Math.random() - 0.5) * 30;
  sizes[i] = 0.5 + Math.random() * 1.5;
}

const geometry = new THREE.BufferGeometry();
geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

const material = new THREE.ShaderMaterial({
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
  uniforms: {
    uTime: { value: 0 },
    uColor: { value: new THREE.Color(0xffffff) },
    uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
  },
  vertexShader: `
    attribute float size;
    uniform float uTime;
    uniform float uPixelRatio;
    varying float vAlpha;

    void main() {
      vec3 pos = position;
      pos.y += sin(uTime + position.x * 0.5) * 0.2;  // gentle drift

      vec4 mvPos = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPos;
      gl_PointSize = size * uPixelRatio * (60.0 / -mvPos.z);
      vAlpha = clamp(1.0 - (-mvPos.z / 30.0), 0.0, 1.0);
    }
  `,
  fragmentShader: `
    precision mediump float;
    uniform vec3 uColor;
    varying float vAlpha;

    void main() {
      vec2 uv = gl_PointCoord - 0.5;
      float d = length(uv);
      float circle = smoothstep(0.5, 0.0, d);
      gl_FragColor = vec4(uColor, circle * vAlpha);
    }
  `,
});

const points = new THREE.Points(geometry, material);
scene.add(points);

// In tick():
material.uniforms.uTime.value += delta;
```

### How it works

Each point is a billboarded quad with size in pixels. The vertex shader scales by `1/-z` (perspective compensation) and `uPixelRatio` (HiDPI). The fragment shader makes a soft circle via `smoothstep` on distance from center. Additive blending lets points overlap into bright clusters.

### Tweaks

- `AdditiveBlending` looks magical but white-out on bright backgrounds. For dark scenes only.
- For star-twinkle: multiply alpha by `0.5 + 0.5 * sin(uTime * speed + position.x)`.
- Mobile: drop COUNT to 1500 and you'll save ~20% GPU.

### See also

- Pattern #13 if you need true geometry per particle.
- `references/SHADERS.md` § "Noise" for non-uniform distributions.

---

## #15 — GLB loader + Draco + Meshopt

**Use when:** Loading any model from Blender or sketchfab. ALWAYS use compression.
**Cost:** Decode is async. Compressed files are 5–15x smaller.

### The code

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const draco = new DRACOLoader();
// Use the decoder bundled WITH this exact three version — guarantees API match.
// (Avoid gstatic CDN versions, which can drift from three's expected ABI.)
draco.setDecoderPath('https://unpkg.com/three@0.170.0/examples/jsm/libs/draco/');
draco.setDecoderConfig({ type: 'js' });  // 'wasm' for ~30% faster, but bigger initial cost

const loader = new GLTFLoader();
loader.setDRACOLoader(draco);
loader.setMeshoptDecoder(MeshoptDecoder);

const gltf = await loader.loadAsync('/models/hero.glb');
gltf.scene.traverse((child) => {
  if (child.isMesh) {
    child.castShadow = true;
    child.receiveShadow = true;
  }
});
scene.add(gltf.scene);

// Cleanup when done with this scene
function cleanupLoaders() {
  draco.dispose();
}
```

### How it works

Draco compresses geometry; Meshopt compresses everything else (animations, morph targets, vertex attributes). A typical 5 MB GLB drops to 400 KB Draco, 200 KB Meshopt+Draco. Both decoders run in JS; the Draco decoder can be `wasm` for speed at the cost of an additional ~150 KB initial download.

### Tweaks

- For very large scenes (rooms, environments), use Meshopt over Draco — Draco has a per-mesh fixed cost overhead.
- Always `gltf.scene.traverse` and set shadow flags — they default to `false` and shadows silently don't work.

### See also

- `references/BLENDER_PIPELINE.md` for the export config that produces Draco-compressed GLB.

---

## #16 — KTX2 texture loader

**Use when:** Texture-heavy scenes (multiple 2K+ albedo/normal maps). Reduces VRAM by ~75% vs JPG.
**Cost:** Async transcode at load.
**Dependencies:** `three/addons/loaders/KTX2Loader.js`, `basis_transcoder.js`, KTX2 files (you must produce these — see below).

### The code

```js
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';

const ktx2 = new KTX2Loader()
  .setTranscoderPath('https://unpkg.com/three@0.170.0/examples/jsm/libs/basis/')
  .detectSupport(renderer);

// Use with GLTFLoader:
loader.setKTX2Loader(ktx2);

// Or standalone:
const tex = await ktx2.loadAsync('/textures/diffuse.ktx2');
```

### Realistic note — why most projects skip this

KTX2 requires you to **produce** the files. The toolchain is `toktx` (from KTX-Software) or `gltf-transform`. There is no "save as KTX2" in any image editor. The encode is slow (10–60 seconds per texture).

**Practical guidance:** Use KTX2 only when you have ≥3 textures of ≥2048px and your VRAM budget is tight (e.g. mobile-heavy traffic). For most Awwwards sites with 1–2 hero textures, **compressed JPG/WebP** is simpler:

```js
// JPG/WebP path — simpler, fine for most projects
const tex = await new THREE.TextureLoader().loadAsync('/textures/diffuse.webp');
tex.colorSpace = THREE.SRGBColorSpace;   // for albedo only — not normal/roughness
tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
```

### How it works

KTX2 stores textures in GPU-native formats (BC7, ASTC, ETC2). The transcoder picks the right format based on the GPU. JPG/WebP must be decoded to RGBA on the CPU, then re-uploaded — KTX2 uploads directly.

### See also

- `references/BLENDER_PIPELINE.md` § "KTX2 export with gltf-transform" for the production path.

---

## #17 — Mesh morphing on scroll (two approaches)

**Use when:** Object transforms shape on scroll — sphere → cube, abstract shape morph.
**Cost:** Approach A is cheap (built-in). Approach B is mid (custom shader).
**Dependencies:** A: morph targets exported from Blender. B: two geometries with same vertex count.

### Approach A — Three.js morph target influences (simpler, requires Blender setup)

```js
// GLB exported from Blender with shape keys → these become morph targets
const mesh = gltf.scene.getObjectByName('hero');
// mesh.morphTargetInfluences is an array of weights, one per shape key

gsap.to(mesh.morphTargetInfluences, {
  0: 1.0,      // morph target index 0 → fully active
  duration: 1,
  scrollTrigger: { trigger: '#section', start: 'top center', end: 'bottom center', scrub: true },
});
```

### Approach B — Vertex shader lerp between two geometries (no Blender)

The trick: start from the SAME base geometry (so vertex order and count match), then displace one of them. This guarantees the morph works.

```js
// Same base → same vertex count, same vertex order
const geomA = new THREE.IcosahedronGeometry(1, 4);   // 642 vertices
const geomB = new THREE.IcosahedronGeometry(1, 4);   // 642 vertices, identical

// Displace B to make it visually different — knobby blob
const posB = geomB.attributes.position;
for (let i = 0; i < posB.count; i++) {
  const x = posB.getX(i), y = posB.getY(i), z = posB.getZ(i);
  const n = (Math.sin(x * 5) + Math.cos(z * 5) + Math.sin(y * 5)) * 0.18;
  posB.setXYZ(i, x + x * n, y + y * n, z + z * n);
}
posB.needsUpdate = true;
geomB.computeVertexNormals();

// Pass B's positions as a custom attribute on A
geomA.setAttribute('position2', new THREE.BufferAttribute(posB.array.slice(), 3));

const mat = new THREE.ShaderMaterial({
  uniforms: { uMix: { value: 0 } },
  vertexShader: `
    attribute vec3 position2;
    uniform float uMix;
    void main() {
      vec3 pos = mix(position, position2, uMix);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    void main() { gl_FragColor = vec4(0.6, 0.7, 1.0, 1.0); }
  `,
});

const morphMesh = new THREE.Mesh(geomA, mat);
scene.add(morphMesh);

// In tick(), drive uMix from scroll:
mat.uniforms.uMix.value = state.scrollProgress.current;
```

**Important:** if you really want two unrelated shapes (sphere → cube), use `BufferGeometryUtils.mergeVertices()` and resample both to a common vertex count, or pre-bake both meshes in Blender and export with shape keys (Approach A).

### When to use which

- **Approach A** if your designer already works in Blender and produces shape keys. Cleanest pipeline.
- **Approach B** for primitive-to-primitive morphs you can do in code. No Blender round-trip.
- For B, **vertex count must match exactly**. Easiest way: subdivide both to a common count (e.g. both at 642 verts).

### See also

- `references/BLENDER_PIPELINE.md` § "Shape keys for GLB morph targets".

---

## #18 — Lerped custom cursor element

**Use when:** Bonhomme/Lusion-style signature cursor (dot that follows mouse, ring that lags behind).
**Cost:** Trivial.

### The code

```html
<div class="cursor-dot"></div>
<div class="cursor-ring"></div>
```

```css
.cursor-dot, .cursor-ring {
  position: fixed; top: 0; left: 0; pointer-events: none;
  border-radius: 50%; transform: translate(-50%, -50%);
  z-index: 9999; mix-blend-mode: difference;
}
.cursor-dot  { width: 6px;  height: 6px;  background: #fff; }
.cursor-ring { width: 36px; height: 36px; border: 1px solid #fff; transition: transform 0.2s; }
.cursor-ring.hover { transform: translate(-50%, -50%) scale(1.6); }

@media (pointer: coarse) { .cursor-dot, .cursor-ring { display: none; } }
body { cursor: none; }
```

```js
const dot  = document.querySelector('.cursor-dot');
const ring = document.querySelector('.cursor-ring');
const cursor = { x: 0, y: 0, dx: 0, dy: 0, rx: 0, ry: 0 };

window.addEventListener('mousemove', (e) => {
  cursor.x = e.clientX; cursor.y = e.clientY;
});

function tickCursor() {
  cursor.dx += (cursor.x - cursor.dx) * 0.4;   // dot fast follow
  cursor.dy += (cursor.y - cursor.dy) * 0.4;
  cursor.rx += (cursor.x - cursor.rx) * 0.12;  // ring slow follow
  cursor.ry += (cursor.y - cursor.ry) * 0.12;
  dot.style.transform  = `translate(${cursor.dx}px, ${cursor.dy}px) translate(-50%, -50%)`;
  ring.style.transform = `translate(${cursor.rx}px, ${cursor.ry}px) translate(-50%, -50%)`;
  requestAnimationFrame(tickCursor);
}
tickCursor();

// Hover effect
document.querySelectorAll('a, button, [data-cursor-hover]').forEach((el) => {
  el.addEventListener('mouseenter', () => ring.classList.add('hover'));
  el.addEventListener('mouseleave', () => ring.classList.remove('hover'));
});
```

### How it works

Two elements; the dot tracks tightly, the ring lags. Different ease values produce the offset that gives the cursor "weight". `mix-blend-mode: difference` makes the cursor visible against any background. The `pointer: coarse` media query hides the cursor on touch devices where it doesn't apply.

### Tweaks

- For deeper personality: scale ring on click, color it on link hover, or warp shape with a CSS clip-path.
- For 3D-aware cursor (intersects scene): pattern #20 (raycaster).

### See also

- Pattern #19 for the "magnetic attract" extension.

---

## #19 — Magnetic hover (3D button attract)

**Use when:** Buttons/links pull toward the cursor when nearby. Bonhomme signature.
**Cost:** Trivial.

### The code

```js
function magnetize(el, strength = 0.4, radius = 80) {
  const onMove = (e) => {
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = e.clientX - cx;
    const dy = e.clientY - cy;
    const dist = Math.hypot(dx, dy);

    if (dist < radius) {
      const tx = dx * strength;
      const ty = dy * strength;
      gsap.to(el, { x: tx, y: ty, duration: 0.4, ease: 'power3.out' });
    } else {
      gsap.to(el, { x: 0, y: 0, duration: 0.6, ease: 'elastic.out(1, 0.4)' });
    }
  };

  window.addEventListener('mousemove', onMove);
  return () => window.removeEventListener('mousemove', onMove);
}

// Usage
document.querySelectorAll('[data-magnetic]').forEach((el) => magnetize(el));
```

### How it works

Listens to global mousemove. When cursor is within `radius` pixels of the element's center, GSAP tweens the element toward the cursor by `strength * distance`. Outside the radius, returns to origin with elastic ease. The ease change between approach and release is the soul of the effect.

### Tweaks

- `strength 0.2` → subtle. `0.6` → "sticky". Above `0.7` looks broken.
- For 3D meshes: same logic, but `dx/dy` against unprojected mesh position, and apply to `mesh.position`.

### See also

- Pattern #18 for the cursor that pairs with this.

---

## #20 — Raycaster + GPU picking alternative

**Use when:** Detecting which 3D object the cursor is over.
**Cost:** Raycaster: O(n × triangles). GPU picking: O(1).

### Approach A — Raycaster, filtered to interactive layer

```js
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const interactive = [];   // array of meshes you want to test

window.addEventListener('mousemove', (e) => {
  pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
  pointer.y = -(e.clientY / window.innerHeight) * 2 + 1;
});

// In tick():
raycaster.setFromCamera(pointer, camera);
const hits = raycaster.intersectObjects(interactive, false);   // false: not recursive
if (hits.length) {
  const obj = hits[0].object;
  // hover state
}
```

### Approach B — GPU picking (faster for many objects)

```js
// Render the scene to an off-screen target, but each interactive object
// gets a unique flat color = its ID. Read back one pixel under the cursor.

const pickRT = new THREE.WebGLRenderTarget(1, 1);
const pickScene = new THREE.Scene();
const pickMaterials = new Map();   // mesh → color-coded material
let nextId = 1;

function registerForPicking(mesh) {
  const r = (nextId & 0xff) / 255;
  const g = ((nextId >> 8) & 0xff) / 255;
  const b = ((nextId >> 16) & 0xff) / 255;
  const pickMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(r, g, b) });
  pickMaterials.set(mesh, { id: nextId, material: pickMat });
  nextId++;
}

function pick(x, y) {
  // Set pick materials, render 1×1 region, read pixel, restore
  for (const [mesh, { material }] of pickMaterials) {
    mesh.userData._origMat = mesh.material;
    mesh.material = material;
  }
  renderer.setRenderTarget(pickRT);
  camera.setViewOffset(window.innerWidth, window.innerHeight, x, y, 1, 1);
  renderer.render(scene, camera);
  camera.clearViewOffset();
  renderer.setRenderTarget(null);

  const buf = new Uint8Array(4);
  renderer.readRenderTargetPixels(pickRT, 0, 0, 1, 1, buf);
  const id = buf[0] | (buf[1] << 8) | (buf[2] << 16);

  for (const [mesh] of pickMaterials) {
    mesh.material = mesh.userData._origMat;
    delete mesh.userData._origMat;   // prevent stale refs accumulating across pick() calls
  }
  return id;
}
```

### When to use which

- **Raycaster** for ≤ ~30 interactive meshes. Simpler, works fine.
- **GPU picking** for hundreds of meshes (e.g. clickable city buildings, particle interaction).
- **Neither** if you can use UV-based hit detection (e.g. texture-based UI in 3D space — fastest of all).

### See also

- Pattern #18 / #19 for cursor and magnetic interactions.

---

## #21 — Touch-friendly drag rotate

**Use when:** Mobile users should be able to spin a hero object.
**Cost:** Trivial.

### The code

```js
let isDragging = false;
let lastX = 0, lastY = 0;
const SENSITIVITY = 0.005;

const start = (x, y) => { isDragging = true; lastX = x; lastY = y; };
const move = (x, y) => {
  if (!isDragging) return;
  const dx = x - lastX;
  const dy = y - lastY;
  state.heroRotY.target += dx * SENSITIVITY;
  state.heroRotX.target = THREE.MathUtils.clamp(
    state.heroRotX.target + dy * SENSITIVITY, -0.5, 0.5,
  );
  lastX = x; lastY = y;
};
const end = () => { isDragging = false; };

// Mouse
canvas.addEventListener('mousedown', (e) => start(e.clientX, e.clientY));
window.addEventListener('mousemove', (e) => move(e.clientX, e.clientY));
window.addEventListener('mouseup', end);

// Touch
canvas.addEventListener('touchstart', (e) => {
  start(e.touches[0].clientX, e.touches[0].clientY);
}, { passive: true });
window.addEventListener('touchmove', (e) => {
  move(e.touches[0].clientX, e.touches[0].clientY);
}, { passive: true });
window.addEventListener('touchend', end);
```

### How it works

Drag delta is added to the lerp target. The lerp loop dampens, so quick flicks settle smoothly. Clamping `heroRotX` prevents the user from flipping the object upside down. `passive: true` on touch listeners avoids fighting native scroll on mobile.

### Tweaks

- Add inertia: store `velX`/`velY` from drag, and on `end`, decay them while feeding `state.heroRotY.target`.
- Disable on `if (e.target.closest('.scroll-section'))` to avoid hijacking text-area scrolling.

---

## #22 — Lenis init + ScrollTrigger bridge

See `ARCHITECTURE.md` § 3 for the canonical wiring. Reproduced here for copy-paste:

```js
import Lenis from 'lenis';
import gsap from 'gsap';
import ScrollTrigger from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  smoothWheel: true,
  prevent: () => false,   // Lenis 1.1 requires this — see ARCHITECTURE.md § 3
});

lenis.on('scroll', ScrollTrigger.update);

gsap.ticker.add((time) => lenis.raf(time * 1000));
gsap.ticker.lagSmoothing(0);
```

### See also

- `ARCHITECTURE.md` § 3 for the full architectural reasoning.

---

## #23 — Scroll-pinned section

**Use when:** A section stays in view while related content animates over it (camera move, text fade chain).

```js
ScrollTrigger.create({
  trigger: '#pinned-section',
  start: 'top top',
  end: '+=200%',     // pin lasts for 2 viewport heights of scroll
  pin: true,
  pinSpacing: true,  // adds the equivalent space below to keep document length correct
  scrub: true,
  onUpdate: (self) => {
    state.pinnedProgress.target = self.progress;
  },
});
```

### Tweaks

- `pinSpacing: false` if pinning a fixed-position canvas overlay (no extra space needed).
- For React/Vue, **always** call `ScrollTrigger.refresh()` after mount so it measures correct heights.

---

## #24 — Horizontal scroll section

```js
const inner = document.querySelector('.h-scroll-inner');

gsap.to(inner, {
  x: () => -(inner.scrollWidth - window.innerWidth),
  ease: 'none',
  scrollTrigger: {
    trigger: '.h-scroll',
    start: 'top top',
    end: () => `+=${inner.scrollWidth - window.innerWidth}`,
    pin: true,
    scrub: true,
    invalidateOnRefresh: true,
  },
});
```

```html
<section class="h-scroll">
  <div class="h-scroll-inner">
    <div class="h-panel">A</div>
    <div class="h-panel">B</div>
    <div class="h-panel">C</div>
  </div>
</section>
```

```css
.h-scroll { overflow: hidden; }
.h-scroll-inner { display: flex; will-change: transform; }
.h-panel { flex: 0 0 100vw; height: 100vh; }
```

### Tweaks

- `invalidateOnRefresh: true` recalculates on resize — critical or horizontal scroll breaks on rotation.

---

## #25 — Reveal-on-scroll fade-in (text)

```js
gsap.utils.toArray('[data-reveal]').forEach((el) => {
  gsap.from(el, {
    y: 40,
    opacity: 0,
    duration: 1,
    ease: 'power3.out',
    scrollTrigger: { trigger: el, start: 'top 85%', toggleActions: 'play none none reverse' },
  });
});
```

```html
<h2 data-reveal>Anything you want revealed</h2>
```

### Tweaks

- For staggered word/letter splits, use SplitText (paid GSAP plugin) or manually wrap each word in a `<span>` and target `el.children`.

---

## #26 — requestIdleCallback warmup

**Use when:** You want to pre-decode textures or shaders during browser idle, so first scroll doesn't hitch.

```js
function warmup() {
  // Compile shaders by rendering once before user sees scene
  renderer.compile(scene, camera);

  // Warm up post-processing chain
  composer.render(0.016);
}

if ('requestIdleCallback' in window) {
  requestIdleCallback(warmup, { timeout: 1000 });
} else {
  setTimeout(warmup, 200);
}
```

### How it works

`renderer.compile()` traverses the scene and compiles every shader program without drawing. First real frame is then ~3–4x faster. This is the difference between "hitch on scroll start" and "smooth from frame 1".

---

## #27 — Visibility API pause loop

**Use when:** Always. Saves battery and CPU when user switches tabs.

```js
let running = true;
let rafId;

function tick() {
  if (!running) return;
  // ... update, render
  rafId = requestAnimationFrame(tick);
}

document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    running = false;
    cancelAnimationFrame(rafId);
  } else {
    running = true;
    clock.getDelta();   // discard the giant delta from the pause
    tick();
  }
});

tick();
```

### Why `clock.getDelta()` after resume

`THREE.Clock` accumulates time even while paused. The first `getDelta()` after resume returns the entire pause duration — without discarding, every animation jumps forward by that amount. The discarded read resets the clock.

---

## #28 — Debounced / coalesced resize

See `ARCHITECTURE.md` § 6 — already covered there. Reproduced for copy-paste:

```js
let resizePending = false;
function onResize() {
  if (resizePending) return;
  resizePending = true;
  requestAnimationFrame(() => {
    const w = window.innerWidth, h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    composer.setSize(w, h);
    resizePending = false;
  });
}
window.addEventListener('resize', onResize);
```

---

## #29 — WebGL feature detection

**Use when:** You want to gracefully degrade for older devices or fall back to a static image.

```js
function detectWebGL() {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!gl) return { supported: false, reason: 'no-context' };

    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    const renderer = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : '';
    const isWeak = /SwiftShader|Software|llvmpipe/i.test(renderer);
    return {
      supported: true,
      webgl2: !!canvas.getContext('webgl2'),
      renderer,
      isWeak,
    };
  } catch (e) {
    return { supported: false, reason: e.message };
  }
}

const caps = detectWebGL();
if (!caps.supported || caps.isWeak) {
  document.body.classList.add('no-webgl');
  // Show a static image / video fallback
} else {
  initThreeScene();
}
```

### Tweaks

- For very old devices: reduce post-processing or skip 3D entirely. The site should still tell its story.

---

## #30 — Background gradient mesh

**Use when:** You want a designed background that's richer than `background: linear-gradient(...)` — e.g. animated noise gradient.

```js
const bgGeom = new THREE.PlaneGeometry(2, 2);
const bgMat = new THREE.ShaderMaterial({
  uniforms: { uTime: { value: 0 } },
  vertexShader: `
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = vec4(position, 1.0); }
  `,
  fragmentShader: `
    precision mediump float;
    uniform float uTime;
    varying vec2 vUv;
    vec3 a = vec3(0.05, 0.05, 0.10);
    vec3 b = vec3(0.20, 0.05, 0.30);
    vec3 c = vec3(0.40, 0.10, 0.60);
    void main() {
      float t = vUv.y + sin(vUv.x * 3.0 + uTime * 0.2) * 0.1;
      vec3 col = mix(mix(a, b, smoothstep(0.0, 0.5, t)), c, smoothstep(0.5, 1.0, t));
      gl_FragColor = vec4(col, 1.0);
    }
  `,
  depthTest: false, depthWrite: false,
});

const bg = new THREE.Mesh(bgGeom, bgMat);
bg.frustumCulled = false;
bg.renderOrder = -1;        // render before everything else

// Add to a separate background scene (so it renders fullscreen regardless of camera)
const bgScene = new THREE.Scene();
bgScene.add(bg);

// In tick(), render bg first, then main scene with autoClear false:
renderer.autoClear = false;
renderer.clear();
renderer.render(bgScene, new THREE.Camera());   // identity camera; geometry is in clip space
renderer.render(scene, camera);
```

### How it works

Plane is in clip space (raw NDC, no projection). Identity camera gives a 1:1 mapping. Rendered first with `autoClear = false` on the renderer, so the main scene draws on top. Beats CSS gradients because you can animate it cheaply with `uTime`.

### Important — composer compatibility

The code above bypasses any post-processing pipeline. If you're using `EffectComposer` (bloom, grain, LUT), do NOT call `renderer.render()` directly — it skips the composer. Two valid approaches with a composer:

```js
// Option 1: Bake the gradient into a single MeshBasicMaterial-textured plane
// inside the main scene, with renderOrder = -1. Composer processes it like
// any other mesh.

// Option 2: Add the bg as a separate RenderPass at the start of the composer chain.
// CRITICAL: the second RenderPass must have .clear = false, or it wipes the bg.
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';

const bgPass = new RenderPass(bgScene, new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1));
const mainPass = new RenderPass(scene, camera);
mainPass.clear = false;
mainPass.clearDepth = true;        // do clear depth so foreground renders correctly

composer.addPass(bgPass);
composer.addPass(mainPass);
// ... rest of chain (bloom, vignette, output, grain)
```

Default to Option 1 in most projects.

### See also

- `references/SHADERS.md` § "Smooth gradients without banding".
- `references/POST_PROCESSING.md` § "Background pass ordering".

---

## #31 — CSS3DRenderer text in 3D space

**Use when:** Real HTML/CSS text needs to live "in" the 3D scene with full font fidelity, real selectability, and real accessibility.
**Cost:** Two renderers (WebGL + CSS3D) layered with synced cameras.
**Dependencies:** `three/addons/renderers/CSS3DRenderer.js`.

### The code

```js
import { CSS3DRenderer, CSS3DObject } from 'three/addons/renderers/CSS3DRenderer.js';

const cssRenderer = new CSS3DRenderer();
cssRenderer.setSize(window.innerWidth, window.innerHeight);
cssRenderer.domElement.style.position = 'fixed';
cssRenderer.domElement.style.inset = '0';
cssRenderer.domElement.style.pointerEvents = 'none';   // let canvas under it receive events
document.body.appendChild(cssRenderer.domElement);

const labelEl = document.createElement('div');
labelEl.className = 'scene-label';
labelEl.textContent = 'Hello, world';
labelEl.style.pointerEvents = 'auto';   // re-enable on the actual element

const label = new CSS3DObject(labelEl);
label.position.set(0, 2, 0);
label.scale.setScalar(0.01);   // CSS pixels → world units
scene.add(label);

// In tick(), render BOTH:
renderer.render(scene, camera);
cssRenderer.render(scene, camera);   // same scene + camera; CSS objects extracted automatically
```

### How it works

`CSS3DRenderer` traverses the same scene and applies CSS `transform: matrix3d(...)` to each `CSS3DObject`'s DOM element so it perfectly aligns with where Three.js would draw it. You get real text antialiasing, font ligatures, copy-paste, screen readers — all things WebGL text loses.

### Tweaks

- Layer order matters: WebGL canvas under CSS3D layer for occlusion to look right.
- True occlusion (object hides text) requires writing depth manually — most sites accept that text always renders on top.

### Footnote — when to use Troika instead

If you need text **inside** the WebGL pipeline (occluded by other meshes, post-processed, drawn into a render target, distance-fielded), use [`troika-three-text`](https://github.com/protectwise/troika/tree/main/packages/troika-three-text). It generates SDF text as a real Three.js mesh. Cost: extra dependency, larger bundle.

---

## #32 — Loading screen + asset preloader

**Use when:** Always. Even a 500ms blank canvas feels broken without a loader.

### The code

```html
<div id="preloader">
  <div class="preloader-counter">0</div>
  <div class="preloader-bar"><div class="preloader-fill"></div></div>
</div>
```

```css
#preloader {
  position: fixed; inset: 0; background: #0a0a0e; color: #fff;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  z-index: 9000; transition: opacity 0.6s ease, visibility 0.6s;
}
#preloader.done { opacity: 0; visibility: hidden; }
.preloader-counter { font: 600 4rem/1 system-ui, sans-serif; letter-spacing: -0.04em; }
.preloader-bar { width: 240px; height: 1px; background: rgba(255,255,255,0.1); margin-top: 1rem; }
.preloader-fill { height: 100%; background: #fff; width: 0%; transition: width 0.2s ease; }
```

```js
const manager = new THREE.LoadingManager();
const counter = document.querySelector('.preloader-counter');
const fill = document.querySelector('.preloader-fill');
const preloader = document.getElementById('preloader');

manager.onProgress = (url, loaded, total) => {
  const pct = Math.round((loaded / total) * 100);
  counter.textContent = pct;
  fill.style.width = `${pct}%`;
};

manager.onLoad = () => {
  // Wait one frame so the bar visibly hits 100%, then fade out
  requestAnimationFrame(() => {
    counter.textContent = '100';
    fill.style.width = '100%';
    setTimeout(() => {
      preloader.classList.add('done');
      playIntro();   // pattern #4
    }, 200);
  });
};

// Pass `manager` to every loader
const gltfLoader = new GLTFLoader(manager);
const rgbeLoader = new RGBELoader(manager);
const texLoader = new THREE.TextureLoader(manager);
```

### How it works

`LoadingManager` aggregates progress across every loader you give it. `onProgress` fires per asset. `onLoad` fires when all assets attached to the manager have completed. Without this, you can't know when "everything is ready" — only when individual loads finish.

### Tweaks

- Animate the digit counter with GSAP for a smoother feel: `gsap.to({ n: 0 }, { n: pct, onUpdate: ... })`.

### Counting non-Three.js assets (fonts, audio)

`LoadingManager` only sees what's loaded through three's loaders. Fonts and audio need a parallel counter that gates the same `onLoad`:

```js
const extraAssets = { loaded: 0, total: 3 };  // e.g. 1 font + 2 audio files
let threeReady = false, extrasReady = false;

function maybeFinish() {
  if (threeReady && extrasReady) {
    preloader.classList.add('done');
    playIntro();
  }
}

manager.onLoad = () => { threeReady = true; maybeFinish(); };

function bumpExtra() {
  extraAssets.loaded++;
  // Update the same UI bar/counter weighted with three's progress if you want
  if (extraAssets.loaded === extraAssets.total) {
    extrasReady = true;
    maybeFinish();
  }
}

document.fonts.ready.then(bumpExtra);
howl1.once('load', bumpExtra);
howl2.once('load', bumpExtra);
```

For a unified percentage bar, weight three's `loaded/total` and the extras' `loaded/total` and average them.

### See also

- Pattern #4 for the intro animation that should follow.

---

## #33 — LUT color grading

**Use when:** Hollywood-grade "look" — film-emulation, teal-orange, faded retro, etc.
**Cost:** One additional post-processing pass.
**Dependencies:** `three/addons/loaders/LUTCubeLoader.js`, `three/addons/postprocessing/LUTPass.js`, a `.cube` LUT file.

### The code

```js
import { LUTCubeLoader } from 'three/addons/loaders/LUTCubeLoader.js';
import { LUTPass } from 'three/addons/postprocessing/LUTPass.js';

const lutPass = new LUTPass({ intensity: 1.0 });

new LUTCubeLoader().load('/luts/film-emulsion-32.cube', (result) => {
  lutPass.lut = result.texture3D;
});

// Add to your composer (postprocessing library) or three's EffectComposer
composer.addPass(lutPass);
```

### How it works

A LUT (lookup table) is a 3D texture that maps RGB input to RGB output. The fragment shader does `output = LUT.sample(input.r, input.g, input.b)` for every pixel. This is how Hollywood color grades — same data structure (`.cube` files) used by Resolve, Premiere, and FCPX.

### Where to get LUTs

- Free: [Cinelut Free Pack](https://www.rocketstock.com/free-after-effects-templates/35-free-luts-for-color-grading-videos/) and many other "free LUT pack" downloads. Always credit when required.
- Paid: $20–$50 packs from FilmConvert, Lutify.me — production-grade.
- DIY: export a 32x32x32 grid from Photoshop's Color Lookup adjustment.

### Tweaks

- `intensity 0.5` blends LUT effect with original — useful when LUT is too aggressive.
- Layer multiple LUTs by stacking passes (`composer.addPass(lutPass1); composer.addPass(lutPass2)`).

### See also

- `references/POST_PROCESSING.md` § "Final composite order" — LUT must come after bloom, before grain.

---

## Reading the patterns

When you don't know which pattern fits, scan the **Quick Index** above and read **Use when** lines until something matches the user's intent. Then copy the snippet, then read **Tweaks** for the parameter you'll most likely change first.
