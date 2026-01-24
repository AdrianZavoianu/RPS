# RPS Design System

**Modern Minimalist Data Visualization Aesthetic**

---

## Design Philosophy

### Core Principles
1. **Minimalist** - Remove unnecessary visual elements
2. **Data-First** - Let the data and content speak
3. **Tech-Forward** - Modern, technical aesthetic
4. **Subtle & Refined** - Gentle interactions, no harsh contrasts
5. **Consistent** - Predictable patterns across the entire app

### Visual Identity
- Clean geometric shapes over colorful icons
- Monochrome hierarchy with selective color accents
- Transparent layers that blend seamlessly
- Generous whitespace for breathing room
- Typography-focused with clear hierarchy

---

## Color Palette

### Background Layers
```css
--bg-primary:   #0a0c10  /* Main app background */
--bg-secondary: #161b22  /* Cards, panels, elevated surfaces */
--bg-tertiary:  #1c2128  /* Nested panels, input fields */
--bg-hover:     rgba(255, 255, 255, 0.03)  /* Subtle hover state */
```

### Text & Foreground
```css
--text-primary:   #d1d5db  /* Main content text */
--text-secondary: #9ca3af  /* Secondary text, labels */
--text-muted:     #7f8b9a  /* Disabled, placeholder text */
--text-accent:    #67e8f9  /* Selected, highlighted text (cyan) */
```

### Accent & Interactive
```css
--accent-primary:   #4a7d89  /* Buttons, primary actions (teal) */
--accent-secondary: #67e8f9  /* Selection, highlights (cyan) */
--accent-hover:     rgba(74, 125, 137, 0.18)  /* Accent hover state */
--accent-selected:  rgba(74, 125, 137, 0.12)  /* Accent selection bg */
```

### Borders
```css
--border-default: #2c313a  /* Standard borders */
--border-subtle:  rgba(255, 255, 255, 0.05)  /* Barely visible dividers */
```

### Semantic Colors
```css
--success: #10b981  /* Success states */
--warning: #f59e0b  /* Warnings */
--error:   #ef4444  /* Errors */
--info:    #3b82f6  /* Info messages */
```

---

## Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

### Size Scale
```css
--text-xs:   12px  /* Metadata, tiny labels */
--text-sm:   13px  /* Secondary content, captions */
--text-base: 14px  /* Body text, standard content */
--text-md:   16px  /* Subheadlines */
--text-lg:   18px  /* Section headers */
--text-xl:   24px  /* Page titles */
--text-2xl:  32px  /* Page headlines */
```

### Font Weights
```css
--weight-normal:   400  /* Body text */
--weight-medium:   500  /* Subheaders, emphasis */
--weight-semibold: 600  /* Headers */
```

---

## Spacing System

### Scale (4px base)
```css
--space-1:  4px   /* Tight spacing within components */
--space-2:  8px   /* Standard component padding */
--space-3:  12px  /* Between related elements */
--space-4:  16px  /* Between sections */
--space-6:  24px  /* Between major sections */
--space-8:  32px  /* Between page sections */
```

### Component Padding
- **Buttons**: `12px 28px` (primary/secondary), `10px 20px` (ghost)
- **Input Fields**: `8px 12px`
- **Cards**: `16px` to `24px`
- **Panels**: `24px` (outer), `16px` (inner)

---

## Components

### Buttons

**Primary Button**
```css
background: #4a7d89;
color: #ffffff;
border: none;
border-radius: 999px;
padding: 12px 28px;
font-weight: 600;
font-size: 15px;

hover: background: rgba(74, 125, 137, 0.18);
```

**Secondary Button**
```css
background: #161b22;
color: #d1d5db;
border: 1px solid #2c313a;
border-radius: 999px;
padding: 12px 28px;
font-weight: 600;
font-size: 15px;

hover: background: rgba(255, 255, 255, 0.03);
       border-color: #4a7d89;
       color: #4a7d89;
```

**Ghost Button**
```css
background: transparent;
color: #d1d5db;
border: 1px solid #2c313a;
border-radius: 999px;
padding: 10px 20px;
font-weight: 500;
font-size: 14px;

hover: border-color: #4a7d89;
       color: #4a7d89;
```

