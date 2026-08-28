# Design system

The live gallery is at [`/styleguide`](../frontend/src/pages/StyleGuide.jsx); the
tokens are in [`frontend/src/theme.css`](../frontend/src/theme.css) and the
JavaScript half in [`frontend/src/lib/theme.js`](../frontend/src/lib/theme.js).

## The idea

The subject is the phylogenetic profile: a binary presence/absence grid that you
reorder until co-occurrence blocks appear. The interface is built out of that —
hairline rules, 3px corners, dense alignment — rather than out of the rounded
cards and pill buttons that any product could use.

The palette comes from **viridis**, the perceptually-uniform colormap that is the
default in this field and the app's own first colorscale. Its floor is a deep
indigo-violet and its ceiling a chartreuse yellow. Taking the chrome from the
same ramp as the data means the plots sit *inside* the design instead of being
pasted into it, and it is a choice the subject justifies rather than a mood.

Zero is anchored to the page ground (`scaleFor` in `lib/theme.js`). Plotly's
stock viridis starts at a bright purple, which on a dark page makes every
*absent* cell the loudest thing in a presence/absence figure — exactly backwards.

## Tokens

| Token | Value | Use |
|---|---|---|
| `--void` | `#0D0B1A` | page ground; also the zero of every colorscale |
| `--panel` / `--panel-2` / `--panel-3` | `#161230` / `#1E1940` / `#262052` | surfaces, raised surfaces |
| `--rule` | `#2C2560` | hairlines; the only border in the system |
| `--paper` | `#EDEBFA` | primary text |
| `--dim` / `--dim-2` | `#8983B5` / `#635D91` | secondary and tertiary text |
| `--signal` | `#E8E14B` | **actions and presence only** |
| `--flow` | `#35B7A8` | links, structure, dendrograms, edges |
| `--warn` | `#FF7B6E` | failure |
| `--r` / `--r-lg` | `3px` / `5px` | corners |

Elevation is carried by surface lightness and hairlines, not by shadows.

Spend the signal sparingly: it marks what you can act on and what is present.
Section headings, body copy and figure labels are never yellow.

## Type

IBM Plex, self-hosted (latin subsets only), no CDN.

- **IBM Plex Mono** is the *display* face — headings, buttons, labels, counts,
  eyebrows, species keys, e-values. Mono at display size reads as an instrument
  readout, and every identifier this app handles genuinely is fixed-width. It
  works because the headlines are kept short; keep writing them short.
- **IBM Plex Sans** is running text.

Utility text (`.eyebrow`, `.label`, `.k`, `.meta`) is mono, uppercase, tracked
`.1em`. Numbers use `.num` for tabular figures.

## The signature

[`ProfileGrid`](../frontend/src/components/ProfileGrid.jsx) is the one memorable
element: a real presence/absence matrix that reorders itself into co-occurrence
modules, once, on load, with a caption that names each phase. It is the method
being performed rather than an illustration of it, which is why the landing page
has no stock imagery. It honours `prefers-reduced-motion` by rendering the sorted
end state directly.

Everything around it is deliberately quiet. There are no scroll reveals: content
is never gated behind an animation that might not fire.

## Components

Buttons (`.btn` + `-primary` / `-secondary` / `-ghost`), inputs (`.input`,
`.select`), `.card`, `.dropzone`, `.status` (info / success / error, with
`.progress`), `.note`, `.stepper`, `details` disclosures, `.pill-tag`, `.aud`,
`.callout`, and the landing-page pieces `.hero`, `.pipeline`, `.index`,
`.figure`, `.credit`. Tool pages use `.tool-head`, `.toolbar`, `.readout` and
`.canvas`.

Plot chrome comes from `plotLayout()` so every figure shares one grid colour,
one hover style and one type stack. Network views take their constants from
[`lib/network.js`](../frontend/src/lib/network.js).

## Floor

Responsive to mobile, visible keyboard focus (`:focus-visible` in signal),
`prefers-reduced-motion` respected, and no third-party requests at runtime.
