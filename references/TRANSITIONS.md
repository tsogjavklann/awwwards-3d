# TRANSITIONS — page transitions for 3D experiences

Page transitions are the difference between "site with multiple pages" and "single connected experience". Awwwards expects: **smooth fade or morph between routes, with the WebGL canvas continuing to render across the transition**.

Three real options:
1. **Native View Transitions API** — easiest, modern browsers only
2. **Barba.js** — battle-tested, works everywhere, MIT license
3. **Custom GSAP transition** — full control, more code

This file covers all three. Pick based on browser support and complexity needs.

---

## Decision tree

```
Need to support Safari < 18 / older Chrome?
├── Yes → Barba.js  (option 2)
└── No → Want full control over the choreography?
    ├── Yes → Custom GSAP  (option 3)
    └── No → View Transitions API  (option 1)
```

For most Awwwards work, **Barba.js** is the safe default. View Transitions are great but Safari support is recent.

---

## Option 1 — View Transitions API (modern)

### Browser support

- Chrome 111+, Edge 111+, Opera 97+ (March 2023)
- Safari 18.0+ (Sept 2024)
- Firefox: behind flag as of early 2026

For sites that don't need to support older browsers, this is the cleanest solution.

### Same-document transitions (SPA-style)

```js
async function navigate(targetUrl) {
  if (!document.startViewTransition) {
    // Fallback for unsupported browsers
    window.location.href = targetUrl;
    return;
  }

  const html = await fetch(targetUrl).then((r) => r.text());
  const newDoc = new DOMParser().parseFromString(html, 'text/html');

  document.startViewTransition(() => {
    document.title = newDoc.title;
    document.querySelector('main').replaceWith(newDoc.querySelector('main'));
  });
}

// Hijack all internal links
document.addEventListener('click', (e) => {
  const link = e.target.closest('a');
  if (!link || link.target === '_blank' || link.origin !== location.origin) return;
  e.preventDefault();
  navigate(link.href);
  history.pushState(null, '', link.href);
});

window.addEventListener('popstate', () => navigate(location.href));
```

### Style the transition

```css
::view-transition-old(root) {
  animation: 0.4s ease-out both fade-out;
}
::view-transition-new(root) {
  animation: 0.4s 0.1s ease-in both fade-in;
}

@keyframes fade-out { to { opacity: 0; transform: scale(0.98); } }
@keyframes fade-in  { from { opacity: 0; transform: scale(1.02); } }
```

### Cross-document transitions (MPA-style, Chrome 126+)

```css
@view-transition { navigation: auto; }
```

That's it — Chrome handles the rest, including for full-page navigations. Currently Chromium-only.

### WebGL canvas during the transition

The canvas keeps rendering. View Transitions snapshot the visible page and animate between snapshots. So:

