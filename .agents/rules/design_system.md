# Visual Design & Cyberpunk Style Guide

The entire CapriPet interface must strictly adhere to the **Cyberpunk 2077 Military-Corpo Tech / HUD** aesthetic fused with the identity of a **feral Rogue AI / I-Skin ("эскин" — sentient escaped entity from beyond the Blackwall)**. Capri is not a benign virtual assistant: she is an unstable, aggressive cyber-entity whose manifestation corrupts and tears through the host system:

1. **Geometry & Framing:**
   - **Chamfered / Cut Corners:** Avoid soft rounded corners (`border-radius`). Instead, use 45-degree chamfers, cut-outs (`_CORNER_CUT`), and asymmetrical angular frames.
   - **Corner Brackets & Technical Crosshairs:** Frame containers with corner brackets, caliper ticks, technical notch markers, and micro-grid indicators (e.g. Acid Green / Neon Crimson corner brackets).
   - **Section Separators:** Crisp, thin technical divider lines (`1px`), dotted/dashed guides, or linear gradients fading into transparency.
   - **Hostile Enclosures:** Asymmetrical hazard framing, diagonal warning stripes (`draw_hazard_frame`), and fragmented containment border lines representing breached sandbox constraints.

2. **CRT, Holo Display & Rogue AI Glitch Elements:**
   - **Scanlines:** Fine horizontal scanlines (`1px` lines every 2–3px with low alpha like `rgba(246, 2, 63, 0.07)`).
   - **Digital Noise, Datamosh & Tearing:** Screen slit slicing, datamosh displacement, line tearing, high-frequency sprite jitter/vibration, and chromatic RGB aberration. Visual elements should appear volatile, as if the OS is struggling to render and contain an intrusive intelligence.
   - **Blackwall Fractures & Lightning Arcs:** Energetic effects must favor angular 90° Manhattan bus paths, stepped fractured geometry, red/crimson discharge with blistering white overdrive cores, and secondary parasitic arcs rather than smooth natural curves.
   - **Holographic Glow & Glass:** High-contrast solid Obsidian Black (`#020106`) bases with crisp neon borders; avoid generic translucent blur/aero unless it represents a CRT phosphorescent panel.

3. **Typography, Telemetry & Rogue Identity:**
   - **Font Stack:** Technical / terminal monospace fonts: `"Press Start 2P"`, `"Pixelify Sans"`, `"VT323"`, `"Terminus"`, `"JetBrains Mono"`, `"DejaVu Sans Mono"`, `monospace`.
   - **Hostile Telemetry & Glitch Glyphs:** Prefix titles, borders, and overlays with tactical rogue AI metadata tags and hex leaks (e.g. `CAPRI//ONLINE`, `[SYS.LOAD: 42%]`, `▶ CAPRI//AWAITING_INPUT // [STATUS]`, `0xDEADBEEF`, `BLACKWALL // BREACH`, `NULL_PTR`, `CORRUPT`).
   - **Typewriter Effect & Block Cursors:** Text input and recognition output should appear via rapid typewriter effect accompanied by block cursor pulses (`█`).
   - **Status Indicators:** Micro LED dots, animated audio equalizer bars, blinking recording/sync markers, and unstable rotating combat/target reticles.

4. **Audio Identity (Sound Design):**
   - **Rogue AI Soundscapes:** Audio cues should incorporate heavily saturated sub-bass drops, high-frequency capacitor whines, digital distortion/clipping via hyperbolic tangent saturation, and electrical static snaps rather than soft acoustic chime tones.

## Character Palette (Strict)

Capri's visual identity uses **only** the following colors:

| Color | Hex | Approx. share |
| --- | --- | --- |
| Neon crimson | `#F6023F` | 45% |
| Obsidian black | `#020106` | 35% |
| Acid green | `#06F868` | 16% |
| White | `#F9F9F9` | 2% |
| Electric blue | `#126EE9` | 1.5% |
| Neon violet | `#9E1FDE` | 0.5% |

**Mandatory rule:** no other colors are allowed. Any new or modified UI, HUD, glitch, transition, effect, particle, lightning, animation, or overlay must be built exclusively from this palette. Do not introduce extra hues, gradients to foreign colors, or hard-coded colors outside this list. Use the percentage shares as the intended visual balance, not as a requirement to use every color in every effect.
