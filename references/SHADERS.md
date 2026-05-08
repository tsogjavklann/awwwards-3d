# SHADERS — GLSL building blocks for Awwwards 3D

Reusable GLSL functions and patterns. Copy into your `ShaderMaterial.fragmentShader` (or `vertexShader`) bodies.

> **Boilerplate every raw ShaderMaterial fragment shader needs:**
> ```glsl
> precision mediump float;   // see ANTI_PATTERNS.md § 9 — non-negotiable for mobile
> // ...your varyings, uniforms, helper functions, main()...
> ```
> Three's built-in materials (and `onBeforeCompile` patches) inject `precision` automatically. Raw `ShaderMaterial` does NOT. Forgetting this on Android causes banding, strobing, or just black output.

This file is organized by what you're trying to achieve:
1. [Noise](#noise)
2. [Fresnel](#fresnel)
3. [Dispersion / chromatic offset](#dispersion)
4. [Time-driven UV](#time-driven-uv)
5. [Smooth gradients](#smooth-gradients)
6. [SDF primitives](#sdf-primitives)
7. [Mapping helpers](#mapping-helpers)
8. [Composition utilities](#composition-utilities)

---

## Noise

### `rand(p)` — pseudo-random hash

```glsl
float rand(vec2 p) {
  return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}
```

**Use when:** film grain, salt-pepper noise, jitter offsets. Cheap, ugly up close, fine for sub-pixel use.

### `valueNoise(p)` — smooth noise

```glsl
float valueNoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);   // smoothstep
  return mix(
    mix(rand(i + vec2(0.0, 0.0)), rand(i + vec2(1.0, 0.0)), u.x),
    mix(rand(i + vec2(0.0, 1.0)), rand(i + vec2(1.0, 1.0)), u.x),
    u.y
  );
}
```

**Use when:** flowing fog, organic surface variation, dust trails. Output range [0, 1].

### `simplex2D(p)` — gold-standard 2D simplex

```glsl
// From Ashima Arts (MIT)
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x * 34.0) + 1.0) * x); }

float simplex2D(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                     -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy));
  vec2 x0 = v -   i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod289(i);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                          + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy),
                          dot(x12.zw, x12.zw)), 0.0);
  m = m * m; m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g;
  g.x  = a0.x  * x0.x  + h.x  * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}
```

**Use when:** you need quality noise that doesn't tile. Output range ≈ [-1, 1]. ~3x more expensive than `valueNoise` but visibly better.

### Layered noise — fBm

```glsl
float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++) {
    v += a * simplex2D(p);
    p *= 2.0;
    a *= 0.5;
  }
  return v;
}
```

**Use when:** clouds, terrain heightmaps, organic surfaces. Mobile: drop loop count to 3.

---

## Fresnel

### Basic fresnel rim

```glsl
float fresnel(vec3 N, vec3 V, float power) {
  return pow(1.0 - max(dot(N, V), 0.0), power);
}

// In fragment shader:
vec3 N = normalize(vNormal);
vec3 V = normalize(vViewPosition);
float rim = fresnel(N, V, 2.5);
```

**Where `vNormal` and `vViewPosition` come from:**

- **Patching a built-in material via `onBeforeCompile`** (PATTERNS.md #7): three.js automatically provides both varyings. You just use them.
- **Raw `ShaderMaterial`:** you must declare and populate them yourself in the vertex shader:

```glsl
// vertex shader (raw ShaderMaterial)
varying vec3 vNormal;
varying vec3 vViewPosition;
void main() {
  vNormal = normalize(normalMatrix * normal);
  vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
  vViewPosition = -mvPos.xyz;
  gl_Position = projectionMatrix * mvPos;
}

// fragment shader
varying vec3 vNormal;
varying vec3 vViewPosition;
// ...your fresnel code...
```

Forgetting this is the #1 reason "my fresnel is black" — the varyings exist as zero vectors and `dot(0,0)` is 0, `pow(1, 2.5)` is 1, but multiplied by a base color of 0 gives nothing.

**Tweaks:**
- `power 1.0` → soft halo
- `power 2.5` → Awwwards default
- `power 5.0+` → razor edge

**Use when:** holographic UI, ghostly characters, sci-fi panels.

### Schlick approximation (more physically accurate)

```glsl
float fresnelSchlick(float cosTheta, float F0) {
  return F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);
}

// Usage
float cosT = max(dot(N, V), 0.0);
float reflectance = fresnelSchlick(cosT, 0.04);   // 0.04 is dielectric default
```

**Use when:** PBR custom materials. `F0 = 0.04` for plastic/glass, `F0 = 1.0` for metal.

---

## Dispersion

### RGB offset (cheap chromatic aberration)

```glsl
vec3 dispersion(sampler2D tex, vec2 uv, vec2 dir, float amount) {
  float r = texture2D(tex, uv + dir * amount * 1.0).r;
  float g = texture2D(tex, uv + dir * amount * 0.5).g;
  float b = texture2D(tex, uv).b;
  return vec3(r, g, b);
}

// Usage — direction from center, amount based on distance
vec2 dir = uv - 0.5;
vec3 color = dispersion(tDiffuse, uv, normalize(dir), length(dir) * 0.02);
```

**Tweaks:** `amount 0.005` is glass edge, `0.02` is dramatic, `0.05+` looks broken.

**Use when:** lens distortion overlay, glass material edge effect, dreamy hero effects.

### True per-IOR refraction (use inside `MeshTransmissionMaterial`)

That material has built-in `chromaticAberration`. Don't reinvent. See PATTERNS.md #5.

---

## Time-driven UV

### Scroll UV

```glsl
uniform float uTime;
varying vec2 vUv;

void main() {
  vec2 uv = vUv;
  uv.x += uTime * 0.1;   // scroll right at 0.1 units/sec
  vec3 color = texture2D(tDiffuse, fract(uv)).rgb;
  gl_FragColor = vec4(color, 1.0);
}
```

`fract(uv)` keeps UVs in [0, 1] for `RepeatWrapping` even when offsets grow huge.

**Use when:** flowing water, conveyor belts, energy beams.

### Pulse / wobble

```glsl
uv.x += sin(uTime * 2.0 + uv.y * 10.0) * 0.02;
```

Sine of `uv.y * frequency` gives different rows different phases — produces a flowing wave instead of a flat shift.

### Time-noise UV displacement

```glsl
vec2 offset = vec2(simplex2D(uv * 5.0 + uTime * 0.3));
vec3 color = texture2D(tDiffuse, uv + offset * 0.05).rgb;
```

**Use when:** glitch / digital effect, water reflection wobble.

---

## Smooth gradients

### Two-color gradient (no banding)

```glsl
varying vec2 vUv;
void main() {
  vec3 a = vec3(0.05, 0.05, 0.10);
  vec3 b = vec3(0.40, 0.10, 0.60);
  vec3 col = mix(a, b, smoothstep(0.0, 1.0, vUv.y));

  // Anti-banding: add tiny noise
  col += (rand(vUv) - 0.5) * 0.02;

  gl_FragColor = vec4(col, 1.0);
}
```

The `+ noise * 0.02` line is the banding-killer. Without it, 8-bit displays show distinct color "stripes" across smooth gradients. With it, the eye perceives continuous color.

### Three-stop gradient

```glsl
vec3 a = vec3(0.05, 0.05, 0.10);
vec3 b = vec3(0.20, 0.05, 0.30);
vec3 c = vec3(0.40, 0.10, 0.60);
vec3 col = (vUv.y < 0.5)
  ? mix(a, b, smoothstep(0.0, 0.5, vUv.y))
  : mix(b, c, smoothstep(0.5, 1.0, vUv.y));
```

**Use when:** hero backgrounds, atmospheric depth.

### Radial gradient

```glsl
float r = length(vUv - 0.5);
vec3 col = mix(vec3(0.9, 0.7, 0.5), vec3(0.1, 0.05, 0.2), smoothstep(0.0, 0.7, r));
```

**Use when:** "spotlight" reveals, sunrise/sunset moods.

---

## SDF primitives

Distance functions in screen UVs. Useful for mask shapes and stylized renders.

```glsl
float sdCircle(vec2 p, float r) { return length(p) - r; }

float sdBox(vec2 p, vec2 b) {
  vec2 d = abs(p) - b;
  return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}

float sdRoundedBox(vec2 p, vec2 b, float r) {
  return sdBox(p, b - r) - r;
}

// Usage — soft anti-aliased circle
vec2 p = (vUv - 0.5) * 2.0;
float d = sdCircle(p, 0.6);
float mask = smoothstep(0.01, -0.01, d);
gl_FragColor = vec4(vec3(mask), 1.0);
```

**Use when:** custom UI shapes, image masks, brand mark reveals.

---

## Mapping helpers

### Normal-map sampling (custom shaders)

```glsl
vec3 normal = texture2D(uNormalMap, vUv).rgb * 2.0 - 1.0;
// Transform from tangent space — usually three handles this for you,
// but for raw ShaderMaterial you'll need vTangent / vBitangent attributes.
```

For most use cases, prefer `MeshStandardMaterial` + onBeforeCompile to inject custom logic, instead of writing a full PBR shader from scratch.

### UV remapping (atlas)

```glsl
// Sample one tile of a 4x4 atlas
vec2 atlas(vec2 uv, int idx, vec2 dim) {
  vec2 cell = vec2(mod(float(idx), dim.x), floor(float(idx) / dim.x));
  return (cell + uv) / dim;
}

// Usage — frame 5 of a 4x4 sprite atlas
vec2 atlasUv = atlas(vUv, 5, vec2(4.0));
vec3 color = texture2D(tAtlas, atlasUv).rgb;
```

**Use when:** sprite-based animations, particle variety from one texture.

### Triplanar mapping (no UV needed)

```glsl
vec3 triplanar(sampler2D tex, vec3 worldPos, vec3 worldNormal, float scale) {
  vec3 blend = abs(worldNormal);
  blend = pow(blend, vec3(4.0));
  blend /= dot(blend, vec3(1.0));
  vec3 x = texture2D(tex, worldPos.yz * scale).rgb;
  vec3 y = texture2D(tex, worldPos.xz * scale).rgb;
  vec3 z = texture2D(tex, worldPos.xy * scale).rgb;
  return x * blend.x + y * blend.y + z * blend.z;
}
```

**Use when:** procedural models without UV maps (e.g. marching cubes terrain, displaced primitives).

---

## Composition utilities

### `screen` blend

```glsl
vec3 screen(vec3 a, vec3 b) {
  return 1.0 - (1.0 - a) * (1.0 - b);
}
```

Brighter than additive, doesn't clip. Use for soft glow overlays.

### `overlay` blend

```glsl
vec3 overlay(vec3 base, vec3 blend) {
  return mix(2.0 * base * blend, 1.0 - 2.0 * (1.0 - base) * (1.0 - blend),
             step(0.5, base));
}
```

The Photoshop "Overlay" mode. Use for film grain, color grades, atmosphere passes.

### Luma extraction

```glsl
// BT.601 (legacy SDTV) — fine for general "perceived brightness"
float lumaBT601(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

// BT.709 (modern HDTV / sRGB) — more accurate for current displays
float lumaBT709(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
```

**Which to use:**
- BT.709 for any modern web work (matches sRGB color space we're already in)
- BT.601 only if you're matching legacy/print pipelines

**Use when:** isolating bright regions for a custom bloom, threshold-based effects, desaturation passes.

---

## Patching three's built-in materials with `onBeforeCompile`

When you want a Standard material with one custom tweak, don't write a full ShaderMaterial. Patch instead:

```js
mat.onBeforeCompile = (shader) => {
  shader.uniforms.uTime = { value: 0 };

  // Inject after the default include slot
  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <output_fragment>',
    `
    // your code here, e.g. fresnel rim:
    vec3 viewDir = normalize(vViewPosition);
    float rim = pow(1.0 - max(dot(normalize(vNormal), viewDir), 0.0), 2.5);
    gl_FragColor.rgb += vec3(0.4, 0.7, 1.0) * rim;
    #include <output_fragment>
    `,
  );
  mat.userData.shader = shader;   // keep ref so you can update uniforms later
};

// In tick():
if (mat.userData.shader) mat.userData.shader.uniforms.uTime.value = clock.elapsedTime;
```

Hooks (replace targets) you'll commonly use:
- `#include <begin_vertex>` — modify position before all transforms
- `#include <project_vertex>` — modify after model-view, before projection
- `#include <output_fragment>` — modify final color (most common)
- `#include <map_fragment>` — modify the diffuse texture sample

See `references/PATTERNS.md` § #7 (fresnel rim) for a worked example.

---

## Performance budget per pixel

Rough fragment-shader cost on mid-tier GPUs at 1080p:

| Op | Cost |
|---|---|
| `texture2D` | 1 unit (4 for HDR/Half-float) |
| `simplex2D` | 8 units |
| `valueNoise` | 3 units |
| `fbm` (5 octaves) | 40 units |
| Loop with 8 `simplex2D` | 64 units |
| Branching (`if`) | 0–3 units depending on coherence |

**Heuristic:** if your fragment shader has more than ~60 ops, mobile will struggle. Cut octaves first, simplify branches second, drop precision third.

---

## When NOT to write a shader

- "I need to color this mesh red" → use `material.color.set(0xff0000)`.
- "I need to fade this in" → animate `material.opacity`.
- "I need to texture this" → use `material.map` with `TextureLoader`.
- "I need PBR" → `MeshStandardMaterial` or `MeshPhysicalMaterial`. Don't reinvent BRDFs.
- "I need a simple post effect" → `ShaderPass` with a small fragment, see POST_PROCESSING.md.

Write a shader when:
- The effect is **time-driven** at sub-frame granularity (waves, dispersion, noise drift)
- You need **per-vertex** displacement (morphing, wind sway)
- You're combining **multiple textures or values per pixel** (triplanar, custom blends)
- Built-in materials can't express it (holographic shaders, custom toon ramps)

---

## See also

- `references/PATTERNS.md` § #7 (Fresnel rim), #8 (UV scroll), #14 (Particle shader), #17 (Mesh morph), #30 (Background gradient mesh)
- `references/POST_PROCESSING.md` for post-pipeline ShaderPass examples
- `references/ANTI_PATTERNS.md` § 9 — don't forget `precision mediump float;`
