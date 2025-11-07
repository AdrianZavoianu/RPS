# RPS Design System

**Modern Minimalist Data Visualization Aesthetic**

This document defines the visual language and design principles for the RPS application, inspired by modern web applications like Vercel, Linear, Framer, and data visualization platforms.

---

## 🎨 Design Philosophy

### Core Principles
1. **Minimalist** - Remove unnecessary visual elements
2. **Data-First** - Let the data and content speak
3. **Tech-Forward** - Modern, technical aesthetic
4. **Subtle & Refined** - Gentle interactions, no harsh contrasts
5. **Consistent** - Predictable patterns across the entire app

### Visual Identity
- **Clean geometric shapes** over colorful icons
- **Monochrome hierarchy** with selective color accents
- **Transparent layers** that blend seamlessly
- **Generous whitespace** for breathing room
- **Typography-focused** with clear hierarchy

---

## 🎭 Color Palette

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
--success: #10b981  /* Success states, confirmations */
--warning: #f59e0b  /* Warnings, attention needed */
--error:   #ef4444  /* Errors, destructive actions */
--info:    #3b82f6  /* Info messages, tips */
```

---

## 📝 Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", "Roboto", "Helvetica Neue", sans-serif;
```

### Size Scale
```css
--text-xs:   12px  /* Metadata, tiny labels */
--text-sm:   13px  /* Secondary content, captions */
--text-base: 14px  /* Body text, standard content */
--text-lg:   16px  /* Subheaders, emphasis */
--text-xl:   18px  /* Section headers */
--text-2xl:  24px  /* Page titles */
```

### Font Weights
```css
--weight-normal:  400  /* Body text */
--weight-medium:  500  /* Subheaders, emphasis */
--weight-semibold: 600 /* Headers */
--weight-bold:    700  /* Strong emphasis (rare) */
```

### Line Heights
```css
--leading-tight:  1.25  /* Headers */
--leading-normal: 1.5   /* Body text */
--leading-relaxed: 1.75 /* Descriptive paragraphs */
```

---

## 🔲 Spacing System

### Scale (4px base)
```css
--space-1:  4px   /* Tight spacing within components */
--space-2:  8px   /* Standard component padding */
--space-3:  12px  /* Between related elements */
--space-4:  16px  /* Between sections */
--space-6:  24px  /* Between major sections */
--space-8:  32px  /* Between page sections */
--space-12: 48px  /* Between distinct pages/views */
```

### Component Padding
- **Buttons**: `8px 16px` (sm), `10px 20px` (md), `12px 24px` (lg)
- **Input Fields**: `8px 12px`
- **Cards**: `16px` to `24px`
- **Panels**: `24px` (outer), `16px` (inner)

---

## 🎯 Components

### Buttons

**Primary Button**
```css
background: #4a7d89;
color: #ffffff;
border: none;
border-radius: 6px;
padding: 10px 20px;
font-weight: 500;
font-size: 14px;

hover: background: #5a8d99;
active: background: #3a6d79;
```

**Secondary Button**
```css
background: #161b22;
color: #d1d5db;
border: 1px solid #2c313a;
border-radius: 6px;
padding: 10px 20px;
font-weight: 500;
font-size: 14px;

hover: background: #1c2128;
```

**Ghost Button**
```css
background: transparent;
color: #9ca3af;
border: none;
padding: 10px 20px;
font-weight: 400;
font-size: 14px;

hover: background: rgba(255, 255, 255, 0.03);
       color: #d1d5db;
```

### Input Fields

```css
background: #0a0c10;
color: #d1d5db;
border: 1px solid #2c313a;  /* Default */
border-radius: 6px;
padding: 8px 12px;
font-size: 14px;

/* Dynamic border colors (for required fields) */
empty-required: border: 2px solid #ff8c00;  /* Orange for empty required */

focus: border-color: #4a7d89;  /* Blue when focused */
       outline: none;
       box-shadow: 0 0 0 3px rgba(74, 125, 137, 0.1);

placeholder: color: #7f8b9a;
```

**Implementation Note**: Use Qt property-based styling for dynamic borders:
```python
line_edit.setProperty("empty", "true")  # Initially empty
line_edit.textChanged.connect(lambda: self._update_empty_state(line_edit))

# Stylesheet:
# QLineEdit[empty="true"] { border: 2px solid #ff8c00; }
# QLineEdit:focus { border-color: #4a7d89; }
```

### Checkboxes

