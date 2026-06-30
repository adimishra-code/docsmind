# Design Tokens

DocsMind enforces strict semantic tokens to ensure dark mode readiness and easy white-labeling.

## Colors
Defined in `src/index.css` as HSL variables, accessed via `tailwind.config.ts`.
- `--background`: Application backdrop.
- `--foreground`: Primary text color.
- `--card`: Surface color for elevated elements.
- `--primary`: Main CTAs and brand accents.
- `--secondary`: Subdued elements.
- `--muted`: Ghost states, borders, faint backgrounds.
- `--accent`: Active/selected states.
- `--destructive`: Danger (red).
- `--info`: Informational (blue).
- `--success`: Positive (green).
- `--warning`: Caution (yellow).

## Typography
- **Sans**: `Inter`, sans-serif. Used for all primary interface text.
- **Mono**: `JetBrains Mono`, monospace. Used strictly for `CodeBlock` and logs.

## Layout & Radii
- `--radius`: Base border radius (default `0.5rem`).
- Spacing relies on Tailwind's default scales, ensuring consistent rhythm.
- `container` is horizontally centered with a `2rem` padding and a max width of `1400px` (`2xl`).

## Motion
- Custom animations configured in Tailwind: `accordion-down`, `accordion-up`.
- `framer-motion` is utilized for layout transitions and micro-interactions, strictly adhering to `.2s ease-out` bounds.