### Input Fields
```css
background: #1c2128;
color: #d1d5db;
border: 1px solid #2c313a;
border-radius: 6px;
padding: 8px 12px;

focus: border-color: #4a7d89;
```

### Checkboxes
```css
/* Unchecked */
indicator: width: 18px; height: 18px;
           border: 2px solid #2c313a;
           border-radius: 3px;
           background: #0a0c10;

/* Checked */
indicator-checked: background: #4a7d89;
                   border-color: #4a7d89;
                   image: url(rps_checkbox_check.png);

/* Hover */
hover: border-color: #4a7d89;
       background: #161b22;
```

### Cards & Panels
```css
background: #161b22;
border: 1px solid #2c313a;
border-radius: 8px;
padding: 16px to 24px;
box-shadow: none;  /* No shadows in dark mode */
```
Note: project cards use a 12px radius for a softer appearance.

### Tree/Navigation Items
```css
/* Default */
background: transparent;
color: #9ca3af;
padding: 7px 10px;
border-radius: 5px;

/* Hover */
hover: background: rgba(255, 255, 255, 0.03);
       color: #d1d5db;

/* Selected */
selected: background: rgba(74, 125, 137, 0.12);
          color: #67e8f9;
```

### Tables
```css
/* Header */
th: background: #161b22;
    color: #9ca3af;
    font-weight: 500;
    font-size: 13px;
    border-bottom: 1px solid #2c313a;

/* Cells */
td: color: #d1d5db;
    font-size: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

/* Row hover */
tr:hover: background: rgba(255, 255, 255, 0.02);
```

---

## Icon System

### Geometric Shapes (Minimalist)
Use simple Unicode geometric characters:

**Navigation & Hierarchy**
- `▸` - Expandable sections
- `›` - Leaf items
- `◆` - Category markers (filled)
- `◇` - Sub-category markers (hollow)

**Actions & States**
- `⊕` - Add, create new
- `⊖` - Remove, delete
- `✓` - Success, completed
- `✗` - Error, failed
- `⚠` - Warning

### Rules
1. **Consistency** - Same icon for same concept
2. **Minimal Color** - Monochrome, colored only for semantic meaning
3. **Size** - Icons inherit text size
4. **Spacing** - Always space after icon: `▸ Label`

---

## Layout Patterns

### Panel Layouts

**Sidebar Navigation**
- Width: `200px` - `250px`
- Background: Transparent or `#0a0c10`
- Padding: `8px 4px`

**Content Area**
- Margin: `16px` from container edges
- Padding: `24px` for cards
- Spacing between elements: `16px`

**Splitters**
- Handle width: `8px`
- Handle color: Transparent
- Hover: `rgba(255, 255, 255, 0.05)`

---

## Animations

### Timing
```css
--duration-fast:   100ms  /* Micro-interactions */
--duration-base:   200ms  /* Standard transitions */
--duration-slow:   300ms  /* Complex animations */
```

### Properties to Animate
- `background-color` - Hover, selection states
- `color` - Text color changes
- `opacity` - Show/hide elements

### Do NOT Animate
- Borders (usually)
- Width/height (causes layout shifts)
- Font properties

---

## Do's and Don'ts

### Do
- Use geometric shapes for icons
- Keep backgrounds transparent or minimal
- Use subtle hover states (3-5% opacity)
- Apply consistent spacing (4px base)
- Use cyan (#67e8f9) for selections
- Animate at 200ms
- Use 8-12px border radius for cards/actions, 6px for inputs

### Don't
- Use colorful emoji icons
- Use heavy box shadows in dark mode
- Use bright, saturated colors
- Use font-weight 700 unless necessary
- Add borders everywhere
- Animate width/height

---

## Implementation

**When creating new components:**
1. Start with transparency - Add background only if needed
2. Use the color palette - Don't introduce new colors
3. Follow spacing scale - Use 4px increments
4. Keep it minimal - Remove decoration until it looks wrong
5. Test hover states - Should be barely visible but noticeable

**Reference files:**
- `src/gui/design_tokens.py` - Palette, spacing, typography, form styles
- `src/gui/styles.py` - Global stylesheet
- `src/gui/ui_helpers.py` - Component creation utilities

---

**Last Updated**: 2026-01-24
**Status**: Active - Apply to all new components