**Classic Style** (visible checkmark inside rectangle):

```css
/* Unchecked */
indicator: width: 18px;
          height: 18px;
          border: 1px solid #2c313a;
          border-radius: 4px;
          background: transparent;

/* Checked */
indicator-checked: background: #4a7d89;  /* Teal fill */
                   image: url(checkmark.png);  /* White ✓ symbol */
                   border-color: #4a7d89;

/* Hover */
hover: border-color: #4a7d89;
```

**Implementation Note**: Use temp file for checkmark image:
```python
import tempfile
# Create 18×18 checkmark pixmap with white ✓
checkmark_pixmap.save(os.path.join(tempfile.gettempdir(), "app_checkbox_check.png"))

# In stylesheet:
# QCheckBox::indicator:checked {
#     image: url({temp_path.replace("\\", "/")});
# }
```

### Cards & Panels

```css
background: #161b22;
border: 1px solid #2c313a;
border-radius: 8px;
padding: 16px to 24px;
box-shadow: none;  /* No shadows in dark mode */
```

### Tree/Navigation Items

```css
/* Default state */
background: transparent;
color: #9ca3af;
padding: 7px 10px;
border-radius: 5px;
font-size: 14px;

/* Hover state */
hover: background: rgba(255, 255, 255, 0.03);
       color: #d1d5db;

/* Selected state */
selected: background: rgba(74, 125, 137, 0.12);
          color: #67e8f9;
          font-weight: 400;
```

### Tables

```css
/* Header */
th: background: #161b22;
    color: #9ca3af;
    font-weight: 500;
    font-size: 13px;
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid #2c313a;

/* Cells */
td: color: #d1d5db;
    font-size: 14px;
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

/* Row hover */
tr:hover: background: rgba(255, 255, 255, 0.02);
```

---

## 🔣 Icon System

### Geometric Shapes (Minimalist)
Use simple Unicode geometric characters instead of colorful emojis:

**Navigation & Hierarchy**
- `▸` - Expandable sections, result sets
- `▾` - Expanded state (alternative)
- `›` - Leaf items, final level items
- `◆` - Category markers (filled)
- `◇` - Sub-category markers (hollow)
- `└` - Terminal items, tree connectors
- `├` - Tree branch items
- `│` - Tree vertical lines

**Actions & States**
- `⊕` - Add, create new
- `⊖` - Remove, delete
- `⊙` - Select, target
- `⟳` - Refresh, reload
- `✓` - Success, completed
- `✗` - Error, failed
- `⚠` - Warning
- `ⓘ` - Information

**Data Types**
- `⊞` - Grid view
- `≡` - List view
- `▭` - Card view
- `▤` - Table view
- `◐` - Loading, in progress

### Icon Usage Rules
1. **Consistency** - Use the same icon for the same concept throughout
2. **Minimal Color** - Icons should be monochrome, colored only for semantic meaning
3. **Size** - Icons inherit text size, no need for explicit sizing
4. **Spacing** - Always include space after icon: `▸ Label` not `▸Label`

---

## 📐 Layout Patterns

### Grid System
- Base unit: `4px`
- Standard spacing: `8px`, `12px`, `16px`, `24px`
- Container max width: Varies by context, no hard limit
- Breakpoints: Not applicable (desktop-only app)

### Panel Layouts

**Sidebar Navigation**
- Width: `200px` - `250px`
- Background: Transparent or `#0a0c10`
- Padding: `8px 4px`
- Item spacing: `1px` vertical margin

**Content Area**
- Margin: `16px` from container edges
- Padding: `24px` for cards
- Spacing between elements: `16px`

**Splitters**
- Handle width: `8px`
- Handle color: Transparent
- Hover: `rgba(255, 255, 255, 0.05)`

---

## 🎬 Animations & Transitions

### Timing
```css
--duration-fast:   100ms  /* Micro-interactions */
--duration-base:   200ms  /* Standard transitions */
--duration-slow:   300ms  /* Complex animations */
--duration-slower: 500ms  /* Page transitions */
```

### Easing
```css
--ease-default: cubic-bezier(0.4, 0.0, 0.2, 1);  /* Standard ease */
--ease-in:      cubic-bezier(0.4, 0.0, 1, 1);    /* Accelerate */
--ease-out:     cubic-bezier(0.0, 0.0, 0.2, 1);  /* Decelerate */
```

