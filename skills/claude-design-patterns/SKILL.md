---
name: claude-design-patterns
description: Engineering rules and reusable patterns for building polished web UI, React artifacts, slide decks, animations, and device mockups — distilled from Anthropic's leaked Claude Design agent system prompt. Use ALONGSIDE the frontend-design skill whenever building or iterating on visual web output: single-file React/HTML artifacts, presentation decks, design-variation explorations, or live-tweakable demos. Covers React/Babel pinning, style-collision avoidance, the live-edit "Tweaks" postMessage protocol, starter-component patterns, the ask-first/expose-variations methodology, and the verifier-agent finishing pass.
---

# Claude Design — portable engineering patterns

Companion to `frontend-design` (which covers aesthetic direction). This file is the
*engineering* layer: how Anthropic's Claude Design agent actually builds web artifacts.
Sourced from the leaked Claude Design system prompt (github.com/asgeirtj/system_prompts_leaks
`Anthropic/claude-design.md`); `/mnt`-path and proprietary-tool machinery stripped — only
the environment-agnostic rules are kept.

## React + Babel pinning (single-file artifacts)

Pin exact versions (never floating ranges like `react@18`) and add Subresource
Integrity — fetch current `sha384-…` hashes from srihash.org or the unpkg response,
don't hardcode stale ones:

```html
<script src="https://unpkg.com/react@18.3.1/umd/react.development.js"
  integrity="sha384-…" crossorigin="anonymous"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js"
  integrity="sha384-…" crossorigin="anonymous"></script>
<script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js"
  integrity="sha384-…" crossorigin="anonymous"></script>
```

## Style-object collision rule

Global-scoped style objects MUST have unique, specific names per component — a bare
`const styles = {...}` collides the moment two components share scope.

```js
const terminalStyles = { ... }   // ✅ not `styles`
const inputStyles = { ... }
```
Or use inline styles to sidestep the problem entirely.

## Multi-file Babel — window-export pattern

Each `<script type="text/babel">` transpiles in an isolated scope. To share components
across scripts, export explicitly at the end of the defining file, then reference via `window.`:

```js
Object.assign(window, { Terminal, Line, Gray, Blue, Bold });
// elsewhere: <window.Terminal />
```

## Live-edit "Tweaks" protocol

Make ONE main file with in-design controls instead of many variant files. Handshake:

1. Register the listener **before** announcing availability:
   ```js
   window.addEventListener('message', (e) => {
     if (e.data.type === '__activate_edit_mode') { /* show Tweaks panel */ }
     else if (e.data.type === '__deactivate_edit_mode') { /* hide it */ }
   });
   ```
2. Then announce: `window.parent.postMessage({type: '__edit_mode_available'}, '*')`
3. On change, persist: `window.parent.postMessage({type: '__edit_mode_set_keys', edits: {fontSize: 18}}, '*')`
4. Wrap the defaults in JSON markers the host rewrites on disk:
   ```js
   const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{ "primaryColor": "#D97757", "fontSize": 16 }/*EDITMODE-END*/;
   ```
Label the panel exactly **"Tweaks"** so it matches the toolbar toggle. Expose the
dimensions the user actually cares about (color, copy, layout, features).

## Starter components (build these patterns when relevant)

| Pattern | Purpose |
|---|---|
| `deck_stage` | Slide-deck shell: viewport scaling, keyboard nav, slide-count overlay, speaker-notes, localStorage, print-to-PDF. Use for ANY slide presentation. |
| `design_canvas` | Present 2+ static options side-by-side in a labeled grid. |
| `animations` | Timeline engine: Stage + Sprite + scrubber + Easing + interpolate. |
| `ios_frame` / `android_frame` | Phone mockups with status bar + keyboard. |
| `macos_window` / `browser_window` | Desktop window / browser chrome. |

Fixed-size content (decks, video) scales to the viewport with a letterboxed black
background; put controls *outside* the scaled element. Avoid `scrollIntoView`.

## Methodology

- **Ask first** for ambiguous briefs (~10 questions): starting point (UI kit / design
  system / codebase / screenshots / Figma), how many variations, which dimensions
  (visual, interaction, copy), novelty expectations. (One clarifying batch, not drip-fed.)
- **Plan visually, expose 3+ variations**: lead with a short design-assumptions comment,
  show the user early, then iterate. Mix by-the-book with novel; vary color, layout,
  typography, iconography, interaction; start basic → get more advanced.
- **Iterate with Tweaks, not new files.**

## Finishing — verifier pass

Mirror the `fork_verifier_agent` pattern with this repo's setup: after the build, confirm
no console crashes, then spawn an independent screenshot/layout check (the bundled
`grounding-verifier` agent or a Playwright/cloakbrowser screenshot pass) rather than
self-certifying. Don't proactively screenshot mid-build unless doing a directed check.

## Guardrails

≥24px text on 1920×1080 slides; ≥44px touch targets on mobile. Prefer CSS grid and
`text-wrap: pretty`. Avoid: aggressive gradients and AI-slop tropes, rounded containers
with left-border accents, overused fonts (Inter/Roboto/Arial without reason), emoji unless
the system uses them, and hand-drawn SVG imagery (use placeholders + ask for real assets).
Refuse to reproduce copyrighted/proprietary UI unless the user works at that company.