- Position the canvas as `position: fixed` outside `<main>` (so swapping `<main>` doesn't tear the canvas)
- Continue your `requestAnimationFrame` loop without interruption
- The transition affects only DOM layers above/below the canvas, not the canvas itself

If you want the canvas itself to crossfade, mark it as a separate view-transition layer:

```css
canvas { view-transition-name: webgl; }
::view-transition-group(webgl) { animation-duration: 0.6s; }
```

---

## Option 2 — Barba.js

[`@barba/core`](https://barba.js.org/) is the production standard for SPA-style transitions across page templates. Excellent integration with GSAP.

### Install

Barba 2.10.x is the current major. Pin to a specific patch version (the codebase has been stable since 2.10.0; 2.10.3 is what was tested for this skill):

```html
<script type="importmap">
{
  "imports": {
    "@barba/core": "https://esm.sh/@barba/core@2.10.3"
  }
}
</script>
```

If `2.10.3` is unavailable on esm.sh, fall back to the floating minor: `https://esm.sh/@barba/core@^2.10.0`. Verify in a browser before relying on it — the API hasn't broken in 2.10.x but a CDN cache miss can serve a stale version briefly.

### Setup

```js
import barba from '@barba/core';
import gsap from 'gsap';

barba.init({
  preventRunning: true,    // ignore clicks during a running transition
  transitions: [{
    name: 'fade',
    leave({ current }) {
      return gsap.to(current.container, {
        opacity: 0,
        y: -30,
        duration: 0.6,
        ease: 'power2.inOut',
      });
    },
    enter({ next }) {
      return gsap.from(next.container, {
        opacity: 0,
        y: 30,
        duration: 0.6,
        ease: 'power2.inOut',
      });
    },
  }],
});
```

### HTML structure

Each page wraps content in `data-barba="container"` with a unique `data-barba-namespace`:

```html
<body>
  <canvas id="webgl"></canvas>
  <div data-barba="wrapper">
    <main data-barba="container" data-barba-namespace="home">
      <!-- home content -->
    </main>
  </div>
</body>
```

Barba swaps the `data-barba="container"` element with the new page's container; everything outside (canvas, header, footer) persists.

### Integrating with the WebGL scene

The canvas keeps rendering through transitions. Hook into Barba's lifecycle to update the scene per route:

```js
barba.hooks.afterEnter(({ next }) => {
  const ns = next.namespace;
  if (ns === 'home') {
    state.cameraZ.target = 6;
    hero.visible = true;
  } else if (ns === 'about') {
    state.cameraZ.target = 4;
    hero.visible = false;
  }
});
```

### Refresh ScrollTrigger after each transition

ScrollTrigger caches document height. After Barba swaps content, refresh:

```js
barba.hooks.after(() => {
  ScrollTrigger.refresh();
  // re-bind any per-page reveal triggers:
  initReveals();
});
```

### Persisting state during transitions

```js
barba.hooks.beforeLeave(({ current }) => {
  // Save scroll position per route
  const scrolls = JSON.parse(sessionStorage.getItem('scrolls') || '{}');
  scrolls[current.url.path] = window.scrollY;
  sessionStorage.setItem('scrolls', JSON.stringify(scrolls));
});

barba.hooks.afterEnter(({ next }) => {
  const scrolls = JSON.parse(sessionStorage.getItem('scrolls') || '{}');
  const y = scrolls[next.url.path] || 0;
  lenis.scrollTo(y, { immediate: true });
});
```

---

## Option 3 — Custom GSAP transition

When you want full control over choreography (e.g. WebGL morph + DOM fade synchronized).

### Pattern

```js
async function transitionTo(url) {
  // 1. Start the WebGL "leaving" animation
  const webglOut = gsap.to(state.cameraZ, {
    target: 12,
    duration: 0.8,
    ease: 'power3.in',
  });

  // 2. Start the DOM fade-out in parallel
  const domOut = gsap.to('main', {
    opacity: 0,
    y: -20,
    duration: 0.6,
    ease: 'power2.inOut',
  });

  // 3. Fetch new page in parallel
  const fetchPage = fetch(url).then((r) => r.text());

  // 4. Wait for all three
  const [_, __, html] = await Promise.all([webglOut, domOut, fetchPage]);

  // 5. Swap content
  const doc = new DOMParser().parseFromString(html, 'text/html');
  document.title = doc.title;
  document.querySelector('main').replaceWith(doc.querySelector('main'));
  history.pushState(null, '', url);

  // 6. Reset scroll
  window.scrollTo(0, 0);
  ScrollTrigger.refresh();

  // 7. Animate WebGL + DOM back in
  gsap.to(state.cameraZ, { target: 6, duration: 1.2, ease: 'power3.out' });
  gsap.from('main', { opacity: 0, y: 20, duration: 0.8, ease: 'power2.out', delay: 0.2 });
}

document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href^="/"]');
  if (!link) return;
  e.preventDefault();
  transitionTo(link.href);
});
```

This pattern gives you total control over:
- WebGL camera movement during the transition
- The exact timing relationship between scene change and DOM swap
- What persists vs what resets

---

## Choreography ideas

### "Plunge through" (vertical scene change)

- camera dollies down + fades to black
- DOM swaps in black frame
- camera rises into the new scene

```js
gsap.timeline()
  .to(state.cameraY, { target: -20, duration: 0.6, ease: 'power3.in' })
  .to('#blackFrame', { opacity: 1, duration: 0.4 }, 0.2)
  .call(() => swapDOM())
  .set(state.cameraY, { current: 20, target: 20 })
  .to(state.cameraY, { target: 1.2, duration: 0.8, ease: 'power3.out' })
  .to('#blackFrame', { opacity: 0, duration: 0.4 }, '-=0.6');
```

### "Hero morph" (object continuity)

The hero object is the **same** across two pages, but its scale/position morphs to the new layout. No fade — just a dolly/scale.

```js
// Before navigation, get the new hero's target position from the next page's data
const nextLayout = await fetch(`${url}/layout.json`).then((r) => r.json());

gsap.timeline()
  .to(hero.position, { x: nextLayout.x, y: nextLayout.y, duration: 1.2, ease: 'power3.inOut' })
  .to(hero.scale, { x: nextLayout.scale, y: nextLayout.scale, z: nextLayout.scale, duration: 1.2, ease: 'power3.inOut' }, 0)
  .call(() => swapDOM());
```

### "Camera shutter" (cinematic black bars)

```js
gsap.timeline()
  .to('.shutter-top, .shutter-bottom', { y: 0, duration: 0.5, ease: 'power3.inOut' })
  .call(swapDOM)
  .to('.shutter-top', { y: '-100%', duration: 0.5, ease: 'power3.inOut', delay: 0.1 })
  .to('.shutter-bottom', { y: '100%', duration: 0.5, ease: 'power3.inOut' }, '<');
```

---

## Persisting WebGL across navigations

The single biggest win for "feels like one experience": don't tear down the WebGL scene between routes. Keep:

- `renderer`, `scene`, `camera` — all module-level
- The `tick()` loop running uninterrupted
- HDRI / textures loaded once

What changes per route:
- `state.cameraY.target`, `state.cameraZ.target` (route-specific framing)
- Visibility of objects (`hero.visible = ...`)
- `ScrollTrigger` setup for the new page's sections

What gets torn down per route (if needed):
- ScrollTrigger instances (`ScrollTrigger.getAll().forEach(t => t.kill())` then re-init)
- DOM-side event listeners

```js
const sceneState = {};   // module-level: persists across routes

function init() {
  /* ... renderer, scene, camera, environment, lighting, hero ... */
  tick();   // never returns
}

function configureRoute(namespace) {
  ScrollTrigger.getAll().forEach((t) => t.kill());

  switch (namespace) {
    case 'home':
      state.cameraZ.target = 6;
      // re-bind home's ScrollTriggers
      break;
    case 'about':
      state.cameraZ.target = 4;
      // re-bind about's ScrollTriggers
      break;
  }
}

barba.init({ /* ... */ });
barba.hooks.afterEnter(({ next }) => configureRoute(next.namespace));

init();
configureRoute('home');
```

---

## Common pitfalls

### "ScrollTrigger fires at the wrong time after transition"

Cause: ScrollTrigger cached the OLD page's height. Fix: `ScrollTrigger.refresh()` in `barba.hooks.after()`.

### "Lenis stays scrolled to the previous position after transition"

Cause: `lenis.raf` continued reading old scroll. Fix: `lenis.scrollTo(0, { immediate: true })` after content swap.

### "Canvas flickers / goes black during transition"

Cause: View Transitions API snapshotting the canvas while it has a stale frame. Fix: render one final frame BEFORE starting the transition:

```js
composer.render();   // force one fresh frame
document.startViewTransition(() => { /* ... */ });
```

### "Page jumps to top of new page"

Cause: not preserving scroll position. Fix: see "Persisting state during transitions" pattern above (Barba example).

### "Two transitions overlap when user clicks fast"

Cause: missing `preventRunning: true` (Barba) or no in-flight guard (custom). Fix: add a state flag:

```js
let inFlight = false;
async function transitionTo(url) {
  if (inFlight) return;
  inFlight = true;
  try { /* ... */ } finally { inFlight = false; }
}
```

---

## Reading order

- Most common case: skim §1 (View Transitions) and §2 (Barba). Pick one.
- Custom choreography: §3 + "Choreography ideas".
- Always read "Persisting WebGL across navigations" — this is the win.
- Debugging: "Common pitfalls".