### Properties to Animate
- `background-color` - Hover, selection states
- `color` - Text color changes
- `opacity` - Show/hide elements
- `transform` - Subtle movements (use sparingly)

### What NOT to Animate
- Borders (usually)
- Width/height (can cause layout shifts)
- Font properties

---

## 🎨 Component Examples

### Tree Browser (Implemented)
```python
# Modern minimalist style
QTreeWidget {
    background-color: transparent;
    border: none;
    padding: 4px;
    font-size: 14px;
}

QTreeWidget::item {
    padding: 7px 10px;
    border-radius: 5px;
    color: #9ca3af;
    margin: 1px 0px;
}

QTreeWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.03);
    color: #d1d5db;
}

QTreeWidget::item:selected {
    background-color: rgba(74, 125, 137, 0.12);
    color: #67e8f9;
    font-weight: 400;
}
```

### Dialog (Standard Pattern)
```python
QDialog {
    background-color: #161b22;
    border: 1px solid #2c313a;
    border-radius: 8px;
}

QLabel {
    color: #d1d5db;
    font-size: 14px;
}

QLineEdit {
    background-color: #0a0c10;
    border: 1px solid #2c313a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #d1d5db;
    font-size: 14px;
}

QLineEdit:focus {
    border-color: #4a7d89;
}
```

---

## ✅ Do's and Don'ts

### ✅ Do's
- Use geometric shapes for icons
- Keep backgrounds transparent or minimal
- Use subtle hover states (3-5% opacity)
- Apply consistent spacing (4px base)
- Use font-weight 400 for body, 500 for emphasis
- Keep borders subtle (#2c313a)
- Use cyan (#67e8f9) for selections
- Animate transitions at 200ms
- Use 5-6px border radius

### ❌ Don'ts
- Don't use colorful emoji icons (🎨📊🌐)
- Don't use heavy box shadows in dark mode
- Don't use bright, saturated colors
- Don't use font-weight 700 unless absolutely necessary
- Don't add borders everywhere (minimal is better)
- Don't use large padding (keep it tight)
- Don't animate width/height (causes jank)
- Don't use different accent colors inconsistently

---

## 🎯 Application Guidelines

### When Creating New Components

1. **Start with transparency** - Add background only if needed
2. **Use the color palette** - Don't introduce new colors
3. **Follow spacing scale** - Use 4px increments
4. **Keep it minimal** - Remove decoration until it looks wrong, then add back one element
5. **Test hover states** - Should be barely visible but noticeable
6. **Check text contrast** - Use #9ca3af for secondary, #d1d5db for primary
7. **Use geometric icons** - Reference the icon system above

### Consistency Checklist
- [ ] Uses colors from the palette
- [ ] Follows 4px spacing grid
- [ ] Font size is 14px (or from type scale)
- [ ] Border radius is 5-6px
- [ ] Hover state is subtle (3-5% opacity)
- [ ] Selected state uses cyan (#67e8f9)
- [ ] No emoji icons (geometric shapes only)
- [ ] No heavy shadows

---

## 📚 References

**Inspiration Sources:**
- [Vercel](https://vercel.com) - Clean, minimalist tech aesthetic
- [Linear](https://linear.app) - Refined, fast, minimal
- [Framer](https://framer.com) - Modern, design-forward
- [Tailwind UI](https://tailwindui.com) - Component patterns
- [shadcn/ui](https://ui.shadcn.com) - Modern React components

**Related Documents:**
- `CLAUDE.md` - Project context, current state, quick development guide
- `ARCHITECTURE.md` - Technical architecture and data model
- `PRD.md` - Product requirements and roadmap
- `HIERARCHY_IMPLEMENTATION_STATUS.md` - Data hierarchy implementation
- `src/gui/styles.py` - Global stylesheet implementation
- `src/gui/ui_helpers.py` - Component creation utilities
- `src/gui/results_tree_browser.py` - Reference implementation

---

**Last Updated**: 2024-11-07
**Status**: Active - Apply to all new components
**Version**: 1.1 - Updated with dialog patterns and dynamic borders

---

## 📖 For Developers

**When creating/modifying UI components:**

1. Read this document to understand design principles
2. Check `results_tree_browser.py` for reference implementation
3. Use colors from palette only (no new colors)
4. Follow 4px spacing grid
5. Use geometric icons (see Icon System), no emojis
6. Keep backgrounds transparent unless needed
7. Test hover/selection states for subtlety

See `CLAUDE.md` → "Styling New UI Components" for code examples.
