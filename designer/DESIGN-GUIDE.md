# Supercat Weather — Design Guide

## Visual Language

### Glassmorphism
The card uses `backdrop-filter: blur(20px)` with `rgba(255, 255, 255, 0.08)` background for a frosted glass effect. This creates depth while keeping content readable. The subtle `1px` border at `rgba(255, 255, 255, 0.12)` defines the card edge.

### Typography
- **Font**: Inter (300/400/500/600/700 weights) — clean, highly legible at small sizes
- **Fallback**: `-apple-system, BlinkMacSystemFont, sans-serif` for instant render
- **Scale**:
  - Temperature: 72px (desktop) / 56px (mobile), weight 700
  - City name: 28px, weight 600
  - Detail values: 18px, weight 600
  - Labels: 11px, uppercase, letter-spacing 0.5px

### Color System

#### Dark Theme (default)
- Background: `#0f0c29 → #302b63 → #24243e` (deep purple gradient)
- Card: rgba white with blur
- Text: white at varying opacities (100% → 85% → 60% → 45% → 25%)

#### Light Theme
- Card: `rgba(255, 255, 255, 0.82)` — high opacity frosted glass
- Text: `#1a1a2e` — dark navy
- Interactive elements: dark opacities instead of white

#### Weather-driven backgrounds
Each weather condition triggers a gradient background:
| Condition | Gradient | Animation |
|-----------|----------|-----------|
| Sunny | Pink → coral → orange (`#f093fb` → `#f5576c` → `#fda085`) | 12s shift |
| Clear night | Deep purple → dark blue | Static |
| Cloudy | Steel blue (`#667db6` → `#4a6fa5`) | 18s shift |
| Foggy | Grey-blue (`#606c88` → `#3f4c6b`) | Static |
| Rainy | Dark grey → blue (`#373b44` → `#4286f4`) | Static |
| Snowy | Light grey → blue-grey (`#e6dada` → `#8ba3c7`) | Static |
| Thunderstorm | Dark navy → midnight blue | 8s shift |

### UV Index colors
| Range | Class | Color |
|-------|-------|-------|
| 0–2 | uv-low | `#4ade80` (green) |
| 3–5 | uv-moderate | `#facc15` (yellow) |
| 6–7 | uv-high | `#fb923c` (orange) |
| 8–10 | uv-very-high | `#ef4444` (red) |
| 11+ | uv-extreme | `#a78bfa` (purple) |

## Component Patterns

### Cards (detail-item, forecast-day, hourly-item)
- Background: `rgba(255, 255, 255, 0.06)`
- Border-radius: 16px
- Hover: translateY(-4px) + background brighten
- Animation: staggered fadeUp (0.05s–0.75s delay)

### Buttons / Controls
- Tab-style segmented controls for forecast view
- Border-radius: 10px–12px
- Active state: `rgba(255, 255, 255, 0.15)` background
- Inactive: transparent, 50% opacity text
- Hover: text brightens to 80%

### Search
- Input: 16px border-radius, translucent background
- Dropdown: glassmorphism, max-height 240px, scrollable
- Selection: keyboard (Arrow keys + Enter) and mouse
- Highlighted item: `rgba(255, 255, 255, 0.1)` background

## Interaction Design

### Micro-interactions
- **Refresh button**: 0.6s spin animation on click
- **View toggle**: 0.3s fade + slide between daily/hourly
- **Temperature pulse**: subtle 3s scale oscillation
- **Weather icon float**: 4s vertical float, combined with weather-specific animations
- **Precipitation bars**: 0.4s width transition

### Weather-specific icon animations
| Condition | Animation |
|-----------|-----------|
| Sunny | 12s slow spin + float |
| Cloudy | 6s horizontal drift + float |
| Rainy | 1s bounce + float |
| Thunderstorm | 3s flash + float |
| Snowy | 5s drift + float |
| Foggy | 4s opacity pulse |
| Clear night | 3s twinkle + float |

### Atmospheric effects
- **Rain**: multi-layer diagonal repeating lines, 0.4s fall animation
- **Snow**: radial gradient flakes, 8s downward drift
- **Thunderstorm**: rain + random lightning flashes (8s cycle)
- **Lightning**: opacity flicker at 92%/95%/97% keyframes

## Accessibility (a11y)

### WCAG compliance
- All interactive elements have visible `:focus-visible` outlines (2px white, 2px offset)
- Search results use `aria-selected` for keyboard navigation
- `role="combobox"` + `aria-expanded` + `aria-controls` on search input
- `role="listbox"` on results container
- `role="tablist"` / `role="tab"` / `role="tabpanel"` on forecast toggle
- Icons have `role="img"` + `aria-label` with text descriptions
- `aria-live="polite"` on primary weather display
- `aria-hidden="true"` on decorative elements (loading bar, scroll fade)

### Reduced motion
- `@media (prefers-reduced-motion: reduce)` disables all animations
  - Background gradients stop shifting
  - Weather particles stop moving
  - FadeUp animations disabled
  - Spinner stops spinning

### Color contrast
- Dark theme: white text on dark gradients — contrast ratio exceeds 7:1
- Light theme: `#1a1a2e` on `rgba(255,255,255,0.82)` — ~10:1
- Snowy/foggy themes: dark text (`#1a1a2e`) on light backgrounds
- UV colors on both themes checked for legibility

### Touch targets
- All interactive elements minimum 44px (mobile-optimized)
- Search results: 44px+ tap targets
- Forecast toggle: padded buttons with 4px gap

## Responsive Behavior

### Breakpoint: 480px
- Card padding: 36px → 24px
- Temperature: 72px → 56px
- Details grid: 4 columns → 2 columns
- Hourly items: 76px → 64px min-width
- Forecast gap reduced

### PWA
- `viewport-fit=cover` for notched devices
- `apple-mobile-web-app-status-bar-style: black-translucent`
- Theme color: `#302b63`
- Standalone display mode
- Portrait orientation lock

## Future Design Opportunities

1. **Animated SVG icons**: replace emoji weather icons with custom SVG illustrations
2. **Expanded detail panel**: tap a detail card to see hourly trend chart
3. **Weather alerts**: visual banner system for extreme weather warnings
4. **Splash screen**: PWA splash screen matching the app theme
5. **Drag-to-refresh**: pull down gesture on mobile
6. **Wind particle effect**: animated wind lines during windy conditions
7. **Sun path visualization**: arc showing sun position across the day
