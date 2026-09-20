---
name: Molten Logistics
colors:
  surface: '#fbf9f8'
  surface-dim: '#dbdad9'
  surface-bright: '#fbf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#e9e8e7'
  surface-container-highest: '#e4e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#5c4038'
  inverse-surface: '#303031'
  inverse-on-surface: '#f2f0f0'
  outline: '#916f66'
  outline-variant: '#e6beb3'
  surface-tint: '#b02f00'
  primary: '#ac2d00'
  on-primary: '#ffffff'
  primary-container: '#d73b00'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb5a0'
  secondary: '#765754'
  on-secondary: '#ffffff'
  secondary-container: '#ffd6d2'
  on-secondary-container: '#7b5b58'
  tertiary: '#974139'
  on-tertiary: '#ffffff'
  tertiary-container: '#b65950'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbd1'
  primary-fixed-dim: '#ffb5a0'
  on-primary-fixed: '#3b0900'
  on-primary-fixed-variant: '#872100'
  secondary-fixed: '#ffdad6'
  secondary-fixed-dim: '#e5bdb9'
  on-secondary-fixed: '#2c1514'
  on-secondary-fixed-variant: '#5c403d'
  tertiary-fixed: '#ffdad6'
  tertiary-fixed-dim: '#ffb4ab'
  on-tertiary-fixed: '#400203'
  on-tertiary-fixed-variant: '#7c2d26'
  background: '#fbf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e2'
typography:
  display-metric:
    fontFamily: Inter
    fontSize: 44px
    fontWeight: '800'
    lineHeight: 48px
    letterSpacing: -0.03em
  display-metric-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-metric:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '700'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.06em
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-sm: 0.75rem
  margin: 1rem
  margin-tablet: 1.5rem
  margin-desktop: 2rem
  space-2xs: 0.25rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.25rem
  space-xl: 1.5rem
  space-2xl: 2rem
  space-3xl: 2.5rem
---

## Brand & Style
This design system defines a high-impact, industrial-warm mobile PWA crafted specifically for wholesale poultry logistics operating under intense field conditions. Rooted in an aesthetic termed *Molten Orange on Charcoal*, it fuses tactical utility with energetic, confident branding. 

The visual personality combines the rugged resilience of fleet logistics with sharp digital ergonomics:
- **Architectural Dual-Surface Contrast:** Dark, authoritative framing elements (headers, status overlays, map containers, bottom sheets, floating navigation) anchor the eye in deep Coffee Bean and Black Cherry tones. In direct opposition, operational work surfaces (order manifests, weight tables, customer details) are rendered in high-reflectance alabaster and clean white, maximizing readability under harsh, direct outdoor Mendoza sunlight.
- **Urgent & Tactile Energy:** The palette is ignited by Molten Orange and Racing Red, commanding instant recognition for high-priority dispatches, status shifts, debt alerts, and primary driver interactions.
- **Tone of Voice:** Direct, concise Argentine operational Spanish (*"Cargado"*, *"Pesado"*, *"En reparto"*, *"Entregado"*, *"Cobrar saldo"*). No corporate fluff—pure functional speed.

## Colors
The color strategy enforces distinct operational zones:
- **Primary Accent (`#F74603` Molten Orange):** Drives immediate focus. Applied strictly to primary action pills, the central delivery FAB, active step markers, and real-time operational highlights.
- **Dark Structural Chrome (`#1A0706` Coffee Bean, `#55100D` Black Cherry):** Used for top app bars, floating bottom navigation bars, full-screen map headers, and modal backdrops. This isolates system-level navigation from daylight-dependent content.
- **Daylight-Optimized Canvas (`#F4F2F1` Alabaster Grey background, `#F9F9F9` Card surface):** High-reflectance, glare-resistant surfaces engineered for outdoor delivery drivers inspecting crates and weight slips.
- **Semantic Indicators:** Never rely on color alone; every semantic status pairs color with a dedicated icon and explicit text:
  - **Delivered / Paid (`#1E8E5A`):** Verified completion and cash collected.
  - **In Progress (`#F74603`):** Active delivery and scale processing.
  - **Pending (`#646464`):** Queued or staged at depot.
  - **Overdue Debt / Danger (`#DD0200`):** Unpaid balances, overweight discrepancies, or dispatch cancellation.

## Typography
Typographic clarity is paramount under heavy vibrations and variable sunlight. The system standardizes on clean neo-grotesque geometry (Inter, styled with tight metrics and tabular numerals):
- **Giant Operational Figures (`display-metric`):** Renders between 28px and 44px with extra-bold weight for rapid at-a-glance scanning of crate counts, total kilograms, and cash tallies while unloading the truck.
- **Tabular Numerals (`fontFeatureSettings: "tnum" 1`):** Mandated for all weights (kg), pricing, invoice totals, and telephone contacts to prevent horizontal jitter during rapid balance reconciliation.
- **Micro Labels (`label-caps`):** Used on stepper checkpoints, table headers, and order meta-badges to establish hierarchy above heavy data values.

