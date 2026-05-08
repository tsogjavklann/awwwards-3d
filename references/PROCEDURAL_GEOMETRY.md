# PROCEDURAL_GEOMETRY — code-only geometry generation

This skill's templates use AI-generated GLBs (via Blender MCP) as one path. **The other path is pure code** — primitives, math, vertex shaders, and Blender Python procedural. For 80–90% of Awwwards aesthetics, hand-coded geometry is **enough, faster, and more controllable** than reaching for AI.

This file documents the procedural toolkit. Cross-reference with `PATTERNS.md` (which has runtime usage) and `BLENDER_PIPELINE.md` (which has the Blender MCP recipes).

---

## When code beats AI

**Reach for code first when:**
- The shape is geometric, abstract, or symmetric (sphere, cylinder, knot, helix)
- You need parametric control (slider for # segments, displacement strength)
- You need exact dimensions (corporate identity, brand alignment)
- You need shapes to morph or deform at runtime
- Determinism matters (same seed → same shape)
- Mobile budget is tight (a `SphereGeometry(1, 32, 32)` is 6× lighter than a 64-poly AI sphere)

**Reach for AI (Hyper3D / Hunyuan) only when:**
- You need a real-world specific object (a particular brand bottle, a specific car model)
- You need detailed organic forms (faces, animals, sculptures)
- You're prototyping concepts at speed and don't care about file weight

This skill defaults to **procedural-first**. Templates `minimal.html`, `coin-scroll.html`, `room-walkthrough.html` all use procedurally-built geometry; only `glass-product.html` loads a GLB (and even that GLB is just a procedurally-generated sphere).

---

## 1. Three.js primitives — complete reference (r170)

The full list, with Awwwards-relevant tweaks. Every one is one constructor call.

### Box

```js
new THREE.BoxGeometry(width, height, depth, widthSegments, heightSegments, depthSegments)
// Defaults: 1, 1, 1, 1, 1, 1
```

**Awwwards use:** Architectural elements (walls, blocks, sofa). Subdivisions for displacement.

### Sphere

```js
new THREE.SphereGeometry(radius, widthSegments, heightSegments,
  phiStart, phiLength, thetaStart, thetaLength)
// Defaults: 1, 32, 16, 0, Math.PI*2, 0, Math.PI
```

**Sweet spots:** `(1, 32, 32)` for hero; `(1, 64, 64)` for glass refraction; `(1, 16, 12)` for mobile particle replacements.

**Trick — half-sphere:** pass `thetaLength: Math.PI / 2` for a dome.

### Cylinder

```js
new THREE.CylinderGeometry(radiusTop, radiusBottom, height, radialSegments,
  heightSegments, openEnded, thetaStart, thetaLength)
// Defaults: 1, 1, 1, 32, 1, false, 0, Math.PI*2
```

**Tricks:**
- `radiusTop: 0` → cone
- `radiusTop: 0.3, radiusBottom: 1` → tapered tower / vase
- `openEnded: true` → tube (use both faces invisible from inside)

### Cone

```js
new THREE.ConeGeometry(radius, height, radialSegments, heightSegments)
```

Just a cylinder with `radiusTop: 0`. Use the cylinder constructor if you'll animate the taper.

### Torus / TorusKnot

```js
new THREE.TorusGeometry(radius, tube, radialSegments, tubularSegments, arc)
// Defaults: 1, 0.4, 12, 48, Math.PI*2

new THREE.TorusKnotGeometry(radius, tube, tubularSegments, radialSegments, p, q)
// Defaults: 1, 0.4, 64, 8, 2, 3
```

**Awwwards use:** Abstract jewelry-like hero shapes. The `(p, q)` integers make different knots:
- `(2, 3)` — classic trefoil
- `(3, 4)` — pretzel
- `(2, 5)` — five-pointed star knot

### Icosahedron / Dodecahedron / Octahedron / Tetrahedron

```js
new THREE.IcosahedronGeometry(radius, detail)
// detail=0 (raw 20 faces), detail=1 (subdivided), detail=4 (642 verts — match for morph!)
```

**Awwwards use:** Faceted geometric heroes. `detail: 0` looks gem-like; `detail: 4+` looks organic after smooth shading.

### Plane

```js
new THREE.PlaneGeometry(width, height, widthSegments, heightSegments)
```

**Use:** Floor, wall, full-screen quad, particle base, vertex displacement target.

For wave/water: `(20, 20, 64, 64)` — 64 subdivisions per axis lets vertex shader displace nicely.

### Ring

```js
new THREE.RingGeometry(innerRadius, outerRadius, thetaSegments, phiSegments,
  thetaStart, thetaLength)
```

**Use:** Halos, planet rings, UI rings.

### Capsule / Tube

```js
new THREE.CapsuleGeometry(radius, length, capSegments, radialSegments)
new THREE.TubeGeometry(curve, tubularSegments, radius, radialSegments, closed)
```

**TubeGeometry is one of the most powerful primitives** — see § 3 (Curve-based geometry).

### Lathe — revolution shape

```js
const profile = [
  new THREE.Vector2(0, -1),
  new THREE.Vector2(0.5, -0.8),
  new THREE.Vector2(0.7, 0),
  new THREE.Vector2(0.4, 0.8),
  new THREE.Vector2(0, 1),
];
new THREE.LatheGeometry(profile, segments=32, phiStart=0, phiLength=Math.PI*2)
```

**Use:** Vases, bottles, lamp shades, anything rotationally symmetric.

### Extrude — 2D shape into 3D

```js
const shape = new THREE.Shape();
shape.moveTo(0, 0);
shape.lineTo(1, 0);
shape.bezierCurveTo(1.5, 0.5, 1.5, 1, 1, 1);
shape.lineTo(0, 1);
shape.lineTo(0, 0);

new THREE.ExtrudeGeometry(shape, {
  depth: 0.3,
  bevelEnabled: true,
  bevelThickness: 0.02,
  bevelSize: 0.02,
  bevelSegments: 4,
  curveSegments: 16,
});
```

**Use:** 3D logos, type, custom architectural shapes from a 2D outline.

### Edges / Wireframe helpers

```js
const edges = new THREE.EdgesGeometry(box, thresholdAngle=15);
const lines = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({color: 0xffffff}));
```

**Awwwards use:** Wireframe overlays (Active Theory aesthetic).

---

## 2. ExtrudeGeometry — 2D logo to 3D hero

Awwwards 3D-typography pattern in 30 lines:

```js
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { FontLoader } from 'three/addons/loaders/FontLoader.js';

const font = await new FontLoader().loadAsync(
  'https://unpkg.com/three@0.170.0/examples/fonts/helvetiker_bold.typeface.json'
);

const geom = new TextGeometry('AWWWARDS', {
  font,
  size: 1,
  depth: 0.25,
  curveSegments: 8,
  bevelEnabled: true,
  bevelThickness: 0.02,
  bevelSize: 0.015,
  bevelOffset: 0,
  bevelSegments: 4,
});
geom.computeBoundingBox();
geom.center();   // critical — TextGeometry origin is bottom-left, center it

const mesh = new THREE.Mesh(geom, new THREE.MeshStandardMaterial({
  color: 0xffffff, metalness: 1, roughness: 0.15,
}));
```

**Tweaks:**
- For thin neon lettering: `depth: 0.05, bevelEnabled: false`
- For thick blocky type: `depth: 0.6, bevelSize: 0.05`
- Use a custom font: pre-convert `.ttf` → `.json` via [facetype.js](https://gero3.github.io/facetype.js/)

---

## 3. Curve-based geometry — `TubeGeometry`

The most flexible primitive in three.js. Pass any curve, get an extrusion.

### Helix (gold ribbon)

```js
const helixPoints = [];
for (let i = 0; i < 200; i++) {
  const t = i / 200;
  helixPoints.push(new THREE.Vector3(
    Math.cos(t * Math.PI * 8) * 0.6,
    t * 4 - 2,
    Math.sin(t * Math.PI * 8) * 0.6,
  ));
}
const helixCurve = new THREE.CatmullRomCurve3(helixPoints);
const helixGeom = new THREE.TubeGeometry(helixCurve, 400, 0.04, 12, false);
```

### Knot from explicit math

```js
class CustomKnotCurve extends THREE.Curve {
  getPoint(t, target = new THREE.Vector3()) {
    const a = t * Math.PI * 2;
    return target.set(
      (2 + Math.cos(a * 3)) * Math.cos(a * 2),
      (2 + Math.cos(a * 3)) * Math.sin(a * 2),
      Math.sin(a * 3),
    );
  }
}
const knot = new THREE.TubeGeometry(new CustomKnotCurve(), 400, 0.15, 12, true);
```

### Lissajous curve (3D figure-eight family)

```js
class Lissajous extends THREE.Curve {
  constructor(a = 3, b = 4, c = 5) { super(); this.a = a; this.b = b; this.c = c; }
  getPoint(t, target = new THREE.Vector3()) {
    const u = t * Math.PI * 2;
    return target.set(
      Math.sin(this.a * u),
      Math.sin(this.b * u + Math.PI / 2),
      Math.sin(this.c * u),
    );
  }
}
const lissajous = new THREE.TubeGeometry(new Lissajous(), 800, 0.05, 12, true);
```

**Awwwards use:** Hero objects that feel like "math made visible". Particularly good with iridescent or transmissive materials.

---

## 4. Vertex shader displacement — animate the surface

A primitive becomes alive when you push its vertices in the vertex shader. Cheap, GPU-driven, no CPU cost.

### Wobbling sphere

```js
const baseGeom = new THREE.IcosahedronGeometry(1, 5);   // ~10k verts for smoothness
const mat = new THREE.ShaderMaterial({
  uniforms: {
    uTime: { value: 0 },
    uAmount: { value: 0.15 },
  },
  vertexShader: `
    uniform float uTime;
    uniform float uAmount;
    varying vec3 vNormal;
    void main() {
      vNormal = normalize(normalMatrix * normal);
      vec3 pos = position;
      float n = sin(pos.x * 4.0 + uTime) * cos(pos.y * 4.0 + uTime * 0.7);
      pos += normal * n * uAmount;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    varying vec3 vNormal;
    void main() {
      float lighting = dot(vNormal, vec3(0.5, 0.7, 0.5));
      gl_FragColor = vec4(vec3(0.6, 0.7, 1.0) * (lighting * 0.5 + 0.5), 1.0);
    }
  `,
});
const wobble = new THREE.Mesh(baseGeom, mat);

// In tick():
mat.uniforms.uTime.value = clock.elapsedTime;
```

### Flag / wave plane

```glsl
// vertex shader
uniform float uTime;
varying vec2 vUv;
void main() {
  vUv = uv;
  vec3 pos = position;
  pos.z = sin(pos.x * 3.0 + uTime) * 0.3 + cos(pos.y * 4.0 + uTime * 0.7) * 0.2;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}
```

Apply to a `PlaneGeometry(2, 2, 64, 64)` — high subdivision matters or it ridges.

### Spike on hover

Combine with raycaster (PATTERNS.md #20). Pass mouse worldPos as uniform; vertices near mouse spike outward:

```glsl
uniform vec3 uMouse;
uniform float uMouseStrength;
void main() {
  vec3 pos = position;
  vec3 worldPos = (modelMatrix * vec4(position, 1.0)).xyz;
  float d = distance(worldPos, uMouse);
  float spike = exp(-d * 4.0) * uMouseStrength;
  pos += normal * spike;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}
```

---

## 5. Math-driven shapes (no Blender, no AI)

### Parametric surface

Three's `ParametricGeometry` was deprecated in r170 — use this drop-in replacement:

```js
function parametricGeometry(fn, segmentsX, segmentsY) {
  const positions = [];
  const indices = [];
  for (let j = 0; j <= segmentsY; j++) {
    for (let i = 0; i <= segmentsX; i++) {
      const u = i / segmentsX;
      const v = j / segmentsY;
      const p = fn(u, v);
      positions.push(p.x, p.y, p.z);
    }
  }
  for (let j = 0; j < segmentsY; j++) {
    for (let i = 0; i < segmentsX; i++) {
      const a = j * (segmentsX + 1) + i;
      const b = a + 1;
      const c = a + segmentsX + 1;
      const d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  g.setIndex(indices);
  g.computeVertexNormals();
  return g;
}

// Klein bottle (the classic non-orientable surface)
const klein = parametricGeometry((u, v) => {
  u *= Math.PI;
  v *= Math.PI * 2;
  let x, y, z;
  if (u < Math.PI) {
    x = 3 * Math.cos(u) * (1 + Math.sin(u)) +
        (2 * (1 - Math.cos(u) / 2)) * Math.cos(u) * Math.cos(v);
    z = -8 * Math.sin(u) - 2 * (1 - Math.cos(u) / 2) * Math.sin(u) * Math.cos(v);
  } else {
    x = 3 * Math.cos(u) * (1 + Math.sin(u)) +
        (2 * (1 - Math.cos(u) / 2)) * Math.cos(v + Math.PI);
    z = -8 * Math.sin(u);
  }
  y = -2 * (1 - Math.cos(u) / 2) * Math.sin(v);
  return new THREE.Vector3(x * 0.1, y * 0.1, z * 0.1);
}, 64, 32);
```

### Mobius strip

```js
const mobius = parametricGeometry((u, v) => {
  u *= Math.PI * 2;
  v = (v - 0.5) * 0.4;
  const x = (1 + v * Math.cos(u / 2)) * Math.cos(u);
  const y = (1 + v * Math.cos(u / 2)) * Math.sin(u);
  const z = v * Math.sin(u / 2);
  return new THREE.Vector3(x, y, z);
}, 128, 8);
```

---

## 6. InstancedMesh — thousands of shapes, one draw call

For particle fields, debris, crowds, asteroid belts. PATTERNS.md #13 covers basics; here's an Awwwards-style use case:

### Galaxy disk

```js
const COUNT = 8000;
const geom = new THREE.IcosahedronGeometry(0.04, 0);
const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x4080ff });
const mesh = new THREE.InstancedMesh(geom, mat, COUNT);

const dummy = new THREE.Object3D();
for (let i = 0; i < COUNT; i++) {
  // Galaxy distribution: spiral arms in xz, thin in y
  const t = i / COUNT;
  const arm = (t * 4) % 1;             // 4 arms
  const angle = arm * Math.PI * 2 + t * Math.PI * 6;
  const r = Math.pow(t, 0.5) * 6;      // density falls off with sqrt
  dummy.position.set(
    Math.cos(angle) * r + (Math.random() - 0.5) * 0.4,
    (Math.random() - 0.5) * 0.3,
    Math.sin(angle) * r + (Math.random() - 0.5) * 0.4,
  );
  dummy.scale.setScalar(0.5 + Math.random() * 1.5);
  dummy.updateMatrix();
  mesh.setMatrixAt(i, dummy.matrix);
}
mesh.instanceMatrix.needsUpdate = true;
```

### Voronoi-like point cluster

```js
// Place N points; each point is the center of a small instanced sphere
// Use poisson-disc sampling or simple jittered grid
const positions = poissonDisc2D(20, 20, 0.5);   // see hash below
positions.forEach((p, i) => {
  dummy.position.set(p.x, 0, p.y);
  dummy.scale.setScalar(0.3 + Math.random() * 0.4);
  dummy.updateMatrix();
  mesh.setMatrixAt(i, dummy.matrix);
});

// Quick jittered grid (good enough for hero scenes)
function poissonDisc2D(w, h, r) {
  const out = [];
  for (let y = -h/2; y < h/2; y += r) {
    for (let x = -w/2; x < w/2; x += r) {
      out.push({ x: x + (Math.random() - 0.5) * r * 0.5,
                 y: y + (Math.random() - 0.5) * r * 0.5 });
    }
  }
  return out;
}
```

---

## 7. Blender Python — beyond Recipe 1-4

`BLENDER_PIPELINE.md` documents 4 base recipes. Here are advanced procedural patterns that go further.

### Geometry Nodes (Blender 3.4+)

For non-destructive procedural meshes — useful when you want one node graph that responds to parameters.

```python
import bpy

# Create a mesh that will host the geometry-nodes modifier
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.active_object
obj.name = 'gn_host'

# Add a Geometry Nodes modifier with a fresh node group
mod = obj.modifiers.new('GN', 'NODES')
node_group = bpy.data.node_groups.new('Procedural', 'GeometryNodeTree')
mod.node_group = node_group

# Build a tiny graph: input geometry → subdivide → output
nodes = node_group.nodes
links = node_group.links

input_node = nodes.new('NodeGroupInput')
output_node = nodes.new('NodeGroupOutput')
subdivide = nodes.new('GeometryNodeSubdivisionSurface')
subdivide.inputs['Level'].default_value = 3

node_group.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
node_group.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

links.new(input_node.outputs['Geometry'], subdivide.inputs['Mesh'])
links.new(subdivide.outputs['Mesh'], output_node.inputs['Geometry'])
```

This is the "professional" path for procedural Blender — verbose to set up via Python but unparalleled for runtime parameter sweeps.

### Boolean operations (CSG via modifiers)

```python
# Subtract a sphere from a cube → "bitten" cube
bpy.ops.mesh.primitive_cube_add(size=2)
cube = bpy.context.active_object

bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(1, 1, 1))
sphere = bpy.context.active_object

bpy.context.view_layer.objects.active = cube
mod = cube.modifiers.new('Bool', 'BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = sphere
bpy.ops.object.modifier_apply(modifier='Bool')

# Hide the cutter
sphere.hide_set(True)
```

**Awwwards use:** Hero objects with "carved" details. Combine with bevel for softness.

### Array + Curve

```python
# Spiral staircase: a step + Array along a curve
import bpy

# Make the step
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
step = bpy.context.active_object
step.scale = (1.5, 0.4, 0.1)
bpy.ops.object.transform_apply(scale=True)

# Make a helical curve
import math
curve_data = bpy.data.curves.new('helix', type='CURVE')
curve_data.dimensions = '3D'
spline = curve_data.splines.new('NURBS')
spline.points.add(99)
for i, p in enumerate(spline.points):
    t = i / 99
    p.co = (math.cos(t * math.pi * 8) * 3, math.sin(t * math.pi * 8) * 3, t * 6, 1)
spline.use_endpoint_u = True
curve_obj = bpy.data.objects.new('helix', curve_data)
bpy.context.collection.objects.link(curve_obj)

# Array modifier on step → follow curve
arr = step.modifiers.new('Arr', 'ARRAY')
arr.fit_type = 'FIT_LENGTH'
arr.fit_length = curve_data.splines[0].calc_length()
arr.use_relative_offset = False
arr.use_constant_offset = True
arr.constant_offset_displace[0] = 0.6   # step-to-step distance

cur = step.modifiers.new('Cur', 'CURVE')
cur.object = curve_obj
```

### Marching cubes from implicit field

For organic shapes from math equations (not in stock Blender, but possible via add-on or scripted vertices):

```python
# Pseudocode — full marching cubes is ~150 lines, see scikit-image marching_cubes
import numpy as np
from skimage import measure

# Build a 3D field
N = 64
x = np.linspace(-2, 2, N); y = np.linspace(-2, 2, N); z = np.linspace(-2, 2, N)
X, Y, Z = np.meshgrid(x, y, z, indexing='ij')

# Field: union of two metaballs
field = 1 / (X*X + Y*Y + Z*Z + 0.1) + 1 / ((X-1)**2 + Y*Y + Z*Z + 0.1)

# Extract surface at iso=2
verts, faces, normals, _ = measure.marching_cubes(field, level=2.0)

# Build Blender mesh from verts/faces
mesh = bpy.data.meshes.new('metaball')
mesh.from_pydata(verts.tolist(), [], faces.tolist())
mesh.update()
obj = bpy.data.objects.new('metaball', mesh)
bpy.context.collection.objects.link(obj)
```

Heavy, but produces shapes you can't get any other way.

---

## 8. Hybrid: code + AI

When code gets you 90% there but you need that last 10% of organic detail, the hybrid approach beats either alone:

1. Code a **base geometry** (sphere, IcoSphere, custom procedural)
2. Pass it through Blender's **Sculpt Mode displacement** with a procedurally-generated brush stamp
3. Apply a **Subdivision Surface + Smooth Modifier** stack
4. Optionally pipe through **Hunyuan/Hyper3D** if you need texture variation

The **Recipe 3 (Blob)** in `BLENDER_PIPELINE.md` is exactly this pattern — code generates shape, displace adds organic noise, smooth cleans it up. **No AI needed.**

---

## 9. Decision tree — code vs AI

```
Is the shape symmetric / mathematically describable?
├── YES → write code (this file). Done.
└── NO → Is it a real-world specific object?
    ├── YES (a particular brand bottle, a known person) → AI 3D or photogrammetry
    └── NO → Can you sketch it from primitives + boolean + bevel?
        ├── YES → write Blender Python (BLENDER_PIPELINE.md)
        └── NO → Is it a "vibe" object (creature, blob, organic)?
            ├── YES → start procedural (this file § 5/7), add AI only if time-pressed
            └── NO → AI 3D as a starting point, then refine in Blender
```

**Heuristic:** if you can describe the shape in 1-2 sentences using geometric vocabulary ("a torus knot with thick ribbon", "a spiral helix of cubes"), code wins every time.

---

## 10. Cheat sheet — Awwwards hero objects, all from code

These are 80% of the hero objects on Awwwards Site of the Day. Each is one constructor + material:

| Look | Code |
|---|---|
| **Chrome ball** | `IcosahedronGeometry(1, 4)` + `MeshStandardMaterial({metalness:1, roughness:0.05})` |
| **Glass orb** | `SphereGeometry(1, 64, 64)` + `MeshPhysicalMaterial({transmission:1, dispersion:1.2})` |
| **Spinning coin** | `CylinderGeometry(1, 1, 0.1, 96)` + `MeshStandardMaterial({color:0xffd271, metalness:1})` |
| **Knot of light** | `TorusKnotGeometry(0.7, 0.18, 200, 16)` + emissive material + bloom |
| **Tube ribbon** | `TubeGeometry(catmullRom, 400, 0.04, 12)` + iridescent material |
| **Wobbling blob** | `IcosahedronGeometry(1, 5)` + ShaderMaterial with vertex displacement |
| **Halo / portal** | `RingGeometry(0.7, 1.0, 64)` + emissive + bloom |
| **3D type** | `TextGeometry({font, depth: 0.25, bevelEnabled: true})` + chrome material |
| **Faceted gem** | `IcosahedronGeometry(1, 0)` (raw 20 faces) + `MeshStandardMaterial({flatShading:true})` |
| **Particle galaxy** | `InstancedMesh(IcosahedronGeometry(0.04,0), mat, 8000)` + spiral arm placement |

Pair any of these with the canonical post chain (`POST_PROCESSING.md`) and you have a publishable hero scene. **No AI, no marketplace, no licensing.**

---

## See also

- `references/PATTERNS.md` § #13 (Instanced mesh), #14 (Particle shader), #17 (Mesh morph) — runtime patterns
- `references/SHADERS.md` — vertex/fragment shader building blocks
- `references/BLENDER_PIPELINE.md` — Blender MCP recipes when you want to go beyond pure-code
- `assets/templates/minimal.html` — every primitive type referenced here is used somewhere in the verified templates
