# PhyloFlask Design System

Read this **before touching any UI**. It defines the look, the tokens, and the
ready-made components so every page stays consistent and polished. A live gallery
of all components is at **`/styleguide`** (template: `pages/styleguide.html`) —
copy markup from there.

> Stack: Flask + Jinja + vanilla HTML/CSS/JS. The whole theme lives in
> `frontend/src/theme.css`, imported once by `frontend/src/main.jsx`. Every page
> renders inside `components/Layout.jsx`
> (clean top navbar + footer). `index.html` is a standalone bento landing.
> With `debug=False`, **restart the server** to see template changes.

## 1. Principles
- **Light "biotech SaaS"** — white surfaces, soft shadows, rounded corners,
  generous whitespace. Friendly and clean (Airbnb / Pinterest feel), not flashy.
- **Calm colour** — neutral surfaces; one blue accent; colour only to encode
  meaning (clusters, status). Black pills for primary actions.
- **Content first** — centred column (`max-width` ~980px for docs/forms), lots
  of breathing room, clear hierarchy.
- **Motion is subtle** — fade-ins, hover lifts; respect `prefers-reduced-motion`.

## 2. Tokens (CSS variables, in `:root`)
| Token | Value | Use |
|-------|-------|-----|
| `--bg` / `--bg-2` | `#eaeef6` / `#f6f8fc` | page background |
| `--surface` / `--surface-2` | `#ffffff` / `#f3f5fa` | cards / insets |
| `--text` / `--text-2` / `--text-3` | `#0e1726` / `#586074` / `#8b93a5` | heading / body / hint |
| `--line` / `--line-2` | `rgba(18,28,54,.10)` / `.16` | borders |
| `--ink` | `#111827` | black pill buttons |
| `--accent` / `--accent-soft` | `#2f6bff` / `#e7eeff` | links, active, focus |
| `--teal` | `#0bb39a` | secondary / success bio accent |
| `--radius` / `--radius-sm` / `--pill` | 16 / 11 / 999px | corners |
| `--shadow` / `--shadow-hover` | `0 10px 30px rgba(20,30,60,.08)` / `.14` | elevation |
| `--font` / `--font-display` | Inter / Space Grotesk | body / headings |

Spacing: use rem rhythm (`1rem 1.5rem 2rem`), px for component-internal gaps
(8/12/16). Headings use `--font-display`; never hardcode colours — use the vars.

## 3. Components (class → what + when)
All are defined in `tools.css`. Minimal example HTML for each is in `/styleguide`.

- **Buttons** — `.futuristic-btn` (primary black pill), `.futuristic-btn-secondary`
  (white outline pill). Disabled = light grey, never a dark blob. Landing uses
  `.btn-pill.btn-dark` / `.btn-ghost`. Always pill-shaped, with an optional leading icon.
- **Inputs / selects** — `.futuristic-input`, `.futuristic-select` (white, light
  border, blue focus ring). Bare `<input>/<select>` are themed too.
- **Drop-zone** — `.dropzone` with `.dz-icon/.dz-title/.dz-hint` + a hidden file
  input; pair with `.file-pill` to confirm the chosen file. Wire via `Phylo.dropzone`.
- **Cards** — `.doc-card` (content card), `.tool-card` (clickable, landing/grid),
  `.mini` (small feature card). White, soft shadow, hover-lift.
- **Stat card** — `.stat` / `.stat.alt` (big number `.n`, label `.l`); dark or white.
- **Pill tag** — `.pill-tag` (keyword chip with leading icon).
- **Callout** — `.callout` + `.callout.bio` / `.callout.cs` (left-accent info box).
- **Status** — `.tool-status` `.show` + `.is-info/.is-error/.is-success`; add a
  `.tool-progress`. Loader = `.tool-loader.show` (spinner + caption). Result hint = `.tool-note`.
- **Stepper** — `.tool-stepper` with `.tool-step` (`.done/.active`) + `.bar`.
- **Badges** — `.aud.bio` / `.aud.cs` (audience tags in docs).
- **Chrome** — `.site-nav` (sticky top navbar), `.site-footer` (3-col), `.site-main`
  (centred container). These come from `components/Layout.jsx`; pages render into its `<Outlet/>`.

## 4. Layout patterns
- **Tool page** — a component under `src/pages/`, rendered by the router, with a
  `<section class="wrapper style1 fade-up"><div class="inner">…</div></section>`.
  Start with a `.tool-stepper`, an `<h1>`, one `<p>` intro, a `.dropzone`, a
  primary button, then `.tool-status` + a results area.
- **Doc page** (help/faq) — `.inner` with a `.doc`/`.faq` wrapper (max-width ~960),
  cards / `<details>` accordions, generous spacing.
- **Landing** — bento grid: stat cards row + display `<h1>` + CTA on the left,
  an art card (SVG molecule) + glass card on the right; pill tags; tool grid; about.

## 5. Visualisation on light
Graph/SVG backgrounds = `--surface`; edges/links = `rgba(18,28,54,.12–.22)`;
node fills use the cluster/genus colours (they read on white); tooltips are dark
cards (`#111827` + white text). Heatmap 0-cells faint, 1-cells `--accent`/coral.

## 6. Do / Don't
- ✅ Use the tokens & component classes; copy from `/styleguide`.
- ✅ Centre content, keep whitespace, round corners, soft shadows.
- ✅ Keep one accent; colour-code only meaning.
- ❌ No hardcoded hex in page styles (breaks dark text / theming).
- ❌ No white `<strong>` (HTML5UP did this — `tools.css` forces it dark; keep it).
- ❌ No fixed pixel widths on visualisations — fluid + responsive.
- ❌ No dependence on HTML5UP scroll JS (`.fade-up` is neutralised).

## 7. Accessibility
Sentence case; `label for` on inputs; `aria-live` on status; sufficient contrast
(text on `--surface` ≥ 4.5:1); keep `prefers-reduced-motion` honoured; icon-only
buttons get `aria-label`.