## Layout & Spacing
The layout uses an adaptive fluid mobile-first grid anchored to an 8pt base unit (with 4pt half-steps for compact status tags):
- **Mobile Handheld (360px - 599px):** 4-column fluid layout with `16px` outer margins and `12px` to `16px` gutters. Content runs edge-to-edge within safe card boundaries. Bottom-padded by `96px` to account for the floating navigation and central elevated FAB.
- **Tablet & Vehicle Mounted (600px - 1023px):** 8-column layout with `24px` margins. Quick-action tiles expand from a 2x2 grid to a 4-column operational strip.
- **Desktop Depot Monitor (1024px+):** 12-column fixed-max layout (max-width `1280px`) with split-pane view (order dispatch queue on left 7 columns, real-time vehicle route and customer metadata on right 5 columns).
- **Physical Touch Target Rule:** All interactive elements maintain an absolute minimum hit area of `48x48px` to guarantee error-free input for drivers wearing work gloves or operating with damp hands.

## Elevation & Depth
Depth is constructed through high-contrast layering and ambient, warm-tinted drop shadows:
- **Level 0 (Field Surface):** Ground layer (`#F4F2F1`). Completely flat without shadow.
- **Level 1 (Card Baseline):** Clean `#F9F9F9` background framed by a subtle 1px border (`#E5E0DE`) and a diffused warm shadow: `0 4px 16px -2px rgba(26, 7, 6, 0.06)`.
- **Level 2 (Hero Operational Cards & Quick Tiles):** Solid `#FFFFFF` or elevated dark cherry `#55100D` with deeper ambient dispersal: `0 8px 24px -4px rgba(26, 7, 6, 0.12)`.
- **Level 3 (Dark Floating Bottom Nav & Overlays):** Near-black `#1A0706` floating capsule elevated above the scroll pane: `0 12px 32px 0 rgba(26, 7, 6, 0.28)`.
- **Level 4 (Molten FAB & Critical Modals):** Accent glow applied to primary FAB: `0 8px 20px 0 rgba(247, 70, 3, 0.38)`.

## Shapes
The shape hierarchy emphasizes friendly ergonomics combined with industrial efficiency:
- **Cards & Operational Panels:** Scaled to `20px` - `24px` corner radii, creating a modern, cushioned pocket aesthetic that protects visual hierarchy on dense lists.
- **Form Inputs & Search Trays:** Standardized at `16px` radius, providing ample inner clearance for large numerals and street addresses.
- **Buttons & Quick-Action Chips:** Fully rounded pills (`9999px` radius) for unambiguous touch affordance.
- **Floating Action Button (FAB):** Perfect geometric circle (`56x56px` minimum footprint).

## Components

### Buttons
- **Primary Operational Button:** Full pill shape, filled with Molten Orange (`#F74603`), text in high-contrast `#FFFFFF` (15px bold). Active/pressed state shifts instantly to Racing Red (`#DD0200`). Height `52px` with a minimum touch target width of `100%` on mobile.
- **Secondary Dark Button:** Coffee Bean (`#1A0706`) background, text in `#FFFFFF`. Used for administrative actions like *"Reasignar Chofer"*.
- **Ghost Action:** Borderless, 14px bold in Molten Orange with active background tint `rgba(247, 70, 3, 0.08)`.

### 4-Dot Order Status Stepper
- **Steps:** `Cargado` -> `Pesado` -> `En reparto` -> `Entregado`.
- **Styling:** Connected by an underlying 3px horizontal track. Completed dots render in solid Delivered Green (`#1E8E5A`) or Molten Orange with an inner checkmark icon. Current active stage pulses with an 8px outer halo of `rgba(247, 70, 3, 0.2)`. Incomplete steps are rendered in neutral grey (`#646464`). Text labels sit below in `label-caps`.

### Hero Metric Card
- **Styling:** Contained within a `24px` radius container. Available in dual styles: Dark Chrome variant (Coffee Bean `#1A0706` background with Black Cherry `#55100D` inner gradient) for summary dashboards, and Crisp Light variant (`#FFFFFF` with `#F4F2F1` border) for delivery lists.
- **Layout:** Displays the aggregate operational metric (`display-metric`, e.g., *"1.420 kg"* or *"$840.500"*) paired with an inline status chip and secondary driver tag (*"Camión 04 • Reparto Norte"*).

### 2x2 Quick-Action Tile Grid
- **Styling:** Four symmetrical rounded tiles (`20px` radius) arranged in a 2-column grid.
- **Content:** Large monochrome icon (28px) placed top-left, giant counter or short directive bottom-left (*"Nuevo Pedido"*, *"Balanza"*, *"Cobranzas"*, *"Ruta GPS"*). Background `#FFFFFF` with active press depth feedback.

### Order Card
- **Styling:** Light surface (`#F9F9F9`), `20px` radius, `16px` inner padding.
- **Structure:** Top row hosts customer commercial name and badge (`status-delivered`, `status-in-progress`, or `status-debt` for overdue balances). Middle block highlights crate counts and total weight in bold tabular format (*"24 Cajones • 480.5 kg"*). Bottom row features direct click-to-call icon button and full-width navigation launch trigger.

### Bottom Sheet
- **Styling:** Dark Chrome container (`#1A0706`), top border radius `24px`, top-centered `36x4px` drag handle in `#646464`.
- **Usage:** Weight scale confirmations, payment capture (Cash / Transferencia / Cuenta Corriente), and delivery signature capture.

### Dark Floating Bottom Navigation & FAB
- **Styling:** Pill-shaped dark dock (`#1A0706`) floating `16px` above screen bottom, spanning 92% screen width. Contains 4 icon-label pairs in muted silver (`#A7A7A7`), turning Molten Orange when active.
- **Central FAB:** Raised `56x56px` circular Molten Orange button breaking the top silhouette of the navigation bar, featuring an oversized plus or QR scanner icon in pure white with molten glow shadow.