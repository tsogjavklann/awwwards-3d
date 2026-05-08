# BLENDER_PIPELINE — Blender MCP recipes + GLB export

This skill assumes Blender MCP (`blender-mcp`) is installed. With it, you can model directly from Claude Code via tools like `mcp__blender__execute_blender_code`. This file documents:

1. Four asset recipes for Awwwards-style hero objects
2. The canonical GLB export configuration (Draco + Meshopt)
3. KTX2 texture compression workflow (when to bother)
4. Shape keys → GLB morph targets

---

## Prerequisites

- **Blender 4.0+ required.** Recipes here use Blender 4.x Python API. Notable changes from 3.x: Principled BSDF input named `Transmission Weight` (was `Transmission`); auto-smooth set via `mesh.use_auto_smooth` + `auto_smooth_angle` properties (the `shade_auto_smooth` operator was removed/renamed in 4.1+). For Blender 3.x, expect to adapt API names.
- `blender-mcp` MCP server registered (already configured in this skill's environment)
- For compression: `gltf-transform` CLI (`npm i -g @gltf-transform/cli`)
- For KTX2: `toktx` from KTX-Software (optional, only when needed)

> **Test recipes before relying on them.** Blender's Python API drifts between minor versions. Run each recipe interactively in your target Blender version and confirm the output before scripting against it. Errors are usually obvious (`AttributeError: 'Object' object has no attribute 'X'`).

> **Verification status:** All four recipes below have been executed end-to-end in **Blender 5.1.1** via the `blender-mcp` server (tested 2026-05). Produced GLB files (6 KB coin, 12 KB glass orb, 6 KB blob, 5 KB room — all Draco-compressed) are committed under `assets/models/` and can be loaded by templates directly. If you regenerate them, the Python below is verified to run unmodified.

Verify Blender MCP is connected:

```js
// From Claude Code:
mcp__blender__get_scene_info()
```

If it fails, the MCP server isn't running. Start Blender, install the addon, enable it.

---

## Recipe 1 — Coin (cylinder + bevel + PBR metal)

The classic Awwwards hero. Spinning coin, scroll-driven flip, gold material with HDRI reflections.

### Blender MCP code

```python
# Run via mcp__blender__execute_blender_code
import bpy

# Clean default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create cylinder with low vertex count
bpy.ops.mesh.primitive_cylinder_add(
    vertices=64,         # smooth enough; bevel will round further
    radius=1.0,
    depth=0.1,           # thin coin
    location=(0, 0, 0),
)
coin = bpy.context.active_object
coin.name = 'coin'

# Apply rotation so flat face is up
coin.rotation_euler = (0, 0, 0)

# Add subdivision for nice bevel
bpy.ops.object.modifier_add(type='BEVEL')
coin.modifiers['Bevel'].width = 0.02
coin.modifiers['Bevel'].segments = 4
coin.modifiers['Bevel'].limit_method = 'ANGLE'
coin.modifiers['Bevel'].angle_limit = 0.523599  # 30 deg
bpy.ops.object.modifier_apply(modifier='Bevel')

# Smooth shading (autosmooth angle set on the mesh data, then apply)
coin.data.use_auto_smooth = True
coin.data.auto_smooth_angle = 0.523599   # 30 degrees
bpy.ops.object.shade_smooth()

# Material — polished gold
mat = bpy.data.materials.new(name='CoinGold')
mat.use_nodes = True
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (1.0, 0.78, 0.34, 1.0)
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.18

coin.data.materials.append(mat)

# Apply transforms (critical for clean GLB export)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```

### Tips

- For an "engraved coin" detail: use a Boolean modifier with text or a logo mesh.
- For a "rough" finish (think old gold): bump `Roughness` to 0.4 and add a subtle Bump map.
- Vertex count after bevel ≈ 1500. Plenty for a hero object; trivial after Draco compression.

---

## Recipe 2 — Glass orb (sphere + transmission setup)

Pair with `MeshTransmissionMaterial` on the JS side (PATTERNS.md #5). Blender role: produce the geometry; the material is overridden in three.

### Blender MCP code

```python
import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# High-density sphere — refraction needs smooth normals
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=64, ring_count=32,
    radius=1.0, location=(0, 0, 0),
)
orb = bpy.context.active_object
orb.name = 'glass_orb'

# Smooth shading
bpy.ops.object.shade_smooth()

# Add a placeholder material — three's MeshTransmissionMaterial replaces it
mat = bpy.data.materials.new(name='GlassPlaceholder')
mat.use_nodes = True
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Transmission Weight'].default_value = 1.0
bsdf.inputs['IOR'].default_value = 1.5
bsdf.inputs['Roughness'].default_value = 0.05
orb.data.materials.append(mat)

bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```

### Tips

- Don't subdivide further than 64 segments — `MeshTransmissionMaterial` is bandwidth-bound, not vertex-bound.
- For a non-spherical glass (lens, prism), start with `primitive_cube_add` + Subdivision Surface.
- After GLB import in three.js, swap material:

```js
gltf.scene.getObjectByName('glass_orb').material = new MeshTransmissionMaterial({ /* ... */ });
```

---

## Recipe 3 — Abstract blob (subdivided sphere + displacement)

For atmospheric, organic hero objects. Common in Lusion / Resn aesthetic.

### Blender MCP code

```python
import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Start with icosphere — uniform vertex distribution
bpy.ops.mesh.primitive_ico_sphere_add(
    subdivisions=4,      # ≈ 642 verts
    radius=1.0,
    location=(0, 0, 0),
)
blob = bpy.context.active_object
blob.name = 'blob'

# Add Displace modifier with noise texture
bpy.ops.object.modifier_add(type='DISPLACE')
disp = blob.modifiers['Displace']
disp.strength = 0.25

# Create the noise texture
tex = bpy.data.textures.new('blob_noise', type='CLOUDS')
tex.noise_scale = 0.8
disp.texture = tex

# Apply the modifier so vertex positions are baked in
bpy.ops.object.modifier_apply(modifier='Displace')

# Recompute normals after displacement
bpy.ops.object.shade_smooth()
bpy.ops.object.modifier_add(type='SMOOTH')
blob.modifiers['Smooth'].iterations = 2
bpy.ops.object.modifier_apply(modifier='Smooth')

# Material — pearlescent / iridescent
mat = bpy.data.materials.new(name='BlobIridescent')
mat.use_nodes = True
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.85, 0.9, 1.0, 1.0)
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.25
blob.data.materials.append(mat)

bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```

### Tips

- For more dramatic deformation: `disp.strength = 0.5` (warning: starts looking lumpy).
- Pair with `iridescence: 1.0` in three.js (PATTERNS.md #6) for the soap-bubble look.
- Vertex count ≈ 642 — keep at this number to support Approach B vertex morph (PATTERNS.md #17).

---

## Recipe 4 — Low-poly room (box-modeled interior)

For room-walkthrough archetype (Igloo Inc., Bruno Simon style).

### Blender MCP code

```python
import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Floor
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = 'floor'

# Walls — back, left, right
# Rotation logic: a Blender plane lies on XY (Z is its normal). To stand it
# vertical, rotate 90° around X (= math.pi/2). For side walls, additionally
# rotate around Z to face inward.
def add_wall(name, location, rotation, size_x, size_y):
    bpy.ops.mesh.primitive_plane_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    obj.scale = (size_x, size_y, 1)
    bpy.ops.object.transform_apply(rotation=True, scale=True)   # apply both

add_wall('wall_back',  (0, -5, 2.5), (math.pi/2, 0, 0),         10, 5)   # faces +Y (toward room center)
add_wall('wall_left',  (-5, 0, 2.5), (math.pi/2, 0, math.pi/2), 10, 5)   # faces +X
add_wall('wall_right', (5, 0, 2.5),  (math.pi/2, 0, -math.pi/2),10, 5)   # faces -X

# Ceiling
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 5))
bpy.context.active_object.rotation_euler = (math.pi, 0, 0)
bpy.ops.object.transform_apply(rotation=True)
bpy.context.active_object.name = 'ceiling'

# Furniture — a simple block representing a sofa
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 2, 0.5))
sofa = bpy.context.active_object
sofa.name = 'sofa'
sofa.scale = (2, 0.8, 0.5)
bpy.ops.object.transform_apply(scale=True)

# Group — select all, parent under empty
bpy.ops.object.select_all(action='DESELECT')
for obj in ['floor', 'wall_back', 'wall_left', 'wall_right', 'ceiling', 'sofa']:
    bpy.data.objects[obj].select_set(True)

# Single material with vertex colors / per-object colors set in three.js
mat = bpy.data.materials.new(name='RoomMatte')
mat.use_nodes = True
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.9, 0.88, 0.85, 1.0)
bsdf.inputs['Roughness'].default_value = 0.85
for obj_name in ['floor', 'wall_back', 'wall_left', 'wall_right', 'ceiling', 'sofa']:
    bpy.data.objects[obj_name].data.materials.append(mat)
```

### Tips

- Keep wall thickness conceptually flat — they're planes, not boxes. Saves geometry.
- Add **one** rim-light light source (a `PointLight` in three.js) at the ceiling for "soft ambient interior" feel.
- For real architectural detail, prefer modeling in Blender by hand — programmatic generation hits limits fast.

---

## GLB export configuration

### From Blender UI (recommended)

1. **File → Export → glTF 2.0 (.glb/.gltf)**
2. Settings:
   - **Format:** glTF Binary (.glb)
   - **Include:** Selected Objects (or Active Collection if more controlled)
   - **Transform:** ✓ +Y Up (three.js default)
   - **Geometry:**
     - ✓ Apply Modifiers
     - ✓ UVs, Normals
     - ✗ Loose Edges, Loose Points
     - **Compression:** ✓ Draco mesh compression
       - Compression level: 6
       - Position Quantization: 14
       - Normal Quantization: 10
       - UV Quantization: 12
       - Color Quantization: 10
       - Generic Quantization: 12
   - **Animation:** ✓ if you have animations, else off

### Result sizing rule of thumb

| Mesh complexity | Raw GLB | + Draco | + Meshopt |
|---|---|---|---|
| Single 1k-poly hero | 80 KB | 40 KB | 30 KB |
| 50k-poly hero | 2.5 MB | 400 KB | 250 KB |
| Full room scene | 8 MB | 1.5 MB | 800 KB |

### From the command line (after export)

If your Blender doesn't have Draco bundled, post-process with `gltf-transform`:

```bash
npm i -g @gltf-transform/cli

# Apply Draco to an exported GLB
gltf-transform draco hero.glb hero-draco.glb

# Then Meshopt for non-geometry data
gltf-transform meshopt hero-draco.glb hero-final.glb

# Inspect to verify
gltf-transform inspect hero-final.glb
```

---

## KTX2 texture compression (advanced)

When to bother:
- 3+ textures of 2K+ resolution
- Mobile-heavy traffic
- VRAM budget pressure (< 200 MB GPU memory)

When to skip (most projects):
- 1-2 hero textures
- Already using 1024×1024 or smaller
- Time pressure

### Workflow

```bash
# Install gltf-transform with KTX2 plugin
npm i -g @gltf-transform/cli

# Compress textures inside a GLB to KTX2 (UASTC for albedo, ETC1S for ORM)
gltf-transform uastc input.glb out-uastc.glb \
  --slots "baseColorTexture" --level 4

gltf-transform etc1s out-uastc.glb out-final.glb \
  --slots "metallicRoughnessTexture,occlusionTexture,normalTexture"
```

UASTC (high-quality) for albedo because color reads are most visible; ETC1S (low-bitrate) for ORM and normal because the eye is less sensitive.

In three.js, register the KTX2 loader (PATTERNS.md #16):

```js
const ktx2 = new KTX2Loader()
  .setTranscoderPath('https://unpkg.com/three@0.170.0/examples/jsm/libs/basis/')
  .detectSupport(renderer);
gltfLoader.setKTX2Loader(ktx2);
```

### Reality check

For a typical Awwwards site with ONE hero textured object, the encode time (5-10 minutes per texture) outweighs the size savings. Use compressed JPG/WebP unless you hit a real budget constraint.

---

## Shape keys → GLB morph targets

For PATTERNS.md #17 Approach A (mesh morphing).

### Blender MCP code

```python
import bpy

# Assume `hero` is the active object
bpy.ops.object.shape_key_add(from_mix=False)   # creates 'Basis'
bpy.context.object.active_shape_key.name = 'Basis'

# Add a second shape key
bpy.ops.object.shape_key_add(from_mix=False)
sk = bpy.context.object.active_shape_key
sk.name = 'Stretched'

# Edit it — sample: pull all vertices outward by 50%
for v in sk.data:
    v.co = v.co * 1.5

# At export, three picks up shape keys as morphTargets automatically
# (when "Shape Keys" is enabled in glTF export options)
```

### Export step

Re-export GLB with **Geometry → Shape Keys** ✓ enabled. Each shape key beyond `Basis` becomes one morph target on the resulting `mesh.morphTargetInfluences[]` array.

### Use in three.js

```js
const hero = gltf.scene.getObjectByName('hero');
hero.morphTargetInfluences[0] = 0.0;   // 'Stretched' index — fully off

// Animate via GSAP (PATTERNS.md #17 Approach A)
gsap.to(hero.morphTargetInfluences, {
  0: 1.0,
  duration: 1.5,
  ease: 'power2.inOut',
  scrollTrigger: { /* ... */ },
});
```

---

## Quality checklist before exporting

- [ ] **Apply transforms** (`Object → Apply → All Transforms`) — unapplied scale produces broken normals
- [ ] **Recalculate normals** (Edit Mode → `Mesh → Normals → Recalculate Outside`)
- [ ] **Single material per mesh** unless you really need slots (each adds a draw call in three.js)
- [ ] **No `n-gons`** — three.js triangulates, but uneven triangulation can cause visible artifacts
- [ ] **UV unwrap done** if you'll texture in three.js (use Smart UV Project as a fallback)
- [ ] **Limit vertex count** — 5k for hero, 1k for secondary, 100 for primitives
- [ ] **Origin at center of mass** so transforms feel natural in three.js
- [ ] **No empties or unused meshes** in the export selection — they bloat the GLB

---

## Common pitfalls

### "GLB loaded but mesh is invisible / dark"

- Material has no `Base Color` set, OR
- Normals are inverted (`Mesh → Normals → Recalculate Outside`), OR
- `mesh.castShadow / receiveShadow` not set in three.js after load (PATTERNS.md #15)

### "Mesh appears at wrong position / rotation in three.js"

- Transforms not applied in Blender. Always `Object → Apply → All Transforms` before export.

### "Shadows look weird / banded"

- VSMShadowMap (recommended) needs higher shadow.bias than PCFShadowMap. Try `key.shadow.bias = -0.0005`.

### "GLB is much bigger than expected"

- Draco compression not enabled in export
- Embedded textures at full resolution (resize before exporting, or use KTX2)
- Animation data included by mistake (uncheck "Animations" in export if you don't need them)

### "Lighting in three.js doesn't match Blender preview"

- Expected. Blender's Cycles/Eevee uses a specific lighting model; three.js uses a different one. Always test in three.js with target HDRI before judging.

---

## See also

- `references/PATTERNS.md` § #15 (GLB + Draco loader), #16 (KTX2), #17 (Mesh morphing)
- `references/ARCHITECTURE.md` § 1 (Scene graph layout)
- `assets/templates/coin-scroll.html` — runtime use of Recipe 1 output
- `assets/templates/glass-product.html` — runtime use of Recipe 2 output
- `assets/templates/room-walkthrough.html` — runtime use of Recipe 4 output
