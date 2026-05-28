# Design System Specification: High-End Enterprise Glassmorphism

## 1. Overview & Creative North Star

### Creative North Star: "The Digital Curator"
This design system moves away from the rigid, utilitarian nature of enterprise software and toward a "curated" editorial experience. The goal is to blend the precision of Apple’s hardware-inspired aesthetics with the ethereal qualities of glassmorphism. We treat the interface not as a series of boxes, but as a layered ecosystem of semi-transparent surfaces floating over a deep, atmospheric canvas.

By leveraging **intentional asymmetry**, generous **negative space**, and **tonal layering**, we eliminate the "template" look. Components should feel like they are resting on a physical desk, reacting to light and depth through refraction and subtle shadows rather than harsh strokes.

---

## 2. Colors & Surface Philosophy

The palette is rooted in sophisticated neutrals and a singular, vibrant blue accent. We move beyond flat color by using light-refractive properties.

### Primary Tones
- **Background Gradient:** A linear transition from `surface` (#f9f9fb) to `surface-container-high` (#e8e8ea). This creates a horizon line that gives the UI a sense of gravity.
- **The Signature Glass:** Cards must use `rgba(255, 255, 255, 0.7)` with a `backdrop-filter: blur(12px)`.
- **Primary Accent:** `primary` (#004e9f) for stability, and `primary_container` (#0066cc) for active interactions.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders for sectioning or containment. 
Boundaries are defined exclusively through:
1.  **Background Shifts:** Placing a `surface_container_lowest` element on a `surface_container_low` background.
2.  **Tonal Transitions:** Using depth to signify the edge of a component.
3.  **Glass Refraction:** The blur effect naturally creates a "soft edge" that differentiates layers.

### Surface Hierarchy & Nesting
Treat the UI as physical layers of frosted glass:
- **Base Layer:** `surface` (The background canvas).
- **Secondary Layer:** `surface_container_low` (In-page sections).
- **Interactive Layer:** `surface_container_lowest` (Cards and floating inputs).
- **Elevated Layer:** Glass components with `surface_tint` reflections.

---

## 3. Typography

The typography uses the **Inter** family to provide a clean, modernist foundation. We use high contrast in scale to drive editorial impact.

| Level | Token | Size | Weight | Role |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | 3.5rem | 700 | Hero moments / Landing titles |
| **Headline** | `headline-lg` | 2.0rem | 600 | Page headers and major sections |
| **Title** | `title-md` | 1.125rem | 500 | Card titles and sub-headings |
| **Body** | `body-lg` | 1.0rem | 400 | Primary reading content |
| **Label** | `label-md` | 0.75rem | 600 | Buttons, tags, and small metadata |

**Editorial Note:** Use `on_surface` (#1a1c1d) for maximum readability on primary text, and `on_surface_variant` (#414753) for secondary descriptions to create a natural visual hierarchy without changing font sizes.

---

## 4. Elevation & Depth

We replace traditional drop shadows with **Ambient Light Dynamics**.

- **The Layering Principle:** Depth is achieved by stacking. A `surface_container_lowest` card sitting on a `surface_container` background creates a natural lift.
- **Ambient Shadows:** For "floating" glass cards, use a multi-layered shadow: `0px 10px 40px rgba(0, 0, 0, 0.04), 0px 2px 10px rgba(0, 0, 0, 0.02)`. The shadow color must never be pure black; it should be a deep tint of the `on_surface` color.
- **The "Ghost Border" Fallback:** If a container requires further definition for accessibility, use the `outline_variant` at **10% opacity**. Never use high-contrast outlines.
- **Asymmetric Depth:** Allow elements to overlap slightly (e.g., a card bleeding over a section break) to break the "grid-lock" of standard enterprise dashboards.

---

## 5. Components

### Buttons
- **Primary:** `primary_container` background with `on_primary` text. Use a `1.5rem` (xl) corner radius for a friendly, modern feel.
- **Glass Secondary:** Semi-transparent white with backdrop-blur.
- **Hover States:** Transition to a slightly more opaque background or a `surface_tint` glow.

### Modern Upload Zone
- **Structure:** Large container with `24px` (xl) rounded corners.
- **Border:** Dashed line using `primary` (#004e9f) at 40% opacity.
- **Interior:** Use a subtle `primary_fixed` background to draw the eye without overwhelming it.

### Cards & Lists
- **No Dividers:** Forbid the use of horizontal rules. Use `1.5rem` vertical spacing or a shift from `surface_container` to `surface_container_lowest` to separate items.
- **Glass Factor:** Ensure cards use the 12px blur to allow the background gradient to bleed through, ensuring the UI feels "alive."

### Navigation Bar
- **Sticky Blur:** Fixed top position. Background: `rgba(255, 255, 255, 0.6)`. 
- **Backdrop-filter:** `blur(20px)`. This ensures content scrolling underneath remains legible but beautifully obscured.

---

## 6. Do’s and Don’ts

### Do
- **Do** prioritize white space over lines. If a section feels crowded, add padding instead of a border.
- **Do** use high-quality, thin-stroke icons that match the `outline` token weight.
- **Do** ensure your Glassmorphism components have a 1px "inner glow" (a very light, nearly transparent top border) to mimic how light hits the edge of real glass.

### Don’t
- **Don't** use pure black (#000000) for shadows or text. It breaks the atmospheric "glass" effect.
- **Don't** use the `DEFAULT` (0.5rem) corner radius for main cards. This system demands the "softness" of `xl` (1.5rem) or `lg` (1.0rem) radii.
- **Don't** use traditional "Material" elevation. If an element needs to stand out, use a tonal shift or a more aggressive backdrop blur rather than a heavy shadow.
- **Don't** use 100% opaque borders. High-contrast lines are the enemy of this system's premium, airy feel.