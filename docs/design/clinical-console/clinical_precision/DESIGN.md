---
name: Clinical Precision
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#444653'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#757684'
  outline-variant: '#c4c5d5'
  surface-tint: '#3755c3'
  primary: '#00288e'
  on-primary: '#ffffff'
  primary-container: '#1e40af'
  on-primary-container: '#a8b8ff'
  inverse-primary: '#b8c4ff'
  secondary: '#006c4a'
  on-secondary: '#ffffff'
  secondary-container: '#82f5c1'
  on-secondary-container: '#00714e'
  tertiary: '#700006'
  on-tertiary: '#ffffff'
  tertiary-container: '#9b000d'
  on-tertiary-container: '#ffa399'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dde1ff'
  primary-fixed-dim: '#b8c4ff'
  on-primary-fixed: '#001453'
  on-primary-fixed-variant: '#173bab'
  secondary-fixed: '#85f8c4'
  secondary-fixed-dim: '#68dba9'
  on-secondary-fixed: '#002114'
  on-secondary-fixed-variant: '#005137'
  tertiary-fixed: '#ffdad6'
  tertiary-fixed-dim: '#ffb4ab'
  on-tertiary-fixed: '#410002'
  on-tertiary-fixed-variant: '#93000b'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: '700'
    lineHeight: 2.25rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 1.375rem
    fontWeight: '600'
    lineHeight: 1.875rem
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.625rem
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.125rem
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1rem
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 0.875rem
    letterSpacing: 0.04em
  data-metric:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '700'
    lineHeight: 1.75rem
    letterSpacing: -0.02em
  data-tabular:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1.125rem
    letterSpacing: 0em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system is engineered for diagnostic utility, cognitive clarity, and clinical trust. Built specifically for nephrologists, clinical researchers, and specialized healthcare providers, the interface balances high-density information architecture with decisive typographic hierarchy. 

The aesthetic adheres strictly to modern clinical ergonomics: utilitarian, restrained, and purposeful. It discards decorative trends—refusing glassmorphism, synthetic glows, ambient colored lighting, and skeuomorphic gradients—in favor of crisp surface definition, immediate scannability, and high contrast. The visual environment mimics mission-critical diagnostic tools where clarity directly impacts patient outcomes. Interfaces prioritize fast visual triage through structured tabular data, deliberate status badging, and standardized interactive behaviors.

## Colors

The color system employs a calibrated clinical palette designed to meet strict WCAG AAA contrast ratios for body content and AA for large display markers. 

### Core Palette
- **Primary Clinical Blue (`#1E40AF`):** Core interactive states, active selection outlines, key navigational triggers, and authoritative brand anchors. Primary Dark (`#1E3A8A`) serves hover/pressed states, while Primary Light (`#DBEAFE`) provides soft selection highlights and subtle row activations.
- **Base Surfaces (`#F8FAFC` & `#FFFFFF`):** Background canvas is rendered in clean slate white (`#F8FAFC`), while cards, data grids, side sheets, and modal panels sit on pure white (`#FFFFFF`).
- **Dividers & Borders (`#E2E8F0`):** Precise 1px borders define all structural compartments without competing with text.
- **Text Tiers:** Primary values, headlines, and data keys use `#0F172A`. Secondary labels, column headers, units of measure, and timestamps use `#475569`. Auxiliary cues and inactive placeholders use `#64748B`.

### Triage & Risk Matrix
Color is functional, never decorative. Risk indicators use consistent three-token systems (Background, Border, Text):
- **CKD / High Risk (`#DC2626`):** Solid text `#991B1B`, background `#FEF2F2`, border `#FECACA`. Indicates acute decline, rapid eGFR trajectory drops, or critical risk classifications (KDIGO Stage 4/5).
- **Moderate Risk / Pending Review (`#D97706`):** Solid text `#92400E`, background `#FFFBEB`, border `#FDE68A`. Signifies borderline markers, moderate albuminuria (A2), or unreviewed pipeline alerts.
- **Healthy / Optimal / Low Risk (`#059669`):** Solid text `#065F46`, background `#ECFDF5`, border `#A7F3D0`. Signifies stable renal biomarkers (KDIGO G1/G2 with normal albuminuria A1).

## Typography

Typography is calibrated for instantaneous comprehension across dense clinical surfaces. Inter is deployed across all UI layers, leveraging its tall x-height and neutral geometric apertures.

### Numerical & Tabular Data
All numerical measurements—eGFR values, serum creatinine, uACR ratios, patient identifiers, timestamps, and probabilities—must activate OpenType tabular lining figures (`font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1, "cv05" 1`). This ensures vertical column alignment down large grids, preventing jitter during live metric streaming or sorting.

### Typographic Hierarchy
- **Header Structure:** Case is standard sentence case. Display headers avoid excessive scales, capping at 28px (`1.75rem`) to maximize vertical efficiency for clinical review.
- **Micro-Labels & Column Keys:** Table headers, metric tags, and unit notations employ `label-sm` (11px) with uppercase tracking (`+0.04em`) to establish clear segregation between operational metrics and patient identities.

## Layout & Spacing

The layout operates on a compact 4px structural baseline grid, expanding to an 8px rhythm for module blocks and macro-containers. The overarching layout structure is a 12-column fluid grid system bounded by fixed clinical sidebars (fixed width of 240px or 64px collapsed).

