# HDRI — Where to get them, which to pick

Awwwards-grade lighting starts with an HDRI. `MeshStandardMaterial` and `MeshPhysicalMaterial` look flat without one — metals turn black, glass turns gray. This file documents:

1. Free sources (CC0 — no attribution required)
2. Curated picks for Awwwards aesthetics
3. Resolution + file weight guidelines
4. Naming convention for this skill
5. Synthetic alternatives (when you can't ship a file)

---

## Free sources

| Source | License | Quality | URL |
|---|---|---|---|
| **Polyhaven** | CC0 | High | https://polyhaven.com/hdris |
| **HDRIHaven** (legacy) | CC0 | High | redirects to Polyhaven |
| **HDRMaps Free** | CC-BY 4.0 | High | https://hdrmaps.com/freebies/ |
| **HDRI-skies** | Mixed (read each) | Medium | https://hdri-skies.com/free-hdris/ |
| **NoEmotion HDRs** | CC-BY-NC | High | http://noemotionhdrs.net |

**Default to Polyhaven.** It's the cleanest pipeline: search by category, preview, download, attribute-free.

---

## Curated picks for Awwwards aesthetics

The HDRI you choose is a **stronger color decision than your material colors**. Pick deliberately. Below are 8 HDRIs we've used or seen in Site-of-the-Day work, grouped by mood.

### Studio / product / cinematic

- **`studio_small_03`** (Polyhaven) — soft three-point feel, neutral white. The default for product showcase.
- **`photo_studio_01`** (Polyhaven) — slightly warm, larger softbox shape. Good for hero objects with curves.
- **`brown_photostudio_02`** (Polyhaven) — moody, low-key. Glass and dark metals love this.

### Outdoor / atmospheric

- **`royal_esplanade`** (Polyhaven) — late afternoon, warm sun + cool sky. Universal "looks great" backup.
- **`spruit_sunrise`** (Polyhaven) — soft golden hour. Iconic three.js demo HDRI; works for almost anything.
- **`moonless_golf`** (Polyhaven) — twilight, low-light. Use for moody scenes or anything that needs blue ambient.

### Industrial / brutalist

- **`empty_warehouse_01`** (Polyhaven) — fluorescent overhead + bounce off concrete. For tech / architectural product shots.
- **`abandoned_workshop_02`** (Polyhaven) — moodier, warmer warehouse. Good for "discovered artifact" feel.

---

## Resolution + file weight

**Always download 1K.** A PMREM-convolved HDRI samples through filtered mipmaps — the eye cannot tell 1K apart from 4K once it's blurred at typical roughness levels. The file weight difference is dramatic:

| Resolution | Approx file size | When to use |
|---|---|---|
| **1K** (1024×512) | 2–3 MB | **Default.** Web, mobile, anything user-facing. |
| 2K | 8–10 MB | Marginal quality bump for hero objects with mirror polish (`roughness 0.0–0.05`). |
| 4K | 20–35 MB | Never on web. CG renders only. |
| 8K | 80+ MB | Never. |

If you find yourself reaching for 2K or higher to "fix" appearance, the issue is usually elsewhere:
- Tone mapping wrong (`renderer.toneMapping = ACESFilmicToneMapping`?)
- Exposure too low (`renderer.toneMappingExposure = 1.0–1.2`)
- Material `envMapIntensity` < 1.0
- Bloom missing — see `references/POST_PROCESSING.md`

---

## Format choice

Polyhaven offers `.exr` and `.hdr`. Three.js supports both. **Prefer `.hdr`** for web:

| Format | Loader | File weight | Notes |
|---|---|---|---|
| **`.hdr`** (Radiance RGBE) | `RGBELoader` | smaller | Default for this skill. 8 bits per channel + shared exponent. |
| `.exr` | `EXRLoader` | larger | Higher precision, but PMREM convolution discards the difference. |

**Loader code** — see `references/PATTERNS.md` § #9 for the canonical HDRI load + PMREM setup.

---

## Naming convention for this skill

Place downloaded files in this directory (`assets/hdri/`) using kebab-case:

```
assets/hdri/
├── README.md              ← this file
├── studio-small-03.hdr    ← (you'll add)
├── royal-esplanade.hdr
└── empty-warehouse-01.hdr
```

In code, reference relatively from a template:

```js
new RGBELoader().setPath('../hdri/').load('studio-small-03.hdr', ...)
```

(Templates live in `assets/templates/`, so `../hdri/` resolves correctly when the HTTP server is rooted at `assets/` — see each template's `HOW TO RUN` block.)

---

## Synthetic alternatives — when you can't ship a file

If the user wants **single-file portable HTML** and won't host an HDRI alongside, use `RoomEnvironment`. It's a procedural mini-scene of colored panels that PMREM convolves into a usable env-map. Result: ~80% as good as a real HDRI, **zero file weight**.

```js
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
pmrem.dispose();
```

All four templates in this skill (`minimal.html`, `coin-scroll.html`, `room-walkthrough.html`, `glass-product.html`) use `RoomEnvironment` — that's why they're truly self-contained, no HDRI download required.

For **production** sites where you control the asset bundle, swap to a real 1K HDRI for noticeable quality bump on metals and glass. Pattern #9 covers the swap.

---

## Quick decision tree

```
Need glass / mirror polish / showcase metals?
├── Shipping single-file HTML (portfolio, demo)
│   → RoomEnvironment (no download)
└── Have an asset bundle (production site)
    ├── Generic / safe pick → studio-small-03.hdr (Polyhaven, 1K)
    ├── Atmospheric / outdoor → royal-esplanade.hdr or spruit-sunrise.hdr
    └── Moody / dark → moonless-golf.hdr or brown-photostudio-02.hdr
```

---

## See also

- `references/PATTERNS.md` § #9 — HDRI loader code
- `references/PATTERNS.md` § #11 — RoomEnvironment fallback
- `references/POST_PROCESSING.md` § "Why HDR" — bloom + HDRI interaction
- `references/ANTI_PATTERNS.md` § 17 — never ship a 4K HDRI