### Breakpoints & Reflow Behavior
- **Desktop (≥ 1280px):** Primary target viewport. Full 12-column layout displaying parallel panels: patient cohort list, contextual biometric detail panel, and predictive analytics pane simultaneously. Gutters are fixed at `1.5rem` (`24px`).
- **Tablet Landscape (1024px – 1279px):** Split-view shifts to an off-canvas slide-over drawer for patient detail panes. Primary cohort grid remains accessible with 16px gutters.
- **Tablet Portrait & Mobile (≤ 1023px):** Data tables convert to card stacks. Multi-column metric comparisons collapse into segmented views. Margin shrinks to `1rem` (`16px`).

### Density Principles
Padding inside data-heavy rows and controls is condensed to minimize scrolling overhead. Row heights for patient worklists default to a compact 36px–40px, enabling clinicians to view up to 20 patient records above the fold.

## Elevation & Depth

Visual hierarchy is maintained via structural surface stratification and hairline boundaries rather than drop shadows. Shadow blur effects are suppressed to keep high-frequency medical data razor-sharp.

### Structural Stratification
- **Flat (Level 0):** Base canvas `#F8FAFC`. Used strictly for workspace backgrounds.
- **Card & Grid Shell (Level 1):** Solid `#FFFFFF` elevated solely by a 1px solid `#E2E8F0` border. No drop shadow.
- **Interactive Flyouts & Filter Popovers (Level 2):** `#FFFFFF` paired with a 1px `#CBD5E1` border and a restrained, non-tinted micro-shadow (`0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.05)`).
- **Critical Modals & Confirmation Overlays (Level 3):** Centered panel on `#FFFFFF`, surrounded by a high-contrast clinical backdrop overlay (`rgba(15, 23, 42, 0.45)`), bounded by `box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.12), 0 4px 6px -4px rgba(15, 23, 42, 0.08)`.

Dividers between tabular rows are continuous 1px lines using `#E2E8F0`. Group separators or summary bands employ a tinted fill `#F1F5F9`.

## Shapes

The geometric architecture uses `Soft` curvature (`0.25rem` / `4px`), projecting precision, discipline, and efficiency.

- **Data Inputs, Buttons, & Badges:** Use a base corner radius of `4px` (`0.25rem`). This provides clean alignment with data grid borders and keeps vertical spacing compact.
- **Panels & Workstations:** Main dashboard cards, chart modules, and slide-in trays apply `6px` (`0.375rem`) to maintain subtle softness without wasting peripheral screen space.
- **Status Indicators & Triage Badges:** Apply `4px` corner radii. True pill geometries (fully rounded 9999px) are strictly reserved for circular notification counters and small status dots.

## Components

### Buttons
- **Primary:** Background `#1E40AF`, text `#FFFFFF`, border none. Hover: `#1E3A8A`. Active/Focus: outline `2px solid #DBEAFE` with `2px` offset. Height: 32px (compact) or 36px (default). Padding: 0 12px.
- **Secondary / Outline:** Background `#FFFFFF`, text `#0F172A`, border `1px solid #CBD5E1`. Hover: `#F8FAFC`.
- **Destructive:** Background `#DC2626`, text `#FFFFFF`. Hover: `#B91C1C`. Reserved for irreversible clinical actions (e.g., discharge overrides, record deletion).
- **Icon Actions:** Ghost style, 28x28px box, color `#475569`, hover `#F1F5F9`.

### Badges & Risk Chips
Composed of a 3-way color system with strict 1px borders, 4px border radius, and internal padding of `2px 8px` with font style `label-sm`:
- **High Risk (CKD Progression):** Text `#991B1B`, Background `#FEF2F2`, Border `#FECACA`.
- **Moderate Risk (Borderline):** Text `#92400E`, Background `#FFFBEB`, Border `#FDE68A`.
- **Low Risk (Stable):** Text `#065F46`, Background `#ECFDF5`, Border `#A7F3D0`.
- **Neutral / Baseline Metric:** Text `#334155`, Background `#F1F5F9`, Border `#CBD5E1`.

### Data Tables (Clinical Grids)
- **Header:** Height 32px, background `#F8FAFC`, border-bottom `1px solid #CBD5E1`. Typography: `label-sm`, color `#475569`, uppercase.
- **Rows:** Height 36px (compact) to 44px (spacious). Alternating zebra striping is disabled; rows separate via `1px solid #E2E8F0`. Hover state triggers background `#F8FAFC`. Active/Selected patient row applies `#EFF6FF` with a 2px left border in `#1E40AF`.
- **Numeric Cells:** Right-aligned, utilizing `data-tabular` with tabular numbers enabled.

### Form Inputs & Selects
- Height 32px. Background `#FFFFFF`, border `1px solid #CBD5E1`, border-radius `4px`.
- Text: `body-md` in `#0F172A`. Placeholder: `#64748B`.
- Focus state: Border color `#1E40AF`, ring `1px solid #1E40AF`.
- Validation states replace standard border with `#DC2626` (Error) or `#059669` (Verified).

### Checkboxes & Radios
- Size 16x16px with a `3px` corner radius for checkboxes, circular for radios.
- Border `1px solid #94A3B8`. Checked state fills `#1E40AF` with a white checkmark icon.

### Clinical Metric Cards
Modular container featuring a fixed 1px `#E2E8F0` perimeter on `#FFFFFF`. Internal padding is `12px` (`space-md`). Displays the primary biomarker or risk percentage using `data-metric`, flanked by KDIGO stage indicators and delta trajectory icons (e.g., eGFR slope -4.2 mL/min/1.73m²/yr).